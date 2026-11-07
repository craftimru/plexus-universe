---
name: project-universe-graph
description: Navigate and maintain a shared game-project map with bounded CLI or MCP queries, validated updates, and explicit acknowledgement of human edits. Use when working in a project that has Project Universe Graph installed.
---

# Project Universe Graph

Use `graph_agent.py` beside this file (Python 3.9+) or the connected graph MCP tools. Run commands from the tool directory, use a full script path, or pass `--root /path/to/project_graph` before the command. Do not load the whole graph or index into conversation by default.

## Before and during a task

```sh
python -X utf8 graph_agent.py search "урон"
python -X utf8 graph_agent.py node sys_damage_model
python -X utf8 graph_agent.py context sys_damage_model --depth 1 --direction both
```

Read the returned source/test paths relative to `PROJECT_ROOT` in `graph_content.py`. For a changed file, use `path "src/combat/damage.gd"` to find owners. Use targeted code searches when a path names a broad directory or the map lacks coverage; a missing node or edge does not prove absence of code or callers.

`context` excludes hierarchy edges by default; use `--hierarchy` deliberately. Search is lexical and requires all words to match. `overview` gives the top level. Queries return compact JSON, normally limited to 6,000 characters; this is not an exact token budget. Follow `next_offset` on paged commands. `truncated`, `node_limit_reached` and `scan_incomplete` explicitly describe limits. Narrow a query before increasing its budget with `--max-chars`.

`rebuild_required` means generated data differs from configuration. Rebuild before relying on it or making bootstrap suggestions. `health` checks the built graph's paths, references and review flags. Add `--scope src` only when a filesystem coverage scan is useful; do not scan the whole project on every task.

## Preserve the user's edits

A node may have `human_edit` with `token`, `at`, `fields`, `acknowledged`, and `human_pending: true`. Read its current text, paths and linked art captions/files. If images changed, inspect the relevant image when it matters to the task. Do not restore an older description or replace human artwork just to match a previous plan.

For pending human edits, run `human-changes ID` to read paged before/after values. **Before continuing affected work, tell the user in commentary what changed and how you will handle it**: what you accept as current intent, what you will preserve, and any conflict with code that needs clarification. Ask only when the meaning is actually unclear. A silent tool acknowledgement is not a user-facing response.

After that explanation, record acknowledgement with the token you actually read and a note describing your intended handling:

```sh
python -X utf8 graph_agent.py acknowledge-node sys_damage_model --token TOKEN_FROM_NODE --note "Уточнение назначения прочитано; сохраняю формулировку и учту её в задаче" --rebuild
```

A newer human save invalidates the token. On conflict, read the current node again; do not blindly retry with a new token or revision. Acknowledgement records familiarity, not approval to overwrite the user's choices. `locked` blocks substantive agent changes even after acknowledgement; leave it for the user to unlock. `needs_review` requests review and does not establish that the node is broken.

## Finish the task by maintaining the map

After relevant code changes:

1. Use `path` for changed files and inspect the affected nodes. Do not label systems `live`/`polished` solely because code was generated.
2. If responsibility, paths, tests, dependencies or status changed, use `update-node`, `add-node`, `set-status`, `add-link` or `remove-link`. Make narrow field changes; do not rewrite the whole snapshot or Python configuration. If architecture did not change, do not invent a map update.
3. For coupled changes, use a reviewed operations file with `apply --file patch.json --dry-run`, then apply the same patch with `--rebuild` and the `--expected-revision` returned by the preview. This validates the final batch together and detects intervening edits.
4. Query the updated nodes and relevant health results. Report unresolved missing paths or intentional plans; do not silently create placeholder files or clear human review flags to make the report look clean.

```sh
python -X utf8 graph_agent.py update-node sys_damage_model --human "Расчёт урона и обработка попаданий" --rebuild
python -X utf8 graph_agent.py add-link sys_ai_commander sys_damage_model --type calls --label "Запрос атаки" --rebuild
```

Writes go to `graph_edit.json` without rewriting Python, retain unmodified fields, validate hierarchy, record history and use the same save routine as the browser. `--rebuild` is explicit for CLI writes; without it generated queries remain stale. `PROJECT_ROOT` remains in Python. The instruction does not grant authorization for unrelated changes or publishing.

For exact operation schemas, flags and patch examples, read [references/agent-api.md](references/agent-api.md) when writing. For new-project suggestions from folders or `@orbit:` markers, use `bootstrap --scope ... --parent ...`, review its operations and descriptions, then dry-run before applying. Never apply a truncated or incomplete suggestion set as though it were a complete import.

## Browser and MCP

Users edit with `python -X utf8 edit_graph.py` or `edit_graph.bat`; `index.html` is the viewer. Browser saves mark human edits automatically and rebuild the agent index. Do not use the human browser endpoint to bypass agent protections. [MCP setup](references/mcp.md) uses optional SDK dependencies and stdio; `graph_apply` is available only when the server was launched with `--allow-write`.
