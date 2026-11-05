# 🌌 Project Universe Graph (Интерактивная карта «Вселенной проекта»)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Three.js](https://img.shields.io/badge/Render-Three.js_r128-black?logo=three.js)](https://threejs.org/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://python.org)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero_External-brightgreen)]()
[![Platform](https://img.shields.io/badge/Platform-Windows_|_Linux_|_macOS-lightgrey)]()

> **Interactive 3D Universe Knowledge Graph for Game Architecture, GDD, Systems, and AI Agent Context Indexing.**  
> *Интерактивный 3D-граф знаний в виде «солнечной системы проекта» для визуализации архитектуры игры, дизайн-документов, ассетов и мгновенного контекстного поиска ИИ-агентов.*

---

## 🇷🇺 О проекте (Russian)

**Project Universe Graph** — это автономная экосистема визуализации и структурирования сложных игровых проектов (Godot, Unreal Engine, Unity, Custom C++/Rust).

Вместо плоских каталогов и громоздких диаграмм, проект разворачивается в **трехмерную галактику знаний** на Three.js:
- **В центре** сияет ядро симуляции (*Tier 0*).
- **По орбитам** обращаются фундаментальные столпы архитектуры (*Tier 1*).
- **Вокруг столпов** группируются конкретные подсистемы (*Tier 2*) и боевые сущности (*Tier 3*).
- **Между узлами** струятся фотонные лучи зависимостей (`calls`, `reads_state`, `writes`, `owns`, `renders`).

---

### 💡 Двойное назначение: Человек и ИИ-агент

| Для Архитектора и Разработчика (Human) | Для ИИ-агента (Claude Code, Gemini, Cursor) |
|---|---|
| 🌌 **Наглядная космическая панорама**: мгновенное понимание архитектурного ландшафта игры. | ⚡ **Экономия токенов до 90%**: агент читает компактный `data/context_nodes.json` вместо обхода файловой системы. |
| ⏱️ **Пульс свежести (Git & mtime)**: яркое мерцание узлов, измененных < 6 ч, мягкое < 24 ч, метка < 48 ч. | 🎯 **Фокус контекста**: точечное определение связанных файлов (`paths`), тестов (`tests`) и зависимостей по ID узла. |
| 🎨 **Кольца статусов**: жизненный цикл от `idea` и `proto` до `live` и `polished`. | 🛡️ **Защита от галлюцинаций**: агент понимает нерушимые границы подсистем и утвержденный контракт связей. |
| 🖼️ **Спутники и арты**: всплывающие карточки с референсами, скриншотами и GDD-описанием. | 🚀 **Автономная навигация**: быстрое погружение в новую кодовую базу за один запрос. |

---

### 🪐 Архитектурные принципы графа

1. **Иерархия 7±2 (Когнитивное правило Миллера):**
   * **Tier 0 (Core):** Ядро движка / Проект (`engine_core`).
   * **Tier 1 (Pillars):** 6–9 фундаментальных столпов (Бой, Экономика, ИИ, Навигация, Визуальный слой, UI/Audio).
   * **Tier 2 (Subsystems):** Менеджеры, сервисы и контроллеры подсистем (`sys_*`).
   * **Tier 3 (Entities):** Классы юнитов, строений, карточки способностей (`unit_*`, `bld_*`).
2. **Кольца жизненного цикла (Status Rings):**
   * `idea` — Пунктир серо-синий: Замысел / план в GDD.
   * `art` — Сплошное фиолетовое: 2D/3D-ассеты и концепты готовы.
   * `proto` — Пунктир янтарный: Прототип / болванка, не подключен к матчу.
   * `wip` — Бегущая бирюзовая дуга: В активной разработке прямо сейчас.
   * `live` — Зеленое сплошное: Проверено и функционирует в игре.
   * `polished` — Золотое свечение: Отполировано, протестировано и оптимизировано.
   * `shelved` — Точечный серый контур: Отложено в бэклог.
3. **Автоматический трекинг свежести (Git + Filesystem mtime):**
   * Скрипт сборки заглядывает в `git log` и атрибуты файлов, вычисляя время последней активности.
   * Узлы с недавними коммитами пульсируют золотым свечением, позволяя с одного взгляда видеть «горячие точки» текущего спринта.
4. **Направленные лучи зависимостей (Dependency Rays):**
   * Фотоны бегут по линиям связей, отражая реальное направление потока данных:
     * `calls` (вызов метода / команды),
     * `reads_state` (чтение состояния),
     * `writes` (запись / транзакция),
     * `owns` (композиция / владение),
     * `renders` (отрисовка визуалом).

---

## 🇬🇧 About Project Universe Graph (English)

**Project Universe Graph** is a zero-dependency, offline-first visualization and indexing toolkit designed for complex game codebases (Godot, Unreal Engine, Unity, Custom C++/Rust engines).

It elevates flat file trees into a **living 3D cosmological map** powered by Three.js:
- **At the center** shines the engine simulation core (*Tier 0*).
- **In stable orbits** circulate the foundational pillars (*Tier 1*).
- **Around each pillar** orbit concrete subsystems (*Tier 2*) and game entities (*Tier 3*).
- **Between nodes**, dynamic photonic beams visualize live architectural coupling (`calls`, `reads_state`, `writes`, `owns`, `renders`).

### 🧠 Why It Matters for AI-Assisted Game Development

Autonomous AI agents (such as Claude Code, Gemini CLI, Cursor Composer, or Antigravity) easily get overwhelmed when indexing hundreds of source files in large game repositories, wasting context tokens and hallucinating dependency boundaries.

With **Project Universe Graph**:
1. The builder generates `data/context_nodes.json` — an ultra-compact, token-efficient semantic index.
2. The agent reads the index in milliseconds, identifying exactly which 1–3 files govern the subsystem in question.
3. Subsystem boundaries remain crystal-clear, preventing architectural drift and unintended couplings.

---

## 📁 Структура репозитория / File Structure

```
project-universe-graph/
├── index.html               # Автономный Three.js HTML-вьюер (работает прямо через file:// без веб-сервера)
├── viewer.js                # Движок 3D-графа, частиц, орбитальной камеры и выдвижной панели
├── three.min.js             # Оффлайн-библиотека Three.js r128
├── build_graph.py           # Генератор данных графа, вычисление свежести по git и генерация индексов
├── graph_content.py         # Конфигурация вашего проекта (столпы, узлы, пути, связи)
├── graph_content.example.py # Чистый эталонный шаблон с примерами и комментариями
├── open_graph.bat           # Однокликовый запуск для Windows (пересборка + открытие)
├── SKILL.md                 # Спецификация навыка для интеграции в AI-агенты (Antigravity / Claude)
├── art/                     # Миниатюры артов и скриншотов (<=720px, кэшируются через .hash)
└── data/
    ├── graph.js             # Собранные данные для прямого открытия в браузере (file://)
    ├── graph.json           # Полный JSON-дамп для внешних инструментов и аналитики
    └── context_nodes.json   # Сверхкомпактный индекс для ИИ-агентов (минимизация токенов)
```

---

## 🚀 Быстрый старт / Quick Start

### 1. Требования / Requirements
- **Python 3.8+**
- Опционально: `Pillow` для автоматического создания миниатюр артов (`pip install pillow`).
- Никаких серверов, node_modules или внешних CDN — всё работает на 100% локально и оффлайн!

### 2. Запуск демонстрации / Run Demo
**Windows:**
Просто дважды щелкните:
```cmd
open_graph.bat
```

**Linux / macOS / PowerShell:**
```bash
python -X utf8 build_graph.py
# Затем откройте index.html в любом браузере:
# Windows:
start index.html
# macOS:
open index.html
# Linux:
xdg-open index.html
```

---

## 🛠️ Интеграция в ваш игровой проект / How to Adopt

### Шаг 1: Скопируйте инструмент в папку проекта
Скопируйте `project-universe-graph` в `tools/project_graph` внутри вашего репозитория игры:
```powershell
Copy-Item -Recurse ".\project-universe-graph" "D:\MyGameProject\tools\project_graph"
```

### Шаг 2: Настройте `graph_content.py`
Откройте `graph_content.py` и опишите структуру вашей игры:
```python
from pathlib import Path

PROJECT_NAME = "My Awesome RTS"
ENGINE_VERSION = "Godot 4.3"
PROJECT_ROOT = str(Path(__file__).parent.parent.parent.resolve())
FRESH_HOURS = 48

FAMILY = {
    "engine_core": "#ffe39a",
    "pillar_match": "#9fb8d0",
    "pillar_combat": "#ff6f4d",
    "pillar_economy": "#ffc64a",
    "pillar_navigation": "#3ee58f"
}

NODES = {
    "engine_core": {
        "label": "Game Core",
        "tier": 0,
        "parent": None,
        "family": "engine_core",
        "status": "live",
        "human": "Центральное ядро симуляции и цикл кадров.",
        "paths": ["src/Main.gd", "project.godot"]
    },
    "pillar_combat": {
        "label": "Боевая Система",
        "tier": 1,
        "parent": "engine_core",
        "family": "pillar_combat",
        "status": "live",
        "human": "Расчет баллистики, урон, радиусы стрельбы.",
        "paths": ["src/combat/"]
    }
}

LINKS = [
    {"source": "pillar_combat", "target": "engine_core", "type": "calls", "label": "регистрация урона"}
]
```

### Шаг 3: Соберите и откройте
```bash
python -X utf8 build_graph.py
```
После сборки вы получите:
- `data/graph.js` для мгновенного просмотра в `index.html`.
- `data/context_nodes.json` для скармливания контекста ИИ-агентам.

---

## 🎮 Управление в 3D-просмотрщике / Controls

- **ЛКМ (Левая кнопка мыши)** — Свободное вращение камеры вокруг центра галактики.
- **Колесико мыши** — Плавный зум к выбранному эшелону архитектуры.
- **ПКМ (Правая кнопка мыши)** — Панорамирование / смещение фокуса.
- **Клик по узлу** — Выбор узла, открытие боковой карточки с описанием, путями, тестами и связанными артами.
- **Двойной клик** — Зум и центрирование камеры на выбранной подсистеме.
- **Esc** — Сброс выбора узла / шаг назад по иерархии.
- **R** — Полный сброс камеры в обзорную позицию.
- **Строка поиска (`/`)** — Быстрый поиск подсистемы или сущности по названию и ключевым словам.
- **Фильтр «Свежее за 48 ч»** — Подсветка всех активных зон, которые коммитились или изменялись за последние 48 часов.

---

## 🤖 Использование ИИ-агентами / AI Agents Workflow

В корень вашего репозитория или в каталог промптов добавьте ссылку на `SKILL.md`.

Когда агент приступает к задаче:
1. Агент заглядывает в `data/context_nodes.json`.
2. Находит целевой узел (например, `sys_damage_model`).
3. Видит точный список исходных файлов (`paths`), тестов (`tests`) и контрактов связи (`links`).
4. Читает только указанные файлы, мгновенно приступая к работе без расхода токенов на сканирование всего дерева проекта.

---

## 📜 Лицензия / License

Распространяется под свободной лицензией **MIT License**.  
Используйте в открытых, коммерческих и инди-проектах без ограничений.
