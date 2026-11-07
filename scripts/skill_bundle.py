"""Build or install a self-contained skill; never include working graph edits."""
import argparse
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "plexus-universe"
RUNTIME = (
    "build_graph.py", "edit_graph.py", "edit_graph.bat", "editor.html", "editor.js",
    "graph_agent.py", "graph_store.py", "graph_health.py", "graph_updates.py", "graph_mcp.py",
    "graph_content.py", "graph_content.example.py", "index.html", "viewer.js", "three.min.js",
    "open_graph.bat", "requirements-mcp.txt",
)


def files(root=ROOT):
    paths = ["SKILL.md", "agents/openai.yaml", *RUNTIME,
             "data/graph.js", "data/graph.json", "data/context_nodes.json"]
    paths += [str(path.relative_to(root)).replace("\\", "/") for folder, pattern in (("references", "*.md"), ("scripts", "*.py"))
              for path in sorted((root / folder).glob(pattern))]
    for path in paths:
        if not (root / path).is_file():
            raise ValueError("Missing bundled file: " + path)
    return paths


def install(destination, root=ROOT):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Skill destination already exists; preserve it or choose another destination")
    selected = files(root)
    destination.mkdir(parents=True)
    for relative in selected:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    return destination


def package(output, root=ROOT):
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for relative in files(root):
            archive.write(root / relative, NAME + "/" + relative)
    return output


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    sub.add_parser("package").add_argument("--output", type=Path, required=True)
    sub.add_parser("install").add_argument("--destination", type=Path,
        default=Path.home() / ".codex" / "skills" / NAME)
    args = cli.parse_args()
    try:
        result = package(args.output) if args.command == "package" else install(args.destination)
    except (OSError, ValueError) as error:
        cli.exit(1, str(error) + "\n")
    print(result)


if __name__ == "__main__":
    main()
