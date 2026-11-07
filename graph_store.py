"""Shared, declarative editor overlay; no changes to the viewer data schema."""
import hashlib
import copy
import json
from contextlib import contextmanager
import math
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
import uuid

SETTINGS = ("PROJECT_NAME", "ENGINE_VERSION", "FRESH_HOURS", "FAMILY", "STATUS_NAMES", "CUSTOM_ARTS", "NODES", "LINKS")
STATUSES = {"idea", "art", "proto", "wip", "live", "polished", "shelved"}


class Conflict(ValueError):
    pass


def revision(root):
    digest = hashlib.sha256()
    for name in ("graph_content.py", "graph_edit.json"):
        path = Path(root) / name
        digest.update(name.encode())
        digest.update(path.read_bytes() if path.exists() else b"<absent>")
    return digest.hexdigest()


def load_overlay(root):
    path = Path(root) / "graph_edit.json"
    if not path.exists():
        return {}
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    validate(document)
    return document


def load_document(root):
    config = runpy.run_path(str(Path(root) / "graph_content.py"))
    document = {key: config[key] for key in SETTINGS if key in config}
    document.update(load_overlay(root))
    validate(document)
    return document


def read_document(root):
    """Read a stable source snapshot, not a possibly outdated generated index."""
    before = revision(root)
    document = load_document(root)
    if before != revision(root):
        raise Conflict("Configuration changed while reading. Retry the query.")
    return document, before


def validate(document):
    if not isinstance(document, dict) or set(document) - set(SETTINGS):
        raise ValueError("Unknown configuration fields")
    nodes = document.get("NODES")
    if not isinstance(nodes, dict) or not nodes:
        raise ValueError("Graph must contain nodes")
    roots = []
    for key, node in nodes.items():
        if not isinstance(key, str) or not key or not isinstance(node, dict):
            raise ValueError("Invalid node ID or node")
        if type(node.get("tier", 2)) is not int or node.get("tier", 2) not in range(4):
            raise ValueError("Node tier must be 0..3: " + key)
    for key, node in nodes.items():
        tier = node.get("tier", 2)
        parent = node.get("parent")
        if parent is None:
            roots.append(key)
            if tier != 0:
                raise ValueError("Root must have tier 0")
        elif not isinstance(parent, str) or parent not in nodes or parent == key:
            raise ValueError("Invalid parent: " + key)
        elif tier <= nodes[parent].get("tier", 2):
            raise ValueError("Child tier must exceed parent tier: " + key)
        if not isinstance(node.get("status", "live"), str) or node.get("status", "live") not in STATUSES:
            raise ValueError("Invalid status: " + key)
        for field in ("label", "human", "note"):
            if field in node and not isinstance(node[field], str):
                raise ValueError("Expected text: " + field)
        for field in ("locked", "needs_review", "proposed", "autoexpand"):
            if field in node and type(node[field]) is not bool:
                raise ValueError("Expected a boolean: " + field)
        stamp = node.get("human_edit")
        if stamp is not None:
            if (not isinstance(stamp, dict) or not isinstance(stamp.get("token"), str) or not stamp["token"]
                    or type(stamp.get("at")) is not int or type(stamp.get("acknowledged")) is not bool
                    or not isinstance(stamp.get("fields"), list)
                    or any(not isinstance(field, str) for field in stamp["fields"])):
                raise ValueError("Invalid human edit stamp: " + key)
            if not isinstance(stamp.get("changes", []), list) or any(
                    not isinstance(change, dict) or not isinstance(change.get("field"), str)
                    for change in stamp.get("changes", [])):
                raise ValueError("Invalid human edit changes: " + key)
        for field in ("paths", "tests", "arts", "sats"):
            if not isinstance(node.get(field, []), list) or any(not isinstance(p, str) for p in node.get(field, [])):
                raise ValueError("Expected a list of strings: " + field)
    if len(roots) != 1:
        raise ValueError("Graph must have exactly one root")
    for key in nodes:
        seen = set()
        current = key
        while current is not None:
            if current in seen:
                raise ValueError("Hierarchy cycle: " + key)
            seen.add(current)
            current = nodes[current].get("parent")
    links = document.get("LINKS", [])
    if not isinstance(links, list):
        raise ValueError("LINKS must be a list")
    pairs = set()
    for link in links:
        if not isinstance(link, dict) or not isinstance(link.get("source"), str) or not isinstance(link.get("target"), str) or link["source"] not in nodes or link["target"] not in nodes:
            raise ValueError("Link references an unknown node")
        if not isinstance(link.get("type", "uses"), str) or not isinstance(link.get("label", ""), str):
            raise ValueError("Link type and label must be text")
        pair = (link["source"], link["target"])
        if pair in pairs:
            raise ValueError("Only one explicit link per ordered node pair is supported")
        pairs.add(pair)
    for field in ("PROJECT_NAME", "ENGINE_VERSION"):
        if field in document and not isinstance(document[field], str):
            raise ValueError("Expected text: " + field)
    if not isinstance(document.get("FAMILY", {}), dict):
        raise ValueError("FAMILY must be an object")
    if any(not isinstance(key, str) or not isinstance(color, str) for key, color in document.get("FAMILY", {}).items()):
        raise ValueError("FAMILY must map IDs to color strings")
    if "FRESH_HOURS" in document and (type(document["FRESH_HOURS"]) not in (int, float) or not math.isfinite(document["FRESH_HOURS"]) or document["FRESH_HOURS"] <= 0):
        raise ValueError("FRESH_HOURS must be positive")


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def write_lock(root):
    path = Path(root) / "graph_write.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise Conflict("Another graph writer is active (graph_write.lock). Retry after it finishes.")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        path.unlink(missing_ok=True)


def document_diff(before, after):
    nodes = []
    old, new = before.get("NODES", {}), after.get("NODES", {})
    for key in sorted(old.keys() | new.keys()):
        if key not in old:
            nodes.append({"id": key, "action": "added", "fields": sorted(new[key])})
        elif key not in new:
            nodes.append({"id": key, "action": "removed", "fields": sorted(old[key])})
        else:
            fields = [f for f in sorted(old[key].keys() | new[key].keys()) if old[key].get(f) != new[key].get(f)]
            if fields:
                nodes.append({"id": key, "action": "updated", "fields": fields})
    old_links, new_links = before.get("LINKS", []), after.get("LINKS", [])
    return {"nodes": nodes, "links_added": [l for l in new_links if l not in old_links],
            "links_removed": [l for l in old_links if l not in new_links],
            "settings": [key for key in SETTINGS if key not in ("NODES", "LINKS") and before.get(key) != after.get(key)]}


def check_locked(before, after):
    """Agent convention, not an authorization boundary; human editor may unlock."""
    old, new = before["NODES"], after["NODES"]
    locked = {key for key, node in old.items() if node.get("locked")}
    for key in locked:
        if {k: v for k, v in new.get(key, {}).items() if k != "human_edit"} != {k: v for k, v in old[key].items() if k != "human_edit"}:
            raise ValueError("Node is locked for agent updates: " + key)
    diff = document_diff(before, after)
    for link in diff["links_added"] + diff["links_removed"]:
        if {link["source"], link["target"]} & locked:
            raise ValueError("Link touches a locked node")
    for key, node in new.items():
        if key not in old or node.get("parent") != old[key].get("parent"):
            if node.get("parent") in locked or (key in old and old[key].get("parent") in locked):
                raise ValueError("Hierarchy change touches a locked parent")
    for key, node in old.items():
        if key not in new and node.get("parent") in locked:
            raise ValueError("Removal touches a locked parent")


def affected_nodes(before, after):
    diff = document_diff(before, after)
    ids = {node["id"] for node in diff["nodes"]}
    for link in diff["links_added"] + diff["links_removed"]:
        ids.update((link["source"], link["target"]))
    for key in list(ids):
        old_parent = before["NODES"].get(key, {}).get("parent")
        new_parent = after["NODES"].get(key, {}).get("parent")
        if old_parent != new_parent:
            ids.update(p for p in (old_parent, new_parent) if p)
    return ids


def stamp_human_edits(before, after):
    # Stamps are server-owned. A browser's old copy cannot erase newer stamps.
    for key, node in after["NODES"].items():
        node.pop("human_edit", None)
        if before["NODES"].get(key, {}).get("human_edit"):
            node["human_edit"] = copy.deepcopy(before["NODES"][key]["human_edit"])
    diff = document_diff(before, after)
    touched = affected_nodes(before, after)
    details = {}
    for change in diff["nodes"]:
        key = change["id"]
        details[key] = {field: {"field": field, "before": before["NODES"].get(key, {}).get(field),
                                "after": after["NODES"].get(key, {}).get(field)}
                        for field in change["fields"] if field != "human_edit"}
    # Captions and source art changes can affect a node without changing arts IDs.
    old_art = {a["key"]: a for a in before.get("CUSTOM_ARTS", [])}
    new_art = {a["key"]: a for a in after.get("CUSTOM_ARTS", [])}
    changed_art = {key for key in old_art.keys() | new_art.keys() if old_art.get(key) != new_art.get(key)}
    for key, node in after["NODES"].items():
        if {node.get("hero"), *node.get("arts", []), *node.get("sats", [])} & changed_art:
            touched.add(key)
            relevant = {node.get("hero"), *node.get("arts", []), *node.get("sats", [])} & changed_art
            details.setdefault(key, {})["art_content"] = {"field": "art_content",
                "before": [old_art[k] for k in sorted(relevant) if k in old_art],
                "after": [new_art[k] for k in sorted(relevant) if k in new_art]}
    for key in touched & after["NODES"].keys():
        changes = details.get(key, {})
        old_structure = {"children": sorted(k for k, n in before["NODES"].items() if n.get("parent") == key),
                         "links": [l for l in before.get("LINKS", []) if key in (l["source"], l["target"])]}
        new_structure = {"children": sorted(k for k, n in after["NODES"].items() if n.get("parent") == key),
                         "links": [l for l in after.get("LINKS", []) if key in (l["source"], l["target"])]}
        if old_structure != new_structure:
            changes["links_or_children"] = {"field": "links_or_children", "before": old_structure, "after": new_structure}
        old_stamp = before["NODES"].get(key, {}).get("human_edit", {})
        if old_stamp and not old_stamp.get("acknowledged"):
            pending = {c["field"]: copy.deepcopy(c) for c in old_stamp.get("changes", [])}
            for field, change in changes.items():
                if field in pending:
                    change["before"] = pending[field]["before"]
                pending[field] = change
            changes = pending
        after["NODES"][key]["human_edit"] = {"token": uuid.uuid4().hex, "at": int(time.time()),
                                                "fields": sorted(changes), "changes": list(changes.values()), "acknowledged": False}


def check_human_edits(before, after, acknowledged=None):
    acknowledged = acknowledged or {}
    for key in affected_nodes(before, after):
        stamp = before["NODES"].get(key, {}).get("human_edit", {})
        if stamp and not stamp.get("acknowledged"):
            if acknowledged.get(key) != stamp.get("token"):
                raise ValueError("Human edits require reading and acknowledgement first: " + key)


def save_document(root, document, expected_revision, rebuild=True, actor="human", summary="", acknowledged=None):
    """Commit an overlay, optional build and audit event under one writer lock.

    Failed builds restore data and snapshot. Atomic replacement protects each
    file, but the multi-file transaction is not power-loss recovery.
    """
    root = Path(root).resolve()
    with write_lock(root):
        if expected_revision != revision(root):
            raise Conflict("The configuration changed. Reload before saving.")
        document = copy.deepcopy(document)
        validate(document)
        before_doc = load_document(root)
        if actor == "agent":
            check_locked(before_doc, document)
            check_human_edits(before_doc, document, acknowledged)
        else:
            stamp_human_edits(before_doc, document)
        overlay = root / "graph_edit.json"
        history = root / "graph_history.jsonl"
        backup = root / "graph_edit.json.bak"
        files = [overlay, history, backup] + [root / "data" / name for name in ("graph.js", "graph.json", "context_nodes.json")]
        before = {path: path.read_bytes() if path.exists() else None for path in files}
        try:
            if before[overlay] is not None:
                atomic_write(backup, before[overlay])
            atomic_write(overlay, (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))
            if rebuild:
                result = subprocess.run([sys.executable, "-X", "utf8", str(root / "build_graph.py")],
                                        cwd=root, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=60)
                if result.returncode:
                    raise ValueError("Build failed: " + (result.stderr or result.stdout)[-2000:])
            current = revision(root)
            event = {"at": int(time.time()), "actor": actor, "summary": summary[:500],
                     "revision": current, "diff": document_diff(before_doc, document), "rebuilt": rebuild}
            atomic_write(history, (before[history] or b"") + (json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
            return current
        except Exception:
            for path, content in before.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(path, content)
            raise
