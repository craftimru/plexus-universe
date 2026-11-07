import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from graph_agent import Graph, bounded, encode, parser, run


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "data" / "graph.json"
        self.path.parent.mkdir()
        self.payload = {
            "built_at": 123, "source": {"project_root": "D:/Game"},
            "nodes": [
                {"id": "root", "label": "Game", "tier": 0, "parent": None, "children": ["combat", "ui"]},
                {"id": "combat", "label": "Бой", "tier": 1, "parent": "root",
                 "human": "Урон и броня", "paths": ["src/combat/"], "tests": ["tests/combat.py"]},
                {"id": "ui", "label": "HUD", "tier": 1, "parent": "root", "paths": ["src/ui.gd"]},
                {"id": "damage", "label": "Damage", "tier": 2, "parent": "combat",
                 "paths": ["src/combat/damage.gd"]},
            ],
            "links": [
                {"source": "root", "target": "combat", "type": "subsystem"},
                {"source": "combat", "target": "damage", "type": "calls"},
                {"source": "damage", "target": "ui", "type": "writes"},
                {"source": "ui", "target": "combat", "type": "reads_state"},
            ],
        }
        self.path.write_text(json.dumps(self.payload), encoding="utf-8")
        self.graph = Graph(self.path)

    def test_search_unicode_multiple_terms_and_paths(self):
        self.assertEqual(self.graph.search("БОЙ броня")[0]["id"], "combat")
        self.assertEqual(self.graph.search("damage")[0]["id"], "damage")
        self.assertEqual(self.graph.search("nothing"), [])

    def test_path_matches_boundaries_and_specific_owner_first(self):
        self.assertEqual([n["id"] for n in self.graph.owners(r"D:\Game\src\combat\damage.gd")], ["damage", "combat"])
        self.assertEqual(self.graph.owners("src/combat_extra/file.gd"), [])
        self.assertEqual(self.graph.owners("tests/combat.py")[0]["id"], "combat")
        self.assertEqual(self.graph.owners(r"d:\GAME\SRC\COMBAT\damage.gd")[0]["id"], "damage")
        self.assertEqual(self.graph.owners("D:/Other/src/combat/damage.gd"), [])

    def test_directions_and_depth(self):
        incoming = self.graph.context("combat", 1, "in", False, 8)
        outgoing = self.graph.context("combat", 1, "out", False, 8)
        self.assertEqual([n["id"] for n in incoming["nodes"]], ["combat", "ui"])
        self.assertEqual([n["id"] for n in outgoing["nodes"]], ["combat", "damage"])
        self.assertEqual(len(self.graph.context("combat", 0, "both", True, 8)["nodes"]), 1)

    def test_cycles_hierarchy_and_node_limit(self):
        result = self.graph.context("combat", 3, "both", True, 2)
        self.assertEqual(len(result["nodes"]), 2)
        self.assertTrue(result["node_limit_reached"])
        full = self.graph.context("combat", 3, "both", True, 20)
        self.assertEqual(len(full["nodes"]), 4)
        self.assertEqual(len(full["links"]), 4)

    def test_budget_keeps_valid_json_and_links_within_selected_nodes(self):
        result = bounded(self.graph.context("combat", 3, "both", True, 8), 512)
        self.assertLessEqual(len(encode(result)), 512)
        self.assertTrue(result["truncated"])
        ids = {n["id"] for n in result["nodes"]}
        self.assertIn("combat", ids)
        self.assertTrue(all(l["source"] in ids and l["target"] in ids for l in result["links"]))

    def test_oversized_card_reports_error_instead_of_silently_losing_paths(self):
        result = bounded({"nodes": [{"id": "big", "paths": ["x" * 10000]}]}, 512)
        self.assertIn("error", result)
        self.assertLessEqual(len(encode(result)), 512)

    def test_pagination_after_budget_trimming(self):
        for node in self.payload["nodes"]:
            node["label"] += "x" * 150
        self.path.write_text(json.dumps(self.payload), encoding="utf-8")
        ids = []
        offset = 0
        while True:
            args = parser().parse_args(["--data", str(self.path), "--max-chars", "512", "overview", "--offset", str(offset)])
            result = run(args)
            self.assertLessEqual(len(encode(result)), 512)
            ids.extend(n["id"] for n in result["nodes"])
            if result["next_offset"] is None:
                break
            self.assertGreater(result["next_offset"], offset)
            offset = result["next_offset"]
        self.assertEqual(ids, ["root", "combat", "ui"])

    def test_config_freshness_and_no_execution(self):
        config = self.path.parent.parent / "graph_content.py"
        config.write_text("raise RuntimeError('must not execute')", encoding="utf-8")
        import os
        os.utime(config, (self.path.stat().st_mtime + 10,) * 2)
        args = parser().parse_args(["--data", str(self.path), "node", "combat"])
        self.assertTrue(run(args)["config_newer_than_graph"])
        config.unlink()
        snapshot = self.path.parent.parent / "graph_edit.json"
        snapshot.write_text("{}", encoding="utf-8")
        os.utime(snapshot, (self.path.stat().st_mtime + 10,) * 2)
        self.assertTrue(run(args)["config_newer_than_graph"])

    def test_missing_node_and_bad_data_are_actionable_cli_errors(self):
        script = Path(__file__).resolve().parents[1] / "graph_agent.py"
        result = subprocess.run([sys.executable, "-X", "utf8", str(script), "--data", str(self.path), "node", "missing"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unknown node", json.loads(result.stdout)["error"])
        self.path.write_text("{broken", encoding="utf-8")
        result = subprocess.run([sys.executable, "-X", "utf8", str(script), "--data", str(self.path), "overview"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1)
        self.assertIn("error", json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
