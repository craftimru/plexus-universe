"""Build a static Pages demo from the shipped template, never a user's map."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def build(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        for name in ("build_graph.py", "graph_store.py", "viewer.js", "index.html"):
            shutil.copy2(ROOT / name, root / name)
        shutil.copy2(ROOT / "graph_content.example.py", root / "graph_content.py")
        result = subprocess.run([sys.executable, "-X", "utf8", str(root / "build_graph.py")],
            cwd=root, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=60)
        if result.returncode:
            raise ValueError(result.stderr or result.stdout)
        graph = json.loads((root / "data" / "graph.json").read_text(encoding="utf-8"))
    graph["project"] = "Plexus Universe · RTS Demo"
    graph["source"] = {"demo": True, "total_nodes": len(graph["nodes"]), "total_links": len(graph["links"])}
    (output / "data").mkdir(exist_ok=True)
    (output / "data" / "graph.js").write_text("window.GRAPH = " + json.dumps(graph, ensure_ascii=False) + ";\n", encoding="utf-8")
    for name in ("viewer.js", "three.min.js"):
        shutil.copy2(ROOT / name, output / name)
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    metadata = '''<meta name="description" content="Plexus Universe: a local-first 3D game architecture knowledge graph for developers and AI agents. Explore the interactive project map, editor, CLI and MCP workflow.">
<meta property="og:title" content="Plexus Universe — a project map for humans and AI agents">
<meta property="og:description" content="Explore game systems, dependencies, source paths and design intent on an interactive 3D map.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://craftimru.github.io/plexus-universe/">
<meta property="og:image" content="https://craftimru.github.io/plexus-universe/preview.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://craftimru.github.io/plexus-universe/">
'''
    html = html.replace("</head>", metadata + "</head>")
    html = html.replace('<script src="three.min.js">', '<script>window.PLEXUS_DEMO = true;</script>\n<script src="three.min.js">')
    (output / "index.html").write_text(html, encoding="utf-8")
    preview = ROOT / "docs" / "images" / "plexus-universe.jpg"
    if preview.exists():
        shutil.copy2(preview, output / "preview.jpg")
    (output / ".nojekyll").touch()
    return output


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    print(build(args.output))
