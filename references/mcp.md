# MCP

MCP-сервер — необязательная обёртка над теми же операциями, что использует CLI. Он работает через stdio, не открывает дополнительный HTTP-порт и не меняет просмотрщик.

Нужен Python 3.10+. Установите зависимости в выбранное окружение:

```sh
python -m pip install -r requirements-mcp.txt
```

Используется официальная библиотека [`mcp`, ветка SDK v1](https://py.sdk.modelcontextprotocol.io/v1/) с ограничением `<2`, поскольку адаптер использует `FastMCP` этой ветки. Обновление на другой основной API должно проходить через отдельную проверку.

Пример конфигурации MCP-клиента (подставьте пути к своему Python и инструменту):

```json
{
  "mcpServers": {
    "project-universe-graph": {
      "command": "C:/Path/to/venv/Scripts/python.exe",
      "args": ["-X", "utf8", "D:/MyGame/tools/project_graph/graph_mcp.py", "--root", "D:/MyGame/tools/project_graph"]
    }
  }
}
```

Названия разделов конфигурации зависят от клиента. Это готовая команда запуска для клиента, который использует формат `mcpServers`; инструмент не меняет настройки ваших агентов автоматически.

По умолчанию доступны `graph_search`, `graph_node`, `graph_human_changes`, `graph_context`, `graph_path`, `graph_overview`, `graph_health`, `graph_bootstrap`. Ответы — ограниченный по размеру JSON в текстовом результате инструмента. Ошибки параметров возвращаются клиенту как ошибки инструмента и не останавливают сервер.

Чтобы разрешить агенту правки карты, добавьте `--allow-write` в `args`. Тогда появится `graph_apply`:

```json
{
  "operations": [
    {"op": "update-node", "id": "sys_damage_model", "fields": {"needs_review": true}}
  ],
  "expected_revision": "REVISION_FROM_GRAPH_NODE",
  "summary": "Проверить изменение модели урона",
  "rebuild": true,
  "dry_run": false
}
```

Формат операций совпадает с [CLI](agent-api.md), включая `acknowledge-node`. Проверка `expected_revision` обязательна. `rebuild` по умолчанию включён, в отличие от CLI; `dry_run` проверяет патч без записи. Защита человеческих правок и `locked` действует так же, как в CLI.

Проверка реального stdio-соединения после установки SDK:

```sh
python -X utf8 -m unittest discover -s tests -p test_mcp.py -v
```
