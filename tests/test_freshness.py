import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from graph_store import load_document, revision, save_document
from graph_updates import apply_operations

REPO = Path(__file__).resolve().parents[1]


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = int(time.time()) - 7 * 86400
        for name in ("build_graph.py", "graph_store.py"):
            shutil.copy2(REPO / name, self.root)
        self.doc = {"NODES": {
            "engine_core": {"tier": 0, "parent": None, "label": "Project"},
            "pillar": {"tier": 1, "parent": "engine_core", "label": "Pillar"},
            "system": {"tier": 2, "parent": "pillar", "label": "System"},
            "entity": {"tier": 3, "parent": "system", "label": "Entity", "human": "Original", "tests": ["test.gd"]},
            "other": {"tier": 1, "parent": "engine_core", "label": "Untouched"}}, "LINKS": []}
        config = "from pathlib import Path\nPROJECT_ROOT = str(Path(__file__).parent)\n" + "\n".join(k + " = " + repr(v) for k, v in self.doc.items())
        self.config = self.root / "graph_content.py"
        self.config.write_text(config, encoding="utf-8")
        (self.root / "test.gd").write_text("extends Node", encoding="utf-8")
        os.utime(self.config, (self.old, self.old))
        os.utime(self.root / "test.gd", (self.old, self.old))
        self.build()

    def build(self):
        subprocess.run([sys.executable, "-X", "utf8", str(self.root / "build_graph.py")], check=True, capture_output=True)
        return self.nodes()

    def nodes(self):
        graph = json.loads((self.root / "data" / "graph.json").read_text(encoding="utf-8"))
        return {n["id"]: n for n in graph["nodes"]}

    def test_agent_edit_propagates_three_levels_but_not_to_sibling(self):
        newer = self.old + 3600
        with patch("graph_store.time.time", return_value=newer):
            apply_operations(self.root, [{"op": "update-node", "id": "entity", "fields": {"human": "New meaning"}}], rebuild=True)
        nodes = self.nodes()
        self.assertEqual(nodes["entity"]["at"], newer)
        for key in ("system", "pillar", "engine_core"):
            self.assertEqual(nodes[key]["agg_at"], newer)
            self.assertEqual(nodes[key]["at"], self.old)
        self.assertEqual(nodes["other"]["agg_at"], self.old)
        self.assertEqual(self.build()["entity"]["at"], newer)

    def test_manual_json_edit_detects_only_affected_node_and_rebuild_stays_stable(self):
        save_document(self.root, load_document(self.root), revision(self.root), rebuild=True)
        path = self.root / "graph_edit.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["NODES"]["entity"]["human"] = "Direct Gemini edit"
        path.write_text(json.dumps(doc), encoding="utf-8")
        newer = self.old + 7200
        os.utime(path, (newer, newer))
        nodes = self.build()
        self.assertEqual(nodes["entity"]["at"], newer)
        self.assertEqual(nodes["other"]["at"], self.old)
        self.assertEqual(self.build()["entity"]["at"], newer)

    def test_acknowledgement_does_not_change_content_time(self):
        doc = load_document(self.root)
        doc["NODES"]["entity"]["human"] = "Human intent"
        with patch("graph_store.time.time", return_value=self.old + 3600):
            save_document(self.root, doc, revision(self.root))
        before = self.nodes()
        token = load_document(self.root)["NODES"]["entity"]["human_edit"]["token"]
        with patch("graph_store.time.time", return_value=self.old + 7200):
            apply_operations(self.root, [{"op": "acknowledge-node", "id": "entity", "token": token, "note": "Read and preserve the human text"}], rebuild=True)
        self.assertEqual(before["entity"]["at"], self.nodes()["entity"]["at"])

    def test_tests_and_images_contribute_without_pretending_code_was_changed(self):
        newer = int(time.time())
        os.utime(self.root / "test.gd", (newer, newer))
        nodes = self.build()
        self.assertEqual(nodes["entity"]["at"], newer)
        self.assertEqual(nodes["engine_core"]["agg_at"], newer)
        art = self.root / "art" / "concept.jpg"
        art.write_bytes(b"\xff\xd8\xffthumbnail\xff\xd9")
        os.utime(art, (newer + 60, newer + 60))
        doc = load_document(self.root)
        doc["CUSTOM_ARTS"] = [{"key": "concept", "path": "art/concept.jpg", "caption": "Concept"}]
        doc["NODES"]["entity"]["arts"] = ["concept"]
        save_document(self.root, doc, revision(self.root))
        self.assertEqual(self.nodes()["entity"]["art_at"], newer + 60)
        self.assertEqual(self.nodes()["engine_core"]["agg_at"], newer + 60)


if __name__ == "__main__":
    unittest.main()
