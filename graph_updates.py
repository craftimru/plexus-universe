"""Validated agent edits, shared by CLI and MCP."""
import copy
import time

from graph_store import Conflict, check_human_edits, check_locked, document_diff, read_document, save_document, validate

NODE_FIELDS = {"label", "human", "status", "tier", "parent", "paths", "tests", "note",
               "hero", "arts", "sats", "flag", "proposed", "autoexpand", "color", "family",
               "codex_state", "locked", "needs_review"}


def apply_operations(root, operations, rebuild=False, dry_run=False, expected_revision=None, summary=""):
    if not isinstance(operations, list) or not 1 <= len(operations) <= 100:
        raise ValueError("Provide between 1 and 100 operations")
    before, current = read_document(root)
    if expected_revision is not None and expected_revision != current:
        raise Conflict("Revision mismatch. Read the affected nodes again before retrying.")
    document = copy.deepcopy(before)
    nodes = document["NODES"]
    links = document.setdefault("LINKS", [])
    acknowledged = {}
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("Each operation must be an object")
        kind = operation.get("op")
        key = operation.get("id")
        if kind in ("update-node", "set-status", "remove-node", "acknowledge-node") and key not in nodes:
            raise ValueError("Unknown node: " + str(key))
        if kind == "acknowledge-node":
            stamp = nodes[key].get("human_edit")
            if not stamp or operation.get("token") != stamp.get("token"):
                raise ValueError("Human edit token changed or is absent; read node again: " + key)
            note = operation.get("note", "")
            if not isinstance(note, str) or not note.strip():
                raise ValueError("Explain what human changes you read and how you will handle them in acknowledgement note")
            acknowledged[key] = stamp["token"]
            stamp["acknowledged"] = True
            stamp["acknowledgement"] = {"at": int(time.time()), "note": note.strip()[:2000]}
        elif kind in ("add-node", "update-node", "set-status"):
            fields = operation.get("node" if kind == "add-node" else "fields", {})
            if kind == "set-status":
                fields = {"status": operation.get("status")}
            if not isinstance(fields, dict) or not fields or set(fields) - NODE_FIELDS:
                raise ValueError("Invalid or empty node fields")
            if kind == "add-node":
                if not isinstance(key, str) or not key or key in nodes:
                    raise ValueError("Node ID must be new and nonempty")
                nodes[key] = {"label": key, "human": "", "status": "idea", "paths": [], "tests": [], **fields}
            else:
                nodes[key].update(fields)
        elif kind == "remove-node":
            if nodes[key].get("parent") is None:
                raise ValueError("Cannot remove the root")
            if any(n.get("parent") == key for n in nodes.values()):
                raise ValueError("Cannot remove a node with children; move or remove children first")
            del nodes[key]
            links[:] = [link for link in links if key not in (link["source"], link["target"])]
        elif kind in ("add-link", "remove-link"):
            source, target = operation.get("source"), operation.get("target")
            if source not in nodes or target not in nodes:
                raise ValueError("Link endpoints must exist")
            matching = [link for link in links if link["source"] == source and link["target"] == target]
            if kind == "add-link":
                if matching:
                    raise ValueError("Explicit link already exists; remove it first in the same batch")
                links.append({"source": source, "target": target, "type": operation.get("type", "uses"),
                              "label": operation.get("label", ""), "proposed": operation.get("proposed", False)})
            else:
                if not matching:
                    raise ValueError("No explicit link found; hierarchy edges come from parent fields")
                links[:] = [link for link in links if link not in matching]
        else:
            raise ValueError("Unknown operation: " + str(kind))
    validate(document)
    check_locked(before, document)
    check_human_edits(before, document, acknowledged)
    diff = document_diff(before, document)
    changed = any(diff.values())
    if dry_run or (not changed and not rebuild):
        return {"saved": False, "dry_run": dry_run, "unchanged": not changed, "revision": current, "diff": diff}
    new_revision = save_document(root, document, current, rebuild=rebuild, actor="agent", summary=summary, acknowledged=acknowledged)
    return {"saved": True, "rebuilt": rebuild, "revision": new_revision, "diff": diff,
            "rebuild_required": not rebuild}
