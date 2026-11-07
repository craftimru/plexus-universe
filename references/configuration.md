# Настройка карты

Это описание начальной Python-конфигурации. Если уже есть `graph_edit.json`, он перекрывает описательные настройки. Человек редактирует карту в браузере, агент — через проверяемые CLI/MCP-операции; корень проекта остаётся в Python.

Инструмент можно держать отдельно от игры или положить, например, в `tools/project_graph`. В его папке должен находиться `graph_content.py`; за основу можно взять `graph_content.example.py`.

Укажите корень игры в `PROJECT_ROOT`. Пути в `paths`, `tests` и относительные пути изображений задаются от этого каталога. Если инструмент лежит в `tools/project_graph`, корень можно получить так:

```python
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
```

Ниже минимальная конфигурация. Замените пути на существующие файлы своего проекта.

```python
from pathlib import Path

PROJECT_NAME = "My Game"
ENGINE_VERSION = "Godot 4"
PROJECT_ROOT = str(Path("D:/Projects/MyGame").resolve())
FRESH_HOURS = 48

FAMILY = {
    "engine_core": "#ffe39a",
    "pillar_combat": "#ff6f4d",
}

NODES = {
    "engine_core": {
        "label": "My Game",
        "tier": 0,
        "parent": None,
        "status": "wip",
        "human": "Игровой проект.",
        "paths": ["project.godot"],
    },
    "pillar_combat": {
        "label": "Боевая система",
        "tier": 1,
        "parent": "engine_core",
        "status": "proto",
        "human": "Расчёт урона и обработка попаданий.",
        "paths": ["src/combat/"],
        "tests": ["tests/test_combat.gd"],
    },
}

LINKS = [
    {
        "source": "pillar_combat",
        "target": "engine_core",
        "type": "reads_state",
        "label": "Читает состояние игры",
    },
]
```

Связи от родителя к дочерним узлам сборщик добавляет сам. Остальные задаются в `LINKS`: например, `calls`, `reads_state`, `writes`, `owns`, `renders`, `delegates` или `uses`. Цвет семейства задаётся в `FAMILY` по ID узла и наследуется его потомками.

Для изображений используйте `CUSTOM_ARTS`: список записей с полями `key`, `path` и `caption`. В узле можно указать ключ основного изображения в `hero`, ключи дополнительных миниатюр в `sats`, а изображения галереи — в `arts`. Сборщик сохраняет JPEG-миниатюры размером до 720 × 720 пикселей в `art/`.

После правок снова запустите сборку и обновите страницу. Данные не обновляются в фоне. Статусы и список тестов берутся из конфигурации: сборщик не проверяет готовность системы и не запускает тесты.
