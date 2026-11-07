"""Filesystem checks and advisory bootstrap; never infer architecture as fact."""
import os
from pathlib import Path
import re

SKIP = {".git", ".godot", "node_modules", "__pycache__", "build", "dist", ".venv", "venv", "art"}
CODE = {".py", ".gd", ".cs", ".cpp", ".cc", ".c", ".h", ".hpp", ".rs", ".ts", ".tsx", ".js", ".jsx", ".lua", ".swift", ".md", ".txt", ".tscn", ".tres", ".json", ".yaml", ".yml"}


def scoped_files(project_root, scope, max_files=2000):
    root = Path(project_root).resolve()
    start = (root / scope).resolve()
    if not start.is_relative_to(root):
        raise ValueError("Scan scope must stay inside PROJECT_ROOT")
    if not start.exists():
        raise ValueError("Scan scope does not exist: " + scope)
    count = 0
    if start.is_file():
        yield start
        return
    for directory, dirs, files in os.walk(start, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink() or path.suffix.lower() not in CODE:
                continue
            count += 1
            if count > max_files:
                yield None
                return
            yield path


def health(graph, scope=None, max_files=2000):
    root = Path(graph.data.get("source", {}).get("project_root", "")).resolve()
    issues = []
    if not root.is_dir():
        return [{"kind": "missing_project_root", "path": str(root)}], False
    for key, node in graph.nodes.items():
        for field in ("paths", "tests"):
            for path in node.get(field, []):
                if not (root / path).exists():
                    issues.append({"kind": "missing_path", "id": key, "field": field, "path": path})
        if node.get("needs_review"):
            issues.append({"kind": "needs_review", "id": key})
        if node.get("human_edit") and not node["human_edit"].get("acknowledged"):
            issues.append({"kind": "human_edits_pending", "id": key})
        parent = node.get("parent")
        if parent and parent not in graph.nodes:
            issues.append({"kind": "broken_parent", "id": key, "parent": parent})
        seen = set()
        current = key
        while current in graph.nodes:
            if current in seen:
                issues.append({"kind": "hierarchy_cycle", "id": key})
                break
            seen.add(current)
            current = graph.nodes[current].get("parent")
    for link in graph.links:
        if link.get("source") not in graph.nodes or link.get("target") not in graph.nodes:
            issues.append({"kind": "broken_link", "source": link.get("source"), "target": link.get("target")})
    incomplete = False
    if scope is not None:
        for path in scoped_files(root, scope, max_files):
            if path is None:
                incomplete = True
                break
            relative = path.relative_to(root).as_posix()
            if not graph.owners(relative):
                issues.append({"kind": "unmapped_file", "path": relative})
    return issues, incomplete


def bootstrap(graph, scope, parent=None, max_files=2000):
    root = Path(graph.data.get("source", {}).get("project_root", "")).resolve()
    if not root.is_dir():
        raise ValueError("PROJECT_ROOT does not exist")
    if parent is not None:
        node = graph.require(parent)
        if node.get("tier", 0) >= 3:
            raise ValueError("Bootstrap parent must have tier 0, 1 or 2")
    suggestions = []
    inferred = {}
    markers = {}
    unknown = []
    incomplete = False
    for path in scoped_files(root, scope, max_files):
        if path is None:
            incomplete = True
            break
        relative = path.relative_to(root).as_posix()
        # Bound marker reads; no execution, binary parsing or symlink traversal.
        with path.open("rb") as stream:
            text = stream.read(131072).decode("utf-8", errors="replace")
        ids = set(re.findall(r"@orbit:\s*([A-Za-z0-9_-]+)", text))
        for key in sorted(ids):
            if key in graph.nodes:
                if graph.nodes[key].get("locked"):
                    unknown.append({"id": key, "path": relative, "reason": "locked"})
                elif relative not in graph.nodes[key].get("paths", []):
                    markers.setdefault(key, set()).add(relative)
            elif parent:
                inferred.setdefault(key, set()).add(relative)
            else:
                unknown.append({"id": key, "path": relative, "reason": "choose_parent"})
        if not ids and parent and not graph.owners(relative):
            folder = path.parent.relative_to(root).as_posix()
            key = "sys_" + re.sub(r"[^a-zA-Z0-9]+", "_", folder if folder != "." else path.stem).strip("_").lower()
            if key in graph.nodes:
                unknown.append({"id": key, "path": relative, "reason": "id_collision"})
            else:
                inferred.setdefault(key, set()).add(relative)
    for key, paths in sorted(markers.items()):
        suggestions.append({"op": "update-node", "id": key,
                            "fields": {"paths": sorted(set(graph.nodes[key].get("paths", [])) | paths)}})
    for key, paths in sorted(inferred.items()):
        suggestions.append({"op": "add-node", "id": key, "node": {
            "label": key, "human": "Предложено по структуре файлов; уточните назначение.",
            "tier": graph.nodes[parent].get("tier", 0) + 1, "parent": parent,
            "status": "idea", "needs_review": True, "paths": sorted(paths), "tests": []}})
    return suggestions, unknown, incomplete
