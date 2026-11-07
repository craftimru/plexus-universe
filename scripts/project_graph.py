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
    candidates = [project, project / "tools" / "project_graph", project / "tools" / "project-universe-graph", project / ".project_graph"]
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


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    for name in ("locate", "init"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--project", type=Path, required=True)
        if name == "init":
            cmd.add_argument("--relative", default="tools/project_graph")
            cmd.add_argument("--name")
    args = cli.parse_args()
    try:
        result = {"maps": locate(args.project)} if args.command == "locate" else {"tool_root": str(initialize(args.project, args.relative, args.name))}
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
