"""
Project Universe Graph — Конфигурация графа (Пример / Template).
Определяет структуру игрового проекта: столпы, подсистемы, сущности, зависимости и цвета.
Скопируйте этот файл в свой проект и адаптируйте под свои пути и архитектуру.
"""
from pathlib import Path

# Имя проекта и версия игрового движка
PROJECT_NAME = "Project Universe Core (Template)"
ENGINE_VERSION = "Universal (Godot / Unreal / Unity / Custom)"

# Корневая директория проекта для отслеживания git и mtime файлов
PROJECT_ROOT = str(Path(__file__).parent.resolve())

# Временное окно свежести недавних правок (в часах)
FRESH_HOURS = 48

# Палитра основных столпов (семейств)
FAMILY = {
    "engine_core": "#ffe39a",       # Золотистое ядро
    "pillar_match": "#9fb8d0",      # Матч и симуляция
    "pillar_combat": "#ff6f4d",     # Боевая система и юниты
    "pillar_economy": "#ffc64a",    # Экономика и ресурсы
    "pillar_navigation": "#3ee58f", # Навигация и поиск пути
    "pillar_ai": "#e06c75",         # Искусственный интеллект
    "pillar_visuals": "#ff62b4",    # Арт, шейдеры и VFX
    "pillar_ui_audio": "#35d6f0"    # Пользовательский интерфейс и звук
}

# Человекочитаемые названия статусов жизненного цикла узлов
STATUS_NAMES = {
    "idea": "Идея / план",
    "art": "Арт и референсы",
    "proto": "Прототип",
    "wip": "В разработке",
    "live": "Работает в игре",
    "polished": "Отполировано",
    "shelved": "Отложено"
}

# Пользовательские миниатюры/арты (до 720px)
# {"key": "unique_key", "path": "relative/path/to/image.png", "caption": "Описание"}
CUSTOM_ARTS = []

# Словарь узлов графа:
# tier 0: Ядро проекта / Core
# tier 1: Столпы архитектуры (6–9 столпов по Миллеру 7±2)
# tier 2: Подсистемы и менеджеры
# tier 3: Конкретные классы, сущности, карточки юнитов
NODES = {
    # ---------------------------------------------------- Tier 0: Ядро движка
    "engine_core": {
        "label": "Engine Core",
        "tier": 0,
        "parent": None,
        "family": "engine_core",
        "status": "live",
        "human": "Центральное ядро симуляции и цикл обновления: координация всех игровых сервисов, жизненный цикл и менеджмент событий.",
        "paths": ["build_graph.py", "viewer.js", "index.html", "SKILL.md"],
        "tests": ["tests/test_core.py"]
    },

    # ---------------------------------------------------- Tier 1: Столпы архитектуры
    "pillar_match": {
        "label": "Матч и Симуляция",
        "tier": 1,
        "parent": "engine_core",
        "family": "pillar_match",
        "status": "live",
        "human": "Контроллер матча, игровое состояние, репликация кадров, правила победы и поражения.",
        "paths": ["build_graph.py"]
    },
    "pillar_combat": {
        "label": "Бой и Юниты",
        "tier": 1,
        "parent": "engine_core",
        "family": "pillar_combat",
        "status": "live",
        "human": "Боевой расчет, нанесение урона, радиусы стрельбы, типы снарядов и характеристики юнитов.",
        "paths": ["viewer.js"]
    },
    "pillar_economy": {
        "label": "Экономика и Ресурсы",
        "tier": 1,
        "parent": "engine_core",
        "family": "pillar_economy",
        "status": "live",
        "human": "Двухуровневая модель ресурсов, добыча харвестерами, энергосети и очереди строительства.",
        "paths": ["SKILL.md"]
    },
    "pillar_navigation": {
        "label": "Навигация и Навмеш",
        "tier": 1,
        "parent": "engine_core",
        "family": "pillar_navigation",
        "status": "live",
        "human": "Двухдоменный поиск пути: наземные сетки проходимости и высотные эшелоны авиации.",
        "paths": ["build_graph.py"]
    },
    "pillar_ai": {
        "label": "Тактический ИИ",
        "tier": 1,
        "parent": "engine_core",
        "family": "pillar_ai",
        "status": "wip",
        "human": "Многоуровневый ИИ: стратегический макро-директор, тактический анализ фронта и микро-управление юнитами.",
        "paths": ["viewer.js"]
    },
    "pillar_visuals": {
        "label": "Визуальный слой и VFX",
        "tier": 1,
        "parent": "engine_core",
        "family": "pillar_visuals",
        "status": "live",
        "human": "Шейдеры ландшафта, 3D-модели, анимации, системы частиц взрывов и выстрелов.",
        "paths": ["index.html"]
    },
    "pillar_ui_audio": {
        "label": "Интерфейс и Аудио",
        "tier": 1,
        "parent": "engine_core",
        "family": "pillar_ui_audio",
        "status": "proto",
        "human": "Тактическая миникарта, командная панель приказов, селектор отрядов и пространственный 3D-звук.",
        "paths": ["open_graph.bat"]
    },

    # ---------------------------------------------------- Tier 2: Подсистемы
    "sys_match_state": {
        "label": "Система Состояний Матча",
        "tier": 2,
        "parent": "pillar_match",
        "status": "live",
        "human": "Управляет переходами лобби -> пре-матч -> активная фаза -> подведение итогов.",
        "paths": ["build_graph.py"]
    },
    "sys_damage_model": {
        "label": "Баллистика и Урон",
        "tier": 2,
        "parent": "pillar_combat",
        "status": "live",
        "human": "Расчет бронепробития, кинетических рикошетов и сплэш-урона взрывных волн.",
        "paths": ["viewer.js"]
    },
    "sys_economy_core": {
        "label": "Ядро Экономики",
        "tier": 2,
        "parent": "pillar_economy",
        "status": "live",
        "human": "Изолированное математическое ядро транзакций, складов и баланса сырья.",
        "paths": ["SKILL.md"]
    },
    "sys_pathfinding_2d_3d": {
        "label": "Поиск Пути A* / Flowfield",
        "tier": 2,
        "parent": "pillar_navigation",
        "status": "live",
        "human": "Оптимизированный поиск маршрутов для сотен юнитов одновременно с обходом динамических препятствий.",
        "paths": ["build_graph.py"]
    },
    "sys_ai_commander": {
        "label": "ИИ-Главнокомандующий",
        "tier": 2,
        "parent": "pillar_ai",
        "status": "wip",
        "human": "Оценивает баланс сил, планирует наступательные коридоры и управляет базой.",
        "paths": ["viewer.js"]
    },
    "sys_hud_minimap": {
        "label": "Тактическая Миникарта",
        "tier": 2,
        "parent": "pillar_ui_audio",
        "status": "proto",
        "human": "Векторный рендер позиций с туманом войны и индикацией сигналов тревоги.",
        "paths": ["index.html"]
    },

    # ---------------------------------------------------- Tier 3: Сущности и компоненты
    "unit_harvester": {
        "label": "Тяжелый Харвестер",
        "tier": 3,
        "parent": "sys_economy_core",
        "status": "live",
        "human": "Машина добычи ресурсов: обладает высшим дорожным приоритетом в логистическом трафике.",
        "paths": ["SKILL.md"]
    },
    "unit_main_battle_tank": {
        "label": "Основной Боевой Танк",
        "tier": 3,
        "parent": "sys_damage_model",
        "status": "live",
        "human": "Гусеничная бронетехника с тяжелым орудием и круговой башней.",
        "paths": ["viewer.js"]
    },
    "module_flowfield_cache": {
        "label": "Кэш Полей Векторов (Flowfield)",
        "tier": 3,
        "parent": "sys_pathfinding_2d_3d",
        "status": "live",
        "human": "Кэшированные карты направлений движения для группового перемещения армий без коллизий.",
        "paths": ["build_graph.py"]
    }
}

# Явные связи и зависимости между узлами (Dependency Rays):
# types: calls, reads_state, writes, owns, renders, delegates, uses
LINKS = [
    {"source": "sys_match_state", "target": "sys_economy_core", "type": "calls", "label": "инициализация счетов"},
    {"source": "sys_ai_commander", "target": "sys_match_state", "type": "reads_state", "label": "чтение расстановки"},
    {"source": "sys_ai_commander", "target": "sys_pathfinding_2d_3d", "type": "calls", "label": "запрос маршрута"},
    {"source": "unit_main_battle_tank", "target": "sys_damage_model", "type": "calls", "label": "выстрел"},
    {"source": "unit_harvester", "target": "sys_economy_core", "type": "writes", "label": "разгрузка сырья"},
    {"source": "unit_harvester", "target": "sys_pathfinding_2d_3d", "type": "calls", "label": "навигация"},
    {"source": "sys_hud_minimap", "target": "sys_match_state", "type": "reads_state", "label": "позиции юнитов"},
    {"source": "module_flowfield_cache", "target": "sys_pathfinding_2d_3d", "type": "uses", "label": "расчет векторов"}
]
