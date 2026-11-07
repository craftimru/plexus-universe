import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from skill_bundle import files, install, package
from project_graph import initialize, locate


class SkillPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_bundle_is_self_contained_without_user_edits_or_caches(self):
        output = package(self.root / "project-universe-graph.skill")
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
            self.assertIn("project-universe-graph/SKILL.md", names)
            self.assertIn("project-universe-graph/agents/openai.yaml", names)
            self.assertIn("project-universe-graph/scripts/project_graph.py", names)
            self.assertFalse(any(".git/" in n or "__pycache__" in n or "graph_edit.json" in n or "graph_history.jsonl" in n for n in names))
            archive.extractall(self.root / "unpacked")
        installed = self.root / "unpacked" / "project-universe-graph"
        self.assertEqual(set(files(installed)), set(files()))

    def test_install_does_not_overwrite_existing_skill(self):
        destination = install(self.root / "installed")
        original = (destination / "SKILL.md").read_bytes()
        with self.assertRaises(ValueError):
            install(destination)
        self.assertEqual(original, (destination / "SKILL.md").read_bytes())

    def test_installed_skill_initializes_project_map_instead_of_copying_demo(self):
        skill = install(self.root / "installed")
        project = self.root / "My Game"
        project.mkdir()
        source = project / "game.gd"
        source.write_text("extends Node", encoding="utf-8")
        command = [sys.executable, "-X", "utf8", str(skill / "scripts" / "project_graph.py")]
        before = subprocess.run(command + ["locate", "--project", str(project)], capture_output=True, text=True, encoding="utf-8", check=True)
        self.assertEqual(json.loads(before.stdout)["maps"], [])
        result = subprocess.run(command + ["init", "--project", str(project)], capture_output=True, text=True, encoding="utf-8", check=True)
        tool = Path(json.loads(result.stdout)["tool_root"])
        graph = json.loads((tool / "data" / "graph.json").read_text(encoding="utf-8"))
        self.assertEqual(graph["project"], "My Game")
        self.assertEqual(len(graph["nodes"]), 1)
        self.assertEqual(Path(graph["source"]["project_root"]).resolve(), project.resolve())
        self.assertEqual(source.read_text(encoding="utf-8"), "extends Node")
        self.assertEqual(locate(project), [str(tool)])
        with self.assertRaises(ValueError):
            initialize(project)
        with self.assertRaises(ValueError):
            initialize(project, "../outside")


if __name__ == "__main__":
    unittest.main()
