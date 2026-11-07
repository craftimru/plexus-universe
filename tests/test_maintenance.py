import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from graph_agent import Graph, bounded, encode, parser, run
from graph_health import bootstrap, health
from graph_store import Conflict, load_document, revision, save_document, write_lock
from graph_updates import apply_operations

REPO = Path(__file__).resolve().parents[1]


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("build_graph.py", "graph_store.py"):
            shutil.copy2(REPO / name, self.root)
        self.doc = {"PROJECT_NAME": "Test", "FAMILY": {"engine_core": "#ffe39a"},
                    "NODES": {
                        "engine_core": {"label": "Root", "tier": 0, "parent": None, "status": "wip", "paths": []},
                        "combat": {"label": "Combat", "tier": 1, "parent": "engine_core", "status": "proto", "paths": ["src/combat.gd"], "tests": []}},
                    "LINKS": []}
        config = "from pathlib import Path\nPROJECT_ROOT = str(Path(__file__).parent)\n" + "\n".join(key + " = " + repr(value) for key, value in self.doc.items())
        (self.root / "graph_content.py").write_text(config, encoding="utf-8")
        (self.root / "src").mkdir()
        (self.root / "src" / "combat.gd").write_text("extends Node\n", encoding="utf-8")
        self.build()

    def build(self):
        subprocess.run([sys.executable, "-X", "utf8", str(self.root / "build_graph.py")], check=True, capture_output=True)

    def query(self, *arguments):
        return run(parser().parse_args(["--root", str(self.root), *arguments]))

    def test_batch_add_update_links_build_and_history(self):
        before = revision(self.root)
        result = apply_operations(self.root, [
            {"op": "add-node", "id": "damage", "node": {"tier": 2, "parent": "combat", "paths": ["src/damage.gd"]}},
            {"op": "add-link", "source": "combat", "target": "damage", "type": "calls"},
            {"op": "set-status", "id": "combat", "status": "live"},
        ], rebuild=True, expected_revision=before, summary="Implement damage")
        self.assertTrue(result["saved"])
        self.assertEqual(self.query("node", "damage")["nodes"][0]["parent"], "combat")
        self.assertFalse(self.query("overview")["rebuild_required"])
        self.assertEqual(self.query("history", "damage")["events"][0]["actor"], "agent")
        self.assertEqual(self.query("history", "damage")["events"][0]["summary"], "Implement damage")
        self.assertEqual(len(result["diff"]["nodes"]), 2)

    def test_dry_run_noop_and_validation_leave_no_snapshot_or_history(self):
        before = revision(self.root)
        operation = {"op": "set-status", "id": "combat", "status": "live"}
        result = apply_operations(self.root, [operation], dry_run=True)
        self.assertFalse(result["saved"])
        self.assertEqual(revision(self.root), before)
        for name in ("graph_edit.json", "graph_history.jsonl", "graph_write.lock"):
            self.assertFalse((self.root / name).exists())
        result = apply_operations(self.root, [{**operation, "status": "proto"}])
        self.assertTrue(result["unchanged"])
        with self.assertRaises(ValueError):
            apply_operations(self.root, [operation, {"op": "add-link", "source": "combat", "target": "missing"}])
        self.assertEqual(revision(self.root), before)

    def test_revision_and_concurrent_writer_prevent_overwrite(self):
        before = revision(self.root)
        operation = {"op": "set-status", "id": "combat", "status": "live"}
        apply_operations(self.root, [operation])
        with self.assertRaises(Conflict):
            apply_operations(self.root, [operation], expected_revision=before)
        with write_lock(self.root), self.assertRaises(Conflict):
            apply_operations(self.root, [{**operation, "status": "wip"}])
        self.assertFalse((self.root / "graph_write.lock").exists())

    def test_locked_node_links_and_parent_edges_resist_agent_changes_but_human_can_unlock(self):
        doc = load_document(self.root)
        doc["NODES"]["combat"]["locked"] = True
        save_document(self.root, doc, revision(self.root))
        operations = [
            {"op": "update-node", "id": "combat", "fields": {"locked": False, "status": "live"}},
            {"op": "add-link", "source": "engine_core", "target": "combat"},
            {"op": "add-node", "id": "new", "node": {"parent": "combat", "tier": 2}},
            {"op": "remove-node", "id": "combat"},
        ]
        for operation in operations:
            with self.subTest(op=operation), self.assertRaises(ValueError):
                apply_operations(self.root, [operation])
        doc["NODES"]["combat"]["locked"] = False
        save_document(self.root, doc, revision(self.root))
        stamp = load_document(self.root)["NODES"]["combat"]["human_edit"]
        apply_operations(self.root, [{"op": "acknowledge-node", "id": "combat", "token": stamp["token"], "note": "Read the human unlock and preserve existing wording"}])
        self.assertTrue(apply_operations(self.root, [{"op": "set-status", "id": "combat", "status": "live"}])["saved"])

    def test_human_changes_require_matching_acknowledgement_and_reset_on_next_edit(self):
        doc = load_document(self.root)
        doc["NODES"]["combat"]["human"] = "Human wording must survive"
        save_document(self.root, doc, revision(self.root))
        node = self.query("node", "combat")["nodes"][0]
        self.assertTrue(node["human_pending"])
        token = node["human_edit"]["token"]
        change = self.query("human-changes", "combat")["changes"][0]
        self.assertEqual(change["before"], None)
        self.assertEqual(change["after"], "Human wording must survive")
        with self.assertRaises(ValueError):
            apply_operations(self.root, [{"op": "set-status", "id": "combat", "status": "live"}])
        with self.assertRaises(ValueError):
            apply_operations(self.root, [{"op": "acknowledge-node", "id": "combat", "token": "wrong", "note": "Read old version"}])
        with self.assertRaises(ValueError):
            apply_operations(self.root, [{"op": "acknowledge-node", "id": "combat", "token": token}])
        apply_operations(self.root, [{"op": "acknowledge-node", "id": "combat", "token": token, "note": "I read the human wording and will preserve it while updating status"}], rebuild=True)
        apply_operations(self.root, [{"op": "set-status", "id": "combat", "status": "live"}], rebuild=True)
        self.assertEqual(self.query("node", "combat")["nodes"][0]["summary"], "Human wording must survive")
        doc = load_document(self.root)
        doc["NODES"]["combat"]["note"] = "Another edit"
        save_document(self.root, doc, revision(self.root))
        self.assertNotEqual(self.query("node", "combat")["nodes"][0]["human_edit"]["token"], token)
        with self.assertRaises(ValueError):
            apply_operations(self.root, [{"op": "acknowledge-node", "id": "combat", "token": token, "note": "I read the human wording and will preserve it while updating status"}])

    def test_unread_human_changes_accumulate_across_saves(self):
        doc = load_document(self.root)
        doc["NODES"]["combat"]["human"] = "First human wording"
        save_document(self.root, doc, revision(self.root))
        doc = load_document(self.root)
        doc["NODES"]["combat"]["human"] = "Final human wording"
        doc["NODES"]["combat"]["note"] = "Keep this detail"
        save_document(self.root, doc, revision(self.root))
        changes = {c["field"]: c for c in self.query("human-changes", "combat")["changes"]}
        self.assertEqual(changes["human"]["before"], None)
        self.assertEqual(changes["human"]["after"], "Final human wording")
        self.assertEqual(changes["note"]["after"], "Keep this detail")

    def test_human_text_links_and_new_nodes_are_all_visible_to_agent(self):
        doc = load_document(self.root)
        doc["NODES"]["combat"]["human"] = "Human instruction"
        doc["NODES"]["new"] = {"label": "New by human", "tier": 2, "parent": "combat", "status": "idea"}
        doc["LINKS"].append({"source": "engine_core", "target": "combat", "type": "uses"})
        save_document(self.root, doc, revision(self.root))
        changes = {c["field"] for c in self.query("human-changes", "combat")["changes"]}
        self.assertIn("human", changes)
        self.assertIn("links_or_children", changes)
        self.assertTrue(self.query("node", "new")["nodes"][0]["human_pending"])

    def test_shared_art_caption_marks_affected_nodes_and_stale_browser_cannot_erase_stamp(self):
        doc = load_document(self.root)
        doc["CUSTOM_ARTS"] = [{"key": "concept", "path": "missing.jpg", "caption": "Old"}]
        doc["NODES"]["combat"]["arts"] = ["concept"]
        save_document(self.root, doc, revision(self.root))
        doc = load_document(self.root)
        old = doc["NODES"]["combat"]["human_edit"]["token"]
        doc["CUSTOM_ARTS"][0]["caption"] = "Human caption"
        doc["NODES"]["combat"].pop("human_edit")
        save_document(self.root, doc, revision(self.root))
        stamp = self.query("node", "combat")["nodes"][0]["human_edit"]
        self.assertNotEqual(stamp["token"], old)
        self.assertIn("art_content", stamp["fields"])
        with self.assertRaises(ValueError):
            apply_operations(self.root, [{"op": "add-link", "source": "engine_core", "target": "combat"}])

    def test_node_removal_requires_leaf_and_removes_explicit_links(self):
        apply_operations(self.root, [
            {"op": "add-node", "id": "damage", "node": {"parent": "combat", "tier": 2}},
            {"op": "add-link", "source": "engine_core", "target": "damage"},
        ])
        with self.assertRaises(ValueError):
            apply_operations(self.root, [{"op": "remove-node", "id": "combat"}])
        result = apply_operations(self.root, [{"op": "remove-node", "id": "damage"}])
        self.assertEqual(len(result["diff"]["links_removed"]), 1)

    def test_no_rebuild_is_detected_even_with_same_mtime(self):
        apply_operations(self.root, [{"op": "set-status", "id": "combat", "status": "live"}])
        snapshot = self.root / "graph_edit.json"
        old_time = (self.root / "data" / "graph.json").stat().st_mtime - 10
        os.utime(snapshot, (old_time, old_time))
        self.assertTrue(self.query("node", "combat")["rebuild_required"])
        self.assertEqual(self.query("health")["issues"][0]["kind"], "rebuild_required")
        with self.assertRaises(ValueError):
            self.query("bootstrap", "--scope", "src", "--parent", "engine_core")

    def test_failed_build_restores_history_backup_snapshot_and_generated_data(self):
        operation = {"op": "set-status", "id": "combat", "status": "live"}
        apply_operations(self.root, [operation], rebuild=True)
        apply_operations(self.root, [{**operation, "status": "wip"}], rebuild=True)
        files = [self.root / name for name in ("graph_edit.json", "graph_edit.json.bak", "graph_history.jsonl")] + list((self.root / "data").iterdir())
        before = {path: path.read_bytes() for path in files}
        (self.root / "build_graph.py").write_text("from pathlib import Path\nPath('data/graph.js').write_text('bad')\nraise RuntimeError('fail')", encoding="utf-8")
        with self.assertRaises(ValueError):
            apply_operations(self.root, [operation], rebuild=True)
        self.assertEqual(before, {path: path.read_bytes() for path in files})

    def test_health_missing_tests_broken_links_and_opt_in_scanning(self):
        (self.root / "src" / "combat.gd").unlink()
        (self.root / "src" / "new.gd").write_text("extends Node", encoding="utf-8")
        graph = Graph(self.root / "data" / "graph.json")
        graph.nodes["combat"]["tests"] = ["tests/missing.py"]
        graph.nodes["combat"]["needs_review"] = True
        graph.links.append({"source": "combat", "target": "unknown"})
        issues, _ = health(graph)
        self.assertEqual(sum(i["kind"] == "missing_path" for i in issues), 2)
        self.assertIn("broken_link", {i["kind"] for i in issues})
        self.assertNotIn("unmapped_file", {i["kind"] for i in issues})
        issues, incomplete = health(graph, "src", 1)
        self.assertIn("unmapped_file", {i["kind"] for i in issues})
        self.assertFalse(incomplete)
        with self.assertRaises(ValueError):
            health(graph, "../")

    def test_bootstrap_markers_and_folders_are_advisory_and_applyable(self):
        (self.root / "src" / "one.py").write_text("# @orbit: combat\n", encoding="utf-8")
        (self.root / "src" / "two.gd").write_text("# @orbit: navigation\n", encoding="utf-8")
        before = revision(self.root)
        graph = Graph(self.root / "data" / "graph.json")
        operations, unresolved, incomplete = bootstrap(graph, "src", "engine_core")
        self.assertEqual(revision(self.root), before)
        self.assertFalse((self.root / "graph_edit.json").exists())
        self.assertFalse(incomplete)
        self.assertEqual(unresolved, [])
        apply_operations(self.root, operations, dry_run=True)
        apply_operations(self.root, operations, rebuild=True)
        self.assertTrue(self.query("node", "navigation")["nodes"][0]["needs_review"])
        self.assertIn("src/one.py", self.query("node", "combat")["nodes"][0]["paths"])

    def test_bounded_pages_never_return_a_nonadvancing_next_offset(self):
        for field in ("issues", "operations", "events"):
            result = bounded({"total": 1, "offset": 0, field: [{"text": "x" * 2000}]}, 512)
            self.assertIn("error", result)
            self.assertLessEqual(len(encode(result)), 512)
        result = bounded({"saved": True, "revision": "x", "rebuilt": True,
                          "diff": {"nodes": [{"id": "a"}] * 300, "links_added": [], "links_removed": [], "settings": []}}, 512)
        self.assertTrue(result["saved"])
        self.assertEqual(result["diff_summary"]["nodes"], 300)

    def test_cli_writes_and_validation_error_exit_status(self):
        command = [sys.executable, "-X", "utf8", str(REPO / "graph_agent.py"), "--root", str(self.root)]
        result = subprocess.run(command + ["update-node", "combat", "--human", "New summary", "--paths", "src/combat.gd", "--rebuild"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["saved"])
        result = subprocess.run(command + ["remove-node", "engine_core"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1)
        self.assertIn("error", json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
