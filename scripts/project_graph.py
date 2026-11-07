"""Locate a project's own map, or initialize one from the bundled runtime."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from skill_bundle import ROOT, files


def locate(project):
    project = Path(project).resolve()
    candidates = [project, project / "tools" / "project_graph", project / "tools" / "plexus-universe", project / "tools" / "project-universe-graph", project / ".project_graph"]
    return [str(path) for path in candidates if (path / "graph_content.py").is_file() and (path / "graph_agent.py").is_file()]


def initialize(project, relative="tools/project_graph", name=None, root=ROOT):
    project = Path(project).resolve()
    if not project.is_dir():
        raise ValueError("Project directory must already exist")
    destination = (project / relative).resolve()
    if destination == project or not destination.is_relative_to(project):
        raise ValueError("Map destination must be a subdirectory of the project")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Map destination is not empty; locate and use the existing map instead")
    destination.mkdir(parents=True, exist_ok=True)
    for relative_file in files(root):
        if relative_file != "graph_content.py" and not relative_file.startswith("data/"):
            target = destination / relative_file
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / relative_file, target)
    project_relative = os.path.relpath(project, destination).replace("\\", "/")
    config = (
        "from pathlib import Path\n"
        "PROJECT_ROOT = str((Path(__file__).resolve().parent / " + repr(project_relative) + ").resolve())\n"
        "PROJECT_NAME = " + repr(name or project.name) + "\n"
        "ENGINE_VERSION = ''\nFRESH_HOURS = 48\nFAMILY = {'engine_core': '#ffe39a'}\n"
        "NODES = {'engine_core': {'label': PROJECT_NAME, 'tier': 0, 'parent': None, 'status': 'idea', "
        "'human': 'Карта проекта; добавьте разделы и уточните их ответственность.', 'paths': [], 'tests': []}}\n"
        "LINKS = []\nCUSTOM_ARTS = []\n"
    )
    (destination / "graph_content.py").write_text(config, encoding="utf-8")
    result = subprocess.run([sys.executable, "-X", "utf8", str(destination / "build_graph.py")],
                            cwd=destination, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=60)
    if result.returncode:
        raise ValueError("Initial graph build failed: " + (result.stderr or result.stdout)[-1000:])
    return destination


def update_map(destination, root=ROOT):
    """Update runtime only, retaining configuration, history, assets and cache."""
    destination = Path(destination).resolve()
    if destination == root.resolve():
        raise ValueError("Update a project map, not the source skill checkout itself")
    if not (destination / "graph_content.py").is_file() or not (destination / "graph_agent.py").is_file():
        raise ValueError("Destination must be an existing map directory")
    sys.path.insert(0, str(root))
    from graph_store import atomic_write, write_lock
    selected = [name for name in files(root) if name != "graph_content.py" and not name.startswith("data/")]
    paths = [destination / name for name in selected] + [destination / "data" / name for name in ("graph.js", "graph.json", "context_nodes.json", "freshness.json")]
    with write_lock(destination):
        before = {p: p.read_bytes() if p.exists() else None for p in paths}
        try:
            for name in selected:
                atomic_write(destination / name, (root / name).read_bytes())
            result = subprocess.run([sys.executable, "-X", "utf8", str(destination / "build_graph.py")],
                cwd=destination, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=60)
            if result.returncode:
                raise ValueError("Updated builder failed: " + (result.stderr or result.stdout)[-1000:])
        except Exception:
            for path, data in before.items():
                if data is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(path, data)
            raise
    return destination


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    for name in ("locate", "init"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--project", type=Path, required=True)
        if name == "init":
            cmd.add_argument("--relative", default="tools/project_graph")
            cmd.add_argument("--name")
    sub.add_parser("update").add_argument("--map", type=Path, required=True)
    args = cli.parse_args()
    try:
        if args.command == "locate":
            result = {"maps": locate(args.project)}
        elif args.command == "update":
            result = {"updated": True, "tool_root": str(update_map(args.map)), "data_preserved": True}
        else:
            result = {"tool_root": str(initialize(args.project, args.relative, args.name))}
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
