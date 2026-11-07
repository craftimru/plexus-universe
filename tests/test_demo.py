import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_demo import build


class DemoTests(unittest.TestCase):
    def test_static_demo_uses_template_without_private_paths_or_editor_backend(self):
        with tempfile.TemporaryDirectory() as temp:
            output = build(temp)
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("window.PLEXUS_DEMO = true", html)
            self.assertTrue((output / "three.min.js").is_file())
            text = (output / "data" / "graph.js").read_text(encoding="utf-8")
            graph = json.loads(text.removeprefix("window.GRAPH = ").rstrip(";\n"))
            self.assertTrue(graph["source"]["demo"])
            self.assertNotIn("project_root", graph["source"])
            self.assertGreater(len(graph["nodes"]), 5)
            self.assertFalse((output / "graph_content.py").exists())
            self.assertFalse((output / "graph_edit.json").exists())
            self.assertFalse((output / "edit_graph.py").exists())


if __name__ == "__main__":
    unittest.main()
