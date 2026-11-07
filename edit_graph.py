"""Local graph editor. Run: python -X utf8 edit_graph.py"""
import argparse
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import runpy
import sys
import threading
from urllib.parse import urlsplit
import webbrowser

from graph_store import atomic_write, load_document, revision, validate

HERE = Path(__file__).resolve().parent


class Conflict(ValueError):
    pass


def save_image(root, content):
    if len(content) > 2_000_000 or not content.startswith(b"\xff\xd8\xff") or not content.endswith(b"\xff\xd9"):
        raise ValueError("Expected a JPEG thumbnail, at most 2 MB")
    key = "upload_" + hashlib.sha256(content).hexdigest()[:24]
    root = Path(root)
    config = runpy.run_path(str(root / "graph_content.py"))
    project_root = Path(config.get("PROJECT_ROOT", root.parent.parent)).resolve()
    path = root / "art" / (key + ".jpg")
    path.parent.mkdir(exist_ok=True)
    atomic_write(path, content)
    return {"key": key, "path": os.path.relpath(path, project_root).replace("\\", "/")}


def save_document(root, document, expected_revision):
    root = Path(root)
    if expected_revision != revision(root):
        raise Conflict("The configuration changed. Reload before saving.")
    validate(document)
    overlay = root / "graph_edit.json"
    files = [overlay] + [root / "data" / name for name in ("graph.js", "graph.json", "context_nodes.json")]
    before = {path: path.read_bytes() if path.exists() else None for path in files}
    if before[overlay] is not None:
        atomic_write(root / "graph_edit.json.bak", before[overlay])
    try:
        atomic_write(overlay, (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        result = subprocess.run([sys.executable, "-X", "utf8", str(root / "build_graph.py")],
                                cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60)
        if result.returncode:
            raise ValueError("Build failed: " + (result.stderr or result.stdout)[-2000:])
    except Exception:
        for path, content in before.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, content)
        raise
    return revision(root)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server, directory=str(server.root))

    def local_request(self):
        allowed = {"127.0.0.1:" + str(self.server.server_port), "localhost:" + str(self.server.server_port)}
        if self.headers.get("Host") not in allowed:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {"http://" + host for host in allowed}

    def json_response(self, status, body):
        content = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if not self.local_request():
            return self.json_response(403, {"error": "Local requests only"})
        path = urlsplit(self.path).path
        if path == "/api/document":
            try:
                with self.server.lock:
                    self.json_response(200, {"document": load_document(self.server.root), "revision": revision(self.server.root)})
            except Exception as error:
                self.json_response(400, {"error": str(error)})
        elif path.startswith("/api/"):
            self.json_response(404, {"error": "Unknown endpoint"})
        elif path == "/" or path in ("/editor.html", "/editor.js", "/index.html", "/viewer.js", "/three.min.js", "/data/graph.js") or path.startswith("/art/"):
            relative = "editor.html" if path == "/" else path.lstrip("/")
            target = (self.server.root / relative).resolve()
            allowed_root = (self.server.root / "art").resolve() if path.startswith("/art/") else self.server.root.resolve()
            if not target.is_relative_to(allowed_root) or not target.is_file():
                return self.json_response(404, {"error": "File not found"})
            self.path = "/" + relative
            super().do_GET()
        else:
            self.json_response(404, {"error": "File not found"})

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_POST(self):
        if not self.local_request():
            return self.json_response(403, {"error": "Local requests only"})
        path = urlsplit(self.path).path
        if path not in ("/api/document", "/api/image"):
            return self.json_response(404, {"error": "Unknown endpoint"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 2_000_000:
                raise ValueError("Request must be between 1 byte and 2 MB")
            content = self.rfile.read(size)
            if path == "/api/image":
                with self.server.lock:
                    art = save_image(self.server.root, content)
                return self.json_response(200, art)
            payload = json.loads(content)
            with self.server.lock:
                new_revision = save_document(self.server.root, payload["document"], payload["revision"])
            self.json_response(200, {"revision": new_revision})
        except Conflict as error:
            self.json_response(409, {"error": str(error)})
        except Exception as error:
            self.json_response(400, {"error": str(error)})


def make_server(root=HERE, port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.root = Path(root)
    server.lock = threading.Lock()
    return server


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--port", type=int, default=8765)
    cli.add_argument("--no-browser", action="store_true")
    args = cli.parse_args()
    server = make_server(port=args.port)
    url = "http://127.0.0.1:" + str(server.server_port) + "/editor.html"
    print("Graph editor: " + url + " (Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
