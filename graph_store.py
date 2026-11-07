"""Shared, declarative editor overlay; no changes to the viewer data schema."""
import hashlib
import json
from pathlib import Path
import runpy

SETTINGS = ("PROJECT_NAME", "ENGINE_VERSION", "FRESH_HOURS", "FAMILY", "STATUS_NAMES", "CUSTOM_ARTS", "NODES", "LINKS")
STATUSES = {"idea", "art", "proto", "wip", "live", "polished", "shelved"}


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
        tier = node.get("tier", 2)
        if type(tier) is not int or tier not in range(4):
            raise ValueError("Node tier must be 0..3: " + key)
        parent = node.get("parent")
        if parent is None:
            roots.append(key)
            if tier != 0:
                raise ValueError("Root must have tier 0")
        elif parent not in nodes or parent == key:
            raise ValueError("Invalid parent: " + key)
        elif tier <= nodes[parent].get("tier", 2):
            raise ValueError("Child tier must exceed parent tier: " + key)
        if node.get("status", "live") not in STATUSES:
            raise ValueError("Invalid status: " + key)
        for field in ("label", "human", "note"):
            if field in node and not isinstance(node[field], str):
                raise ValueError("Expected text: " + field)
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
        if not isinstance(link, dict) or link.get("source") not in nodes or link.get("target") not in nodes:
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
    if "FRESH_HOURS" in document and (type(document["FRESH_HOURS"]) not in (int, float) or document["FRESH_HOURS"] <= 0):
        raise ValueError("FRESH_HOURS must be positive")


def atomic_write(path, content):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(content)
    temp.replace(path)
