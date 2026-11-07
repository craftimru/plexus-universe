---
name: project-universe-graph
description: Navigate a manually curated game-project graph to find relevant source files, tests, and dependencies using bounded local queries. Use when working in a project that has Project Universe Graph installed.
---

# Project Universe Graph

Use `graph_agent.py` beside this file to navigate the project's map. Commands below run from the tool's directory; from another directory use its full path. The CLI reads the graph internally and returns only the requested records. Do not load the entire `data/graph.json` or `data/context_nodes.json` into conversation by default.

## Find the task's context

```sh
python -X utf8 graph_agent.py search "урон"
python -X utf8 graph_agent.py node sys_damage_model
python -X utf8 graph_agent.py context sys_damage_model --direction both --depth 1
```

- `search` matches ID, label, description and paths; multiple words must all match. It returns up to five brief cards. Try another term if it finds nothing; search is lexical, not semantic.
- `node` returns one card with description, source paths, test paths and child IDs.
- `context` follows explicit dependencies, one hop by default. Use `--direction in` for callers, `out` for dependencies, `both` for both. Parent/child edges are excluded unless `--hierarchy` is added. Maximum depth is three; default node limit is eight.
- `overview` returns the root and top-level sections, five at a time.
- `path "src/combat/damage.gd"` finds nodes whose source/test paths cover the given file. More specific matches come first; paths are relative to `PROJECT_ROOT`, or absolute beneath it.

For another slice use `--limit` and `--offset` on `search`, `overview` or `path`. Follow `next_offset` to continue. For a child branch, query its ID instead of expanding every branch.

Output is compact JSON, limited to 6,000 characters by default. Change the budget before the command:

```sh
python -X utf8 graph_agent.py --max-chars 3000 context sys_damage_model --limit 4
```

`truncated: true` means records were removed for the character budget. `node_limit_reached: true` means traversal skipped neighbors at the node limit. Narrow the query, navigate by returned IDs, or deliberately increase the limit/budget if needed. An oversized single card returns an error rather than silently hiding its paths. A character limit is not an exact token count.

## Read and maintain the relevant sources

Resolve returned paths relative to `PROJECT_ROOT` in `graph_content.py`. Read the relevant files and listed tests, then query another node only when the task calls for it. The map does not contain source contents. A configured directory may be broad; narrow searches within that directory.

The map is manually maintained. Statuses and test paths are declarations, not proof that code works. A missing node or edge does not prove absence of code or callers; use targeted repository search when coverage is insufficient. When a task changes paths, responsibilities or dependencies, update the affected entries in the active description: `graph_edit.json` if present, otherwise `graph_content.py`. The JSON is a full snapshot of descriptive settings and overrides the Python configuration; `PROJECT_ROOT` remains in Python. Do not overwrite unrelated user edits.

`built_at` is the graph build time. `config_newer_than_graph` only checks whether the adjacent Python configuration or editor snapshot is newer than the generated JSON; it does not validate source changes or map completeness. When configuration or freshness information needs updating, run:

```sh
python -X utf8 build_graph.py
```

The CLI never rebuilds automatically. It reads JSON without executing project configuration. Use `--data /path/to/data/graph.json` before the command to query another generated graph.

For user-facing editing, run `python -X utf8 edit_graph.py` (Python 3.9+). The browser editor saves validated nodes, links and image associations to `graph_edit.json` and rebuilds the viewer and agent index. `index.html` is the read-only viewer. Uploaded thumbnails are stored in `art/`; keep them with the snapshot when moving the tool.
