"""Navigate and maintain a shared project map with bounded JSON responses."""
import argparse
from collections import deque
import json
from pathlib import Path
import re
import sys
from graph_store import revision

WRITES = {"update-node", "add-node", "remove-node", "set-status", "add-link", "remove-link", "apply", "acknowledge-node"}


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def normalized(path):
    path = path.replace("\\", "/")
    return (path[2:] if path.startswith("./") else path).rstrip("/")


class Graph:
    def __init__(self, path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding="utf-8-sig"))
        self.nodes = {node["id"]: node for node in self.data["nodes"]}
        self.links = self.data.get("links", [])
        self.adj = {key: [] for key in self.nodes}
        for link in self.links:
            if link["source"] in self.nodes and link["target"] in self.nodes:
                self.adj[link["source"]].append(link)
                if link["source"] != link["target"]:
                    self.adj[link["target"]].append(link)

    def require(self, node_id):
        if node_id not in self.nodes:
            raise ValueError("Unknown node: " + node_id + ". Use search first.")
        return self.nodes[node_id]

    def card(self, node_id, brief=False):
        node = self.require(node_id)
        result = {"id": node_id, "label": node.get("label", node_id),
                  "status": node.get("status"), "parent": node.get("parent")}
        if node.get("human_edit") and not node["human_edit"].get("acknowledged"):
            result["human_pending"] = True
        if brief:
            return result
        result.update(summary=node.get("human", ""), paths=node.get("paths", []),
                      tests=node.get("tests", []), children=node.get("children", []),
                      at=node.get("at"), locked=node.get("locked", False), needs_review=node.get("needs_review", False))
        if node.get("human_edit"):
            result["human_edit"] = {key: value for key, value in node["human_edit"].items() if key != "changes"}
            result["human_edit"]["change_count"] = len(node["human_edit"].get("changes", []))
        art_keys = list(dict.fromkeys([key for key in [node.get("hero")] + node.get("arts", []) + [s.get("art") for s in node.get("sats", [])] if key]))
        if art_keys:
            result["arts"] = [{"key": key, **self.data.get("arts", {}).get(key, {})} for key in art_keys]
        return result

    def search(self, query):
        words = re.findall(r"\w+", query.casefold())
        if not words:
            raise ValueError("Search query must contain letters or digits.")
        ranked = []
        for key, node in self.nodes.items():
            fields = [(key, 10), (node.get("label", ""), 6),
                      (" ".join(node.get("paths", [])), 3),
                      (node.get("human", ""), 1)]
            scores = [sum(weight for value, weight in fields if word in value.casefold())
                      for word in words]
            if all(scores):
                ranked.append((sum(scores) + (100 if query.casefold() == key.casefold() else 0), key))
        return [self.card(key, brief=True) for _, key in sorted(ranked, key=lambda x: (-x[0], x[1]))]

    def owners(self, path):
        path = normalized(path)
        root = normalized(self.data.get("source", {}).get("project_root", ""))
        windows = bool(re.match(r"^[A-Za-z]:/", root))
        if windows:
            path, root = path.casefold(), root.casefold()
        if root and path.startswith(root + "/"):
            path = path[len(root) + 1:]
        elif path.startswith("/") or re.match(r"^[A-Za-z]:/", path):
            return []
        matches = []
        for key, node in self.nodes.items():
            prefixes = [normalized(p) for p in node.get("paths", []) + node.get("tests", [])]
            if windows:
                prefixes = [p.casefold() for p in prefixes]
            matched = [p for p in prefixes if path == p or path.startswith(p + "/") or p == "."]
            if matched:
                matches.append((max(map(len, matched)), key))
        return [self.card(key, brief=True) for _, key in sorted(matches, key=lambda x: (-x[0], x[1]))]

    def context(self, node_id, depth, direction, hierarchy, limit):
        self.require(node_id)
        queue = deque([(node_id, 0)])
        seen = {node_id}
        selected = []
        used_links = []
        seen_links = set()
        omitted = set()
        while queue:
            current, distance = queue.popleft()
            selected.append(self.card(current))
            if distance >= depth:
                continue
            for link in self.adj[current]:
                if not hierarchy and link.get("type") in ("subsystem", "primary_hierarchy", "roster_member"):
                    continue
                source, target = link["source"], link["target"]
                if direction == "out" and source != current:
                    continue
                if direction == "in" and target != current:
                    continue
                neighbor = target if source == current else source
                if neighbor not in seen:
                    if len(seen) >= limit:
                        omitted.add(neighbor)
                        continue
                    seen.add(neighbor)
                    queue.append((neighbor, distance + 1))
                signature = (source, target, link.get("type"), link.get("label", ""))
                if signature not in seen_links:
                    seen_links.add(signature)
                    used_links.append({k: link[k] for k in ("source", "target", "type", "label", "proposed") if k in link})
        return {"nodes": selected, "links": used_links, "node_limit_reached": bool(omitted)}


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def bounded(result, max_chars):
    """Drop complete records, never cut a JSON string in the middle."""
    result.setdefault("truncated", False)
    while True:
        page = None
        if "total" in result:
            page = next((key for key in ("nodes", "issues", "operations", "events", "changes") if key in result), "nodes")
            end = result["offset"] + len(result.get(page, []))
            result["next_offset"] = end if end < result["total"] else None
        if len(encode(result)) <= max_chars:
            return result
        result["truncated"] = True
        if len(result.get("nodes", [])) > 1:
            removed = result["nodes"].pop()["id"]
            if "links" in result:
                result["links"] = [link for link in result["links"]
                                   if removed not in (link["source"], link["target"])]
        elif result.get("links"):
            result["links"].pop()
        elif any(result.get(key) and (key != page or len(result[key]) > 1) for key in ("issues", "operations", "unresolved", "events", "changes")):
            key = next(key for key in ("unresolved", "events", "operations", "issues", "changes") if result.get(key) and (key != page or len(result[key]) > 1))
            result[key].pop()
        elif "diff" in result:
            # Preserve the transaction outcome even when its diff is too big.
            result["diff_summary"] = {key: len(value) for key, value in result.pop("diff").items()}
        else:
            # Preserve the requested node's identity. A single large card can
            # still exceed the budget; report this instead of hiding fields.
            if "saved" in result:
                return {"saved": result["saved"], "revision": result["revision"], "rebuilt": result.get("rebuilt", False), "truncated": True}
            return {"error": "Response exceeds budget. Increase --max-chars or narrow the query.",
                    "truncated": True, "ids": [n["id"][:80] for n in result.get("nodes", [])][:1]}


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--data", type=Path, default=Path(__file__).parent / "data" / "graph.json")
    cli.add_argument("--root", type=Path, help="tool directory containing graph_content.py and data/")
    cli.add_argument("--max-chars", type=positive, default=6000,
                     help="maximum JSON characters (minimum 512; not a token count)")
    commands = cli.add_subparsers(dest="command", required=True)
    for name in ("overview", "search", "path"):
        cmd = commands.add_parser(name)
        if name != "overview":
            cmd.add_argument("query")
        cmd.add_argument("--limit", type=positive, default=5)
        cmd.add_argument("--offset", type=int, default=0)
    commands.add_parser("node").add_argument("id")
    changes = commands.add_parser("human-changes")
    changes.add_argument("id")
    changes.add_argument("--limit", type=positive, default=5)
    changes.add_argument("--offset", type=int, default=0)
    context = commands.add_parser("context")
    context.add_argument("id")
    context.add_argument("--depth", type=int, choices=range(4), default=1)
    context.add_argument("--direction", choices=("in", "out", "both"), default="both")
    context.add_argument("--hierarchy", action="store_true", help="also follow parent/child edges")
    context.add_argument("--limit", type=positive, default=8)
    for name in ("health", "bootstrap"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--scope", required=name == "bootstrap", help="opt-in project-relative file scan")
        cmd.add_argument("--max-files", type=positive, default=2000)
        cmd.add_argument("--limit", type=positive, default=20)
        cmd.add_argument("--offset", type=int, default=0)
        if name == "bootstrap":
            cmd.add_argument("--parent", help="parent for suggested new nodes")
    history = commands.add_parser("history")
    history.add_argument("id", nargs="?")
    history.add_argument("--limit", type=positive, default=5)
    history.add_argument("--offset", type=int, default=0)
    for name in sorted(WRITES):
        cmd = commands.add_parser(name)
        cmd.add_argument("--rebuild", action="store_true")
        cmd.add_argument("--dry-run", action="store_true")
        cmd.add_argument("--expected-revision")
        cmd.add_argument("--summary", default="")
        if name == "apply":
            cmd.add_argument("--file", type=Path, required=True, help="JSON list or object with operations")
        elif name in ("add-link", "remove-link"):
            cmd.add_argument("source")
            cmd.add_argument("target")
            if name == "add-link":
                cmd.add_argument("--type", default="uses")
                cmd.add_argument("--label", default="")
        else:
            cmd.add_argument("id")
            if name == "acknowledge-node":
                cmd.add_argument("--token", required=True)
                cmd.add_argument("--note", required=True, help="what you saw and how you will handle the human changes")
            elif name == "set-status":
                from graph_store import STATUSES
                cmd.add_argument("status", choices=sorted(STATUSES))
            elif name != "remove-node":
                for field in ("label", "human", "status", "note"):
                    cmd.add_argument("--" + field)
                cmd.add_argument("--tier", type=int, required=name == "add-node")
                cmd.add_argument("--parent", required=name == "add-node")
                for field in ("paths", "tests"):
                    cmd.add_argument("--" + field, nargs="*")
                for field in ("needs-review", "locked"):
                    cmd.add_argument("--" + field, choices=("true", "false"))
    return cli


def run(args):
    if args.max_chars < 512:
        raise ValueError("--max-chars must be at least 512")
    root = args.root.resolve() if args.root else args.data.resolve().parent.parent
    if args.root:
        args.data = root / "data" / "graph.json"
    if args.command in WRITES:
        from graph_updates import apply_operations
        operation = {"op": args.command}
        if args.command == "apply":
            payload = json.loads(args.file.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict) and (payload.get("truncated") or payload.get("scan_incomplete") or payload.get("next_offset") is not None):
                raise ValueError("Do not apply an incomplete suggestion response; review and extract the intended operations explicitly")
            operations = payload.get("operations") if isinstance(payload, dict) else payload
        else:
            if hasattr(args, "id"):
                operation["id"] = args.id
            if args.command in ("update-node", "add-node"):
                fields = {field: getattr(args, field) for field in ("label", "human", "status", "note", "tier", "parent", "paths", "tests") if getattr(args, field) is not None}
                for field in ("locked", "needs_review"):
                    if getattr(args, field) is not None:
                        fields[field] = getattr(args, field) == "true"
                operation["node" if args.command == "add-node" else "fields"] = fields
            elif args.command == "set-status":
                operation["status"] = args.status
            elif args.command == "acknowledge-node":
                operation["token"] = args.token
                operation["note"] = args.note
            elif args.command in ("add-link", "remove-link"):
                operation.update(source=args.source, target=args.target)
                if args.command == "add-link":
                    operation.update(type=args.type, label=args.label)
            operations = [operation]
        return bounded(apply_operations(root, operations, args.rebuild, args.dry_run, args.expected_revision, args.summary), args.max_chars)
    if args.command == "history":
        if args.offset < 0:
            raise ValueError("--offset must be nonnegative")
        path = root / "graph_history.jsonl"
        from collections import deque
        selected = deque(maxlen=args.offset + args.limit)
        total = 0
        if path.exists():
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    event = json.loads(line)
                    diff = event.get("diff", {})
                    if args.id and not (any(n["id"] == args.id for n in diff.get("nodes", [])) or any(args.id in (l["source"], l["target"]) for l in diff.get("links_added", []) + diff.get("links_removed", []))):
                        continue
                    selected.append(event)
                    total += 1
        rows = list(reversed(selected))[args.offset:args.offset + args.limit]
        return bounded({"events": rows, "total": total, "offset": args.offset,
                        "revision": revision(root)}, args.max_chars)
    graph = Graph(args.data)
    result = {"built_at": graph.data.get("built_at")}
    folder = args.data.resolve().parent.parent
    result["config_newer_than_graph"] = any(
        config.exists() and config.stat().st_mtime > args.data.stat().st_mtime
        for config in (folder / "graph_content.py", folder / "graph_edit.json"))
    result["revision"] = revision(folder)
    built_revision = graph.data.get("source", {}).get("config_revision")
    result["rebuild_required"] = result["revision"] != built_revision if built_revision else result["config_newer_than_graph"]
    if args.command == "human-changes":
        if args.offset < 0:
            raise ValueError("--offset must be nonnegative")
        stamp = graph.require(args.id).get("human_edit") or {}
        rows = stamp.get("changes", [])
        result.update(id=args.id, human_edit={key: value for key, value in stamp.items() if key != "changes"},
                      changes=rows[args.offset:args.offset + args.limit], total=len(rows), offset=args.offset)
        return bounded(result, args.max_chars)
    if args.command in ("health", "bootstrap"):
        if args.offset < 0:
            raise ValueError("--offset must be nonnegative")
        from graph_health import bootstrap, health
        if args.command == "health":
            rows, incomplete = health(graph, args.scope, args.max_files)
            if result["rebuild_required"]:
                rows.insert(0, {"kind": "rebuild_required"})
            field = "issues"
        else:
            if result["rebuild_required"]:
                raise ValueError("Rebuild the graph before generating bootstrap suggestions")
            rows, unresolved, incomplete = bootstrap(graph, args.scope, args.parent, args.max_files)
            result["unresolved"] = unresolved[:args.limit]
            result["unresolved_total"] = len(unresolved)
            field = "operations"
            result["advisory_only"] = True
        result.update({field: rows[args.offset:args.offset + args.limit], "total": len(rows),
                       "offset": args.offset, "scan_incomplete": incomplete})
        return bounded(result, args.max_chars)
    if args.command in ("overview", "search", "path"):
        if args.offset < 0:
            raise ValueError("--offset must be nonnegative")
        if args.command == "overview":
            rows = [graph.card(key, brief=True) for key, node in graph.nodes.items() if node.get("tier", 2) <= 1]
        elif args.command == "search":
            rows = graph.search(args.query)
        else:
            rows = graph.owners(args.query)
        result.update(total=len(rows), offset=args.offset, nodes=rows[args.offset:args.offset + args.limit])
    elif args.command == "node":
        result["nodes"] = [graph.card(args.id)]
    else:
        result.update(graph.context(args.id, args.depth, args.direction, args.hierarchy, args.limit))
    return bounded(result, args.max_chars)


def main():
    args = parser().parse_args()
    if args.max_chars < 512:
        parser().error("--max-chars must be at least 512")
    try:
        result = run(args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(encode({"error": str(error)[:300], "hint": "Run python -X utf8 build_graph.py to rebuild data."}))
        return 1
    print(encode(result))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
