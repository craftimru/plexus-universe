"""Optional stdio MCP adapter. Core behavior lives in graph_agent/graph_updates."""
import argparse
import contextlib
import io
from pathlib import Path
import sys

from graph_agent import bounded, encode, parser, run
from graph_updates import apply_operations


def create_server(root, allow_write=False):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as error:
        raise RuntimeError("MCP needs Python 3.10+ and: python -m pip install -r requirements-mcp.txt") from error
    root = Path(root).resolve()
    mcp = FastMCP("project-universe-graph")

    def query(arguments, max_chars):
        if not 512 <= max_chars <= 100000:
            raise ValueError("max_chars must be 512..100000")
        errors = io.StringIO()
        try:
            with contextlib.redirect_stderr(errors):
                args = parser().parse_args(["--root", str(root), "--max-chars", str(max_chars)] + arguments)
        except SystemExit:
            raise ValueError(errors.getvalue()[-500:])
        return encode(run(args))

    @mcp.tool()
    def graph_search(query_text: str, limit: int = 5, offset: int = 0, max_chars: int = 6000) -> str:
        """Find brief node cards by ID, label, description and source paths."""
        return query(["search", query_text, "--limit", str(limit), "--offset", str(offset)], max_chars)

    @mcp.tool()
    def graph_node(node_id: str, max_chars: int = 6000) -> str:
        """Read one node's summary, files, tests, children and agent flags."""
        return query(["node", node_id], max_chars)

    @mcp.tool()
    def graph_human_changes(node_id: str, limit: int = 5, offset: int = 0, max_chars: int = 6000) -> str:
        """Read paged before/after human edits. Tell the user what you saw and how you will handle it before acknowledging."""
        return query(["human-changes", node_id, "--limit", str(limit), "--offset", str(offset)], max_chars)

    @mcp.tool()
    def graph_context(node_id: str, depth: int = 1, direction: str = "both", hierarchy: bool = False, limit: int = 8, max_chars: int = 6000) -> str:
        """Read bounded dependencies around a node; hierarchy is opt-in."""
        if direction not in ("in", "out", "both") or depth not in range(4) or limit < 1:
            raise ValueError("Invalid context options")
        arguments = ["context", node_id, "--depth", str(depth), "--direction", direction, "--limit", str(limit)]
        if hierarchy:
            arguments.append("--hierarchy")
        return query(arguments, max_chars)

    @mcp.tool()
    def graph_path(file_path: str, limit: int = 5, offset: int = 0, max_chars: int = 6000) -> str:
        """Find nodes covering a source or test file; most specific first."""
        return query(["path", file_path, "--limit", str(limit), "--offset", str(offset)], max_chars)

    @mcp.tool()
    def graph_health(scope: str = "", limit: int = 20, offset: int = 0, max_chars: int = 6000) -> str:
        """Report missing paths, broken graph references and review flags. Optional scope scans up to 2000 files for gaps."""
        arguments = ["health", "--limit", str(limit), "--offset", str(offset)]
        if scope:
            arguments += ["--scope", scope]
        return query(arguments, max_chars)

    @mcp.tool()
    def graph_overview(limit: int = 5, offset: int = 0, max_chars: int = 6000) -> str:
        """Read paged root and top-level sections."""
        return query(["overview", "--limit", str(limit), "--offset", str(offset)], max_chars)

    @mcp.tool()
    def graph_bootstrap(scope: str, parent: str = "", limit: int = 20, offset: int = 0, max_chars: int = 6000) -> str:
        """Suggest a reviewable patch from file groups and @orbit markers; does not write."""
        arguments = ["bootstrap", "--scope", scope, "--limit", str(limit), "--offset", str(offset)]
        if parent:
            arguments += ["--parent", parent]
        return query(arguments, max_chars)

    if allow_write:
        @mcp.tool()
        def graph_apply(operations: list[dict], expected_revision: str, summary: str = "", rebuild: bool = True, dry_run: bool = False, max_chars: int = 6000) -> str:
            """Apply validated node/link operations atomically with revision and locked-node checks. Use dry_run for preview."""
            if not 512 <= max_chars <= 100000:
                raise ValueError("max_chars must be 512..100000")
            return encode(bounded(apply_operations(root, operations, rebuild, dry_run, expected_revision, summary), max_chars))
    return mcp


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, default=Path(__file__).parent)
    cli.add_argument("--allow-write", action="store_true", help="expose graph_apply; defaults to read-only tools")
    args = cli.parse_args()
    try:
        server = create_server(args.root, args.allow_write)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
