import copy
import http.client
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edit_graph import Conflict, make_server, save_document, save_image
from graph_store import load_document, revision, validate


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        repo = Path(__file__).resolve().parents[1]
        for name in ("build_graph.py", "graph_store.py", "graph_content.py", "index.html", "editor.html"):
            shutil.copy2(repo / name, self.root)
        self.document = load_document(self.root)

    def test_save_rebuilds_viewer_and_agent_data_without_modifying_python_config(self):
        config = (self.root / "graph_content.py").read_bytes()
        before = revision(self.root)
        self.document["NODES"]["sys_damage_model"]["human"] = "Обновлено пользователем"
        after = save_document(self.root, self.document, before)
        self.assertNotEqual(before, after)
        self.assertEqual((self.root / "graph_content.py").read_bytes(), config)
        self.assertEqual(load_document(self.root)["NODES"]["sys_damage_model"]["human"], "Обновлено пользователем")
        graph = json.loads((self.root / "data" / "graph.json").read_text(encoding="utf-8"))
        self.assertTrue((self.root / "data" / "graph.js").read_text(encoding="utf-8").startswith("window.GRAPH = "))
        self.assertEqual(next(n for n in graph["nodes"] if n["id"] == "sys_damage_model")["human"], "Обновлено пользователем")
        context = json.loads((self.root / "data" / "context_nodes.json").read_text(encoding="utf-8"))
        self.assertEqual(context["sys_damage_model"]["summary"], "Обновлено пользователем")
        saved = (self.root / "graph_edit.json").read_bytes()
        self.document["PROJECT_NAME"] = "Changed"
        save_document(self.root, self.document, after)
        self.assertEqual((self.root / "graph_edit.json.bak").read_bytes(), saved)

    def test_conflict_does_not_overwrite_edits(self):
        old = revision(self.root)
        save_document(self.root, self.document, old)
        with self.assertRaises(Conflict):
            save_document(self.root, self.document, old)

    def test_invalid_structure_rejected_before_write(self):
        for change in ("parent", "link", "root", "cycle", "duplicate"):
            doc = copy.deepcopy(self.document)
            if change == "parent":
                doc["NODES"]["pillar_combat"]["parent"] = "missing"
            elif change == "link":
                doc["LINKS"][0]["target"] = "missing"
            elif change == "root":
                doc["NODES"]["pillar_combat"].update(parent=None, tier=0)
            elif change == "cycle":
                doc["NODES"]["pillar_combat"]["parent"] = "sys_damage_model"
            else:
                doc["LINKS"].append(doc["LINKS"][0])
            with self.subTest(change=change), self.assertRaises(ValueError):
                save_document(self.root, doc, revision(self.root))
            self.assertFalse((self.root / "graph_edit.json").exists())

    def test_failed_build_rolls_back_overlay_and_generated_files(self):
        save_document(self.root, self.document, revision(self.root))
        files = [self.root / "graph_edit.json"] + list((self.root / "data").iterdir())
        before = {p: p.read_bytes() for p in files}
        (self.root / "build_graph.py").write_text("from pathlib import Path\nPath('data/graph.js').write_text('broken')\nraise RuntimeError('test failure')", encoding="utf-8")
        self.document["PROJECT_NAME"] = "Will fail"
        with self.assertRaises(ValueError):
            save_document(self.root, self.document, revision(self.root))
        self.assertEqual({p: p.read_bytes() for p in files}, before)

    def test_image_upload_deduplicates_and_builds_without_pillow(self):
        # Minimal marker fixture checks storage; actual browser encoding is
        # exercised in UI verification, not inferred from these marker bytes.
        jpeg = b"\xff\xd8\xffthumbnail\xff\xd9"
        art = save_image(self.root, jpeg)
        self.assertEqual(save_image(self.root, jpeg), art)
        self.assertEqual((self.root / art["path"]).read_bytes(), jpeg)
        self.document["CUSTOM_ARTS"] = [{**art, "caption": "Drop"}]
        self.document["NODES"]["sys_damage_model"].update(hero=art["key"], arts=[art["key"]])
        save_document(self.root, self.document, revision(self.root))
        graph = json.loads((self.root / "data" / "graph.json").read_text(encoding="utf-8"))
        self.assertEqual(graph["arts"][art["key"]]["file"], "art/" + art["key"] + ".jpg")
        with self.assertRaises(ValueError):
            save_image(self.root, b"not an image")

    def test_local_http_save_upload_and_conflict(self):
        server = make_server(self.root, 0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        self.addCleanup(client.close)
        client.request("GET", "/api/document")
        response = client.getresponse()
        payload = json.loads(response.read())
        self.assertEqual(response.status, 200)
        client.request("POST", "/api/document", json.dumps(payload), {"Content-Type": "application/json"})
        response = client.getresponse(); response.read()
        self.assertEqual(response.status, 200)
        client.request("POST", "/api/document", json.dumps(payload), {"Content-Type": "application/json"})
        response = client.getresponse(); response.read()
        self.assertEqual(response.status, 409)
        client.request("POST", "/api/image", b"\xff\xd8\xffthumbnail\xff\xd9", {"Content-Type": "image/jpeg"})
        response = client.getresponse(); body = json.loads(response.read())
        self.assertEqual(response.status, 200)
        self.assertIn("key", body)
        for path in ("/graph_content.py", "/art/../graph_content.py", "/.git/config"):
            client.request("GET", path)
            response = client.getresponse(); response.read()
            self.assertEqual(response.status, 404)
        client.request("POST", "/api/document", json.dumps(payload), {"Origin": "http://example.com"})
        response = client.getresponse(); response.read()
        self.assertEqual(response.status, 403)


if __name__ == "__main__":
    unittest.main()
