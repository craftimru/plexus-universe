"""Query the local graph without sending the whole index to an agent.

Only reads data/graph.json; never imports project configuration or source files.
"""
import argparse
from collections import deque
import json
from pathlib import Path
import re
import sys


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
        if brief:
            return result
        result.update(summary=node.get("human", ""), paths=node.get("paths", []),
                      tests=node.get("tests", []), children=node.get("children", []),
                      at=node.get("at"))
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
    result["truncated"] = False
    while True:
        if "total" in result:
            end = result["offset"] + len(result["nodes"])
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
        else:
            # Preserve the requested node's identity. A single large card can
            # still exceed the budget; report this instead of hiding fields.
            return {"error": "Response exceeds budget. Increase --max-chars or use search.",
                    "truncated": True, "ids": [n["id"][:80] for n in result.get("nodes", [])][:1]}


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--data", type=Path, default=Path(__file__).parent / "data" / "graph.json")
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
    context = commands.add_parser("context")
    context.add_argument("id")
    context.add_argument("--depth", type=int, choices=range(4), default=1)
    context.add_argument("--direction", choices=("in", "out", "both"), default="both")
    context.add_argument("--hierarchy", action="store_true", help="also follow parent/child edges")
    context.add_argument("--limit", type=positive, default=8)
    return cli


def run(args):
    graph = Graph(args.data)
    result = {"built_at": graph.data.get("built_at")}
    folder = args.data.resolve().parent.parent
    result["config_newer_than_graph"] = any(
        config.exists() and config.stat().st_mtime > args.data.stat().st_mtime
        for config in (folder / "graph_content.py", folder / "graph_edit.json"))
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
