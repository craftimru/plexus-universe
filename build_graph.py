"""
Сборщик графа проекта (Project Universe Graph) для интерактивного 3D-просмотрщика.
Запуск: python -X utf8 build_graph.py
Автоматически считывает конфигурацию из graph_content.py, сканирует структуру проекта,
вычисляет время свежести файлов через git и mtime, формирует арты, связи и зависимости.
Генерирует data/graph.js (для index.html), data/graph.json и data/context_nodes.json для ИИ.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))

try:
    import graph_content as C
except ImportError:
    try:
        import graph_content_example as C
    except ImportError:
        print("Error: Neither graph_content.py nor graph_content_example.py was found.")
        print("Please create graph_content.py based on graph_content.example.py.")
        sys.exit(1)

PROJECT_ROOT = Path(getattr(C, "PROJECT_ROOT", HERE.parent.parent)).resolve()
ART_DIR = HERE / "art"
DATA_DIR = HERE / "data"
ART_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- git и mtime
def get_git_info():
    last = {}
    dirty = set()
    try:
        out = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "log", "--name-only", "--format=@@%ct", "--no-renames"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        ).stdout
        ts = None
        for line in out.splitlines():
            if line.startswith("@@"):
                ts = int(line[2:])
            elif line.strip() and ts is not None and line.strip() not in last:
                last[line.strip().replace("\\", "/")] = ts

        st = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "status", "--porcelain"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        ).stdout
        for line in st.splitlines():
            p = line[3:].strip().strip('"').replace("\\", "/")
            dirty.add(p)
    except Exception:
        pass
    return last, dirty


GIT_LAST, GIT_DIRTY = get_git_info()
SKIP_EXT = {".import", ".uid", ".tmp", ".log"}


def get_file_time(rel_path):
    p = PROJECT_ROOT / rel_path
    try:
        m = int(p.stat().st_mtime)
    except OSError:
        return None
    r = rel_path.replace("\\", "/")
    dirty = r in GIT_DIRTY or any(d.endswith("/") and r.startswith(d) for d in GIT_DIRTY)
    if r in GIT_LAST and not dirty:
        return GIT_LAST[r]
    return m


def expand_paths(rel_path, cap=300):
    p = PROJECT_ROOT / rel_path
    out = []
    if not p.exists():
        return []
    if p.is_file():
        t = get_file_time(rel_path)
        return [(rel_path.replace("\\", "/"), t)] if t else []
    if p.is_dir():
        for dp, dn, fn in os.walk(p):
            dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__", ".godot", "build")]
            for f in fn:
                if Path(f).suffix in SKIP_EXT:
                    continue
                full_f = os.path.join(dp, f)
                r = os.path.relpath(full_f, PROJECT_ROOT).replace("\\", "/")
                t = get_file_time(r)
                if t:
                    out.append((r, t))
                if len(out) >= cap:
                    return out
    return out


# ---------------------------------------------------------------- Арты
ART = {}


def add_art(key, path_or_rel, caption):
    p = Path(path_or_rel)
    if not p.is_absolute():
        p = PROJECT_ROOT / path_or_rel
    if not p.exists():
        return False
    h = hashlib.sha1((str(p) + str(int(p.stat().st_mtime))).encode()).hexdigest()[:8]
    out_file = ART_DIR / f"{key}.jpg"
    hash_file = ART_DIR / f"{key}.hash"

    need_build = not out_file.exists()
    if not need_build and hash_file.exists():
        need_build = (hash_file.read_text(encoding="utf-8").strip() != h)

    if need_build and HAS_PIL:
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail((720, 720))
            im.save(out_file, "JPEG", quality=82)
            hash_file.write_text(h, encoding="utf-8")
        except Exception as e:
            print(f"Warning: could not process image {p}: {e}")
            return False

    at = None
    try:
        at = int(p.stat().st_mtime)
        rel = os.path.relpath(p, PROJECT_ROOT).replace("\\", "/")
        at = get_file_time(rel) if not rel.startswith("..") else at
    except Exception:
        pass

    ART[key] = {"file": f"art/{key}.jpg", "caption": caption, "at": at}
    return True


# Регистрация пользовательских артов из graph_content
for art_item in getattr(C, "CUSTOM_ARTS", []):
    add_art(art_item["key"], art_item["path"], art_item["caption"])


# ---------------------------------------------------------------- Сборка узлов
nodes = {}

# 1. Загрузка из словаря C.NODES
raw_nodes = getattr(C, "NODES", {})
for nid, n in raw_nodes.items():
    nodes[nid] = {
        "id": nid,
        "label": n.get("label", nid),
        "tier": n.get("tier", 2),
        "parent": n.get("parent"),
        "family": n.get("family"),
        "color": n.get("color"),
        "status": n.get("status", "live"),
        "human": n.get("human", ""),
        "paths": list(n.get("paths", [])),
        "tests": list(n.get("tests", [])),
        "hero_key": n.get("hero"),
        "sat_keys": list(n.get("sats", [])),
        "arts": list(n.get("arts", [])),
        "flag": n.get("flag"),
        "codex_state": n.get("codex_state", "Активный модуль"),
        "note": n.get("note", ""),
        "autoexpand": n.get("autoexpand", False),
        "proposed": n.get("proposed", False)
    }

# ---------------------------------------------------------------- Связи
links = []
seen_links = set()

for l in getattr(C, "LINKS", []):
    s = l.get("source")
    t = l.get("target")
    if s and t and s in nodes and t in nodes:
        key = (s, t)
        if key not in seen_links:
            seen_links.add(key)
            links.append({
                "source": s,
                "target": t,
                "type": l.get("type", "subsystem"),
                "label": l.get("label", ""),
                "proposed": l.get("proposed", False)
            })

# Автоматические иерархические связи от родителя к потомку
for nid, n in nodes.items():
    p = n.get("parent")
    if p and p in nodes:
        key = (p, nid)
        if key not in seen_links:
            seen_links.add(key)
            links.append({
                "source": p,
                "target": nid,
                "type": "subsystem",
                "label": "",
                "proposed": False
            })

# ---------------------------------------------------------------- Расчет свежести и файлов
for nid, n in nodes.items():
    files = []
    for p in n["paths"]:
        files += expand_paths(p)
    n["_files"] = files
    n["at"] = max([t for _, t in files], default=None)
    n["changes"] = [{"path": f, "at": t} for f, t in sorted(files, key=lambda x: -x[1])[:5]]

    # Фасеты (грани)
    facets = []
    has_code = any(f.endswith(".gd") or f.endswith(".py") or f.endswith(".cs") or f.endswith(".cpp") for f, _ in files)
    facets.append({"k": "code", "label": "код", "on": has_code, "at": n["at"]})
    has_tests = bool(n["tests"])
    facets.append({"k": "tests", "label": "тесты " + ", ".join(n["tests"]) if n["tests"] else "тесты", "on": has_tests, "at": n["at"] if has_tests else None})
    has_docs = any(f.endswith(".md") or f.endswith(".txt") for f, _ in files)
    if has_docs:
        facets.append({"k": "docs", "label": "GDD/доки", "on": True, "at": n["at"]})
    n["facets"] = facets

# ---------------------------------------------------------------- Иерархия детей и семейств
children = {}
for nid, n in nodes.items():
    par = n.get("parent")
    if par:
        children.setdefault(par, []).append(nid)

families_dict = getattr(C, "FAMILY", {})


def get_node_family(nid):
    cur = nid
    visited = set()
    while cur and cur not in visited:
        visited.add(cur)
        if cur in families_dict:
            return cur
        n = nodes.get(cur)
        if not n:
            break
        cur = n.get("parent")
    return "engine_core"


for nid, n in nodes.items():
    n["children"] = children.get(nid, [])
    fam = get_node_family(nid)
    n["family"] = fam
    if not n.get("color"):
        n["color"] = families_dict.get(fam, "#9fb8d0")


# Агрегированное время свежести (свежесть узла = max среди его потомков)
def calc_agg_at(nid, visited=None):
    if visited is None:
        visited = set()
    if nid in visited:
        return 0
    visited.add(nid)
    n = nodes[nid]
    t = n.get("at") or 0
    for c in n.get("children", []):
        if c in nodes:
            t = max(t, calc_agg_at(c, visited) or 0)
    n["agg_at"] = t or None
    return t


root_nodes = [nid for nid, n in nodes.items() if not n.get("parent")]
for r in root_nodes:
    calc_agg_at(r)


# ---------------------------------------------------------------- Hero и Satellites арты
def get_hero_art(nid, visited=None):
    if visited is None:
        visited = set()
    if nid in visited:
        return None
    visited.add(nid)
    n = nodes[nid]
    if n.get("hero_key") and n["hero_key"] in ART:
        return n["hero_key"]
    for k in n.get("arts", []):
        if k in ART:
            return k
    for c in n.get("children", []):
        if c in nodes:
            h = get_hero_art(c, visited)
            if h:
                return h
    return None


for nid, n in nodes.items():
    n["hero"] = get_hero_art(nid)
    sats = []
    for k in n.get("sat_keys", []):
        if k in ART and len(sats) < 5 and k != n["hero"]:
            sats.append({"art": k, "caption": ART[k]["caption"], "node": None})
    n["sats"] = sats


# ---------------------------------------------------------------- Финализация JSON
SIZE_MAP = {0: 28, 1: 16, 2: 11, 3: 7.5}
out_nodes = []
context_nodes = {}

for nid, n in nodes.items():
    t = n.get("tier", 2)
    sz = SIZE_MAP.get(t, 10.0) + min(6, len(n.get("children", [])) * 0.4)
    item = {
        "id": n["id"],
        "label": n["label"],
        "tier": n["tier"],
        "parent": n["parent"],
        "children": n["children"],
        "family": n["family"],
        "color": n["color"],
        "status": n["status"],
        "status_text": getattr(C, "STATUS_NAMES", {}).get(n["status"], n["status"]),
        "human": n["human"],
        "hero": n["hero"],
        "sats": n["sats"],
        "arts": [k for k in n.get("arts", []) if k in ART],
        "facets": n["facets"],
        "at": n["at"],
        "agg_at": n["agg_at"],
        "changes": n["changes"],
        "proposed": n["proposed"],
        "autoexpand": n["autoexpand"],
        "paths": n["paths"],
        "size": sz,
        "flag": n.get("flag"),
        "codex_label": n["label"],
        "note": n.get("note", ""),
        "codex_state": n["codex_state"],
        "tests": n["tests"]
    }
    out_nodes.append(item)

    # Запись в компактный индекс context_nodes для ИИ
    context_nodes[nid] = {
        "label": n["label"],
        "tier": n["tier"],
        "parent": n["parent"],
        "family": n["family"],
        "status": n["status"],
        "summary": n["human"],
        "paths": n["paths"],
        "tests": n["tests"],
        "children": n["children"]
    }

fresh_hours = getattr(C, "FRESH_HOURS", 48)
payload = {
    "built_at": int(time.time()),
    "fresh_hours": fresh_hours,
    "project": getattr(C, "PROJECT_NAME", "RTS Game"),
    "engine": getattr(C, "ENGINE_VERSION", "Godot 4"),
    "status_names": getattr(C, "STATUS_NAMES", {
        "idea": "Идея / план",
        "art": "Арт и референсы",
        "proto": "Прототип, не подключён",
        "wip": "В работе",
        "live": "Работает в игре",
        "polished": "Отполировано",
        "shelved": "Отложено"
    }),
    "nodes": out_nodes,
    "links": links,
    "arts": ART,
    "source": {
        "project_root": str(PROJECT_ROOT),
        "total_nodes": len(out_nodes),
        "total_links": len(links)
    }
}

# Генерация файлов данных
(DATA_DIR / "graph.js").write_text("window.GRAPH = " + json.dumps(payload, ensure_ascii=False) + ";\n", encoding="utf-8")
(DATA_DIR / "graph.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
(DATA_DIR / "context_nodes.json").write_text(json.dumps(context_nodes, ensure_ascii=False, indent=2), encoding="utf-8")

fresh = [n for n in out_nodes if n["at"] and (time.time() - n["at"]) < fresh_hours * 3600]
print(f"=== Project Universe Graph Сборка Завершена ===")
print(f"Узлов: {len(out_nodes)}, Связей: {len(links)}, Артов: {len(ART)}")
print(f"Свежих за {fresh_hours} ч: {len(fresh)}")
