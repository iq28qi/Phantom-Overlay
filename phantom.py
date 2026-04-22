import sys
import os
import json
import time
import math
import random
import threading
import asyncio
import traceback
from collections import deque

import psutil
import keyboard
import pygetwindow as gw
import pyttsx3
from pypresence import Presence
from ping3 import ping

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QSystemTrayIcon,
    QMenu, QStyle, QDialog, QFormLayout, QSlider, QPushButton, QFileDialog,
    QCheckBox, QHBoxLayout, QLineEdit, QSpinBox, QListWidget,
    QListWidgetItem, QColorDialog, QGraphicsDropShadowEffect, QSizePolicy,
    QFrame, QTextEdit, QStackedWidget, QToolButton, QScrollArea, QGridLayout,
    QComboBox, QMessageBox, QDoubleSpinBox, QInputDialog
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QPoint, QPointF, QPropertyAnimation, QEasingCurve,
    QRectF, QTimer, pyqtProperty, QObject, QEvent
)
from PyQt6.QtGui import (
    QAction, QIcon, QColor, QPainter, QLinearGradient, QRadialGradient,
    QPen, QBrush, QPainterPath, QFont, QFontDatabase, QPixmap, QImage,
    QConicalGradient, QKeySequence
)

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as SessionManager,
    )
    HAS_WINSDK = True
except ImportError:
    HAS_WINSDK = False


# ==========================================================
#                      КОНФИГУРАЦИЯ
# ==========================================================
CONFIG_FILE = "phantom_config.json"

APP_VERSION = "5.1.0 — Hyper+"

DEFAULT_CONFIG: dict = {
    # --- core ---
    "opacity": 235,
    "theme": "dark",
    "language": "ru",                # ru | en
    "bg_image": "",
    "accent_color": "#00ff99",
    "hotkey_toggle": "ctrl+shift+p",
    "hotkey_settings": "ctrl+shift+o",
    "update_interval_ms": 1000,
    "pos_x": 100,
    "pos_y": 100,
    # --- widget visibility ---
    "show_gpu": True,
    "show_cpu": True,
    "show_ram": True,
    "show_network": True,
    "show_music": True,
    "show_visualizer": True,
    "show_ai": True,
    "show_battery": True,
    "show_disk_io": True,
    "show_cpu_temp": True,
    "show_sparklines": True,
    "show_clock": True,
    "show_peak": False,
    "show_in_taskbar": False,
    # --- module order (render order in panel) ---
    "module_order": [
        "header", "chips", "clock", "body", "peak",
        "visualizer", "network", "music", "ai",
    ],
    # --- behaviour ---
    "smart_hide": False,
    "enable_voice": True,
    "compact_mode": False,
    "corner_snap": "none",           # none | tl | tr | bl | br
    "corner_margin": 24,
    "always_on_top": True,
    "click_through": False,
    "drag_lock": False,
    "auto_hide_secs": 0,             # 0 = off; seconds of inactivity before fade
    # --- visual flair ---
    "animated_border": True,
    "particles": True,
    "font_scale": 1.0,
    "corner_radius": 18,             # 8 – 40 px
    "shadow_intensity": 48,          # 0 – 80
    "border_style": "solid",         # solid | dashed | neon | none
    "color_mode": "steps",           # steps | gradient
    "hover_microanim": True,
    "clock_seconds": True,
    # --- window sizing ---
    "window_mode": "auto",           # auto | xs | s | m | l | xl | fixed | free
    "fixed_width": 440,
    "fixed_height": 420,
    # --- thresholds (warn/critical) ---
    "cpu_warn": 80, "cpu_crit": 95,
    "ram_warn": 80, "ram_crit": 92,
    "gpu_warn": 75, "gpu_crit": 85,
    "ping_warn": 60, "ping_crit": 120,
    "ping_host": "8.8.8.8",
    # --- preset name (meta) ---
    "theme_preset": "Neon Mint",
    # --- layout profile slots ---
    "profile_names": {"slot1": "Gaming", "slot2": "Coding", "slot3": "Streaming"},
    "profiles": {"slot1": {}, "slot2": {}, "slot3": {}},
    # --- discord ---
    "discord_enabled": False,
    "discord_client_id": "",
    # --- games ---
    "target_games": [
        "CS2", "Counter-Strike", "Dota 2", "Genshin Impact", "Minecraft",
        "GTA 5", "Cyberpunk 2077", "Valorant", "Fortnite", "Apex Legends",
    ],
}


# ---- i18n ----
TRANSLATIONS: dict = {
    "ru": {
        "app.title": "PHANTOM",
        "app.waiting_media": "🎵  Ожидание медиа…",
        "app.ai_working": "🤖  Silphiette: работаю…",
        "settings.title": "Phantom · Настройки",
        "settings.done": "✔  Готово",
        "settings.live_preview": "LIVE PREVIEW",
        "settings.live_hint": "Изменения применяются мгновенно.\nПресеты — во вкладке «Пресеты».",
        "settings.search": "Поиск по настройкам…",
        "nav.general": "Общие",
        "nav.design": "Дизайн",
        "nav.layout": "Раскладка",
        "nav.modules": "Модули",
        "nav.thresholds": "Пороги",
        "nav.presets": "Пресеты",
        "nav.profiles": "Профили",
        "nav.games": "Игры",
        "nav.about": "О программе",
        "search_ph": "Поиск по настройкам…",
        "settings": "Настройки",
        "hide": "Скрыть",
        "quit": "Выйти",
        "wait_media": "Ожидание медиа…",
        "working": "работаю…",
        "page.layout.title": "Раскладка и окно",
        "page.layout.subtitle": "Порядок модулей, размер окна, профили лейаута. Перетаскивай модули стрелками.",
        "layout.order": "Порядок модулей",
        "layout.order_hint": "Стрелки ↑ ↓ меняют порядок. Галочка — виден ли модуль.",
        "layout.window": "Размер и режим окна",
        "layout.profiles": "Профили лейаута",
        "layout.profile_save": "💾 Сохранить",
        "layout.profile_load": "▶ Загрузить",
        "layout.profile_rename": "✎ Имя",
        "layout.profile_empty": "— пусто —",
        "layout.profile_saved": "Профиль сохранён",
        "layout.profile_loaded": "Профиль загружен",
        "layout.rename_title": "Имя профиля",
        "layout.rename_prompt": "Новое имя:",
        "page.general.title": "Общие настройки",
        "page.general.subtitle": "Хоткеи, язык, интервал обновления, поведение окна, перенос конфигурации.",
        "page.design.title": "Дизайн и внешний вид",
        "page.design.subtitle": "Акцент, прозрачность, форма окна, эффекты, фон.",
        "page.modules.title": "Модули оверлея",
        "page.modules.subtitle": "Какие блоки показывать и в каком порядке. Стрелки ↑ ↓ меняют порядок.",
        "page.thresholds.title": "Пороги тревог",
        "page.thresholds.subtitle": "Warn — карточка желтеет, Critical — краснеет (+ голос для GPU).",
        "page.presets.title": "Темы-пресеты",
        "page.presets.subtitle": "Клик — мгновенно применяет акцент, прозрачность и эффекты.",
        "page.profiles.title": "Профили лейаута",
        "page.profiles.subtitle": "Три слота для полного снимка конфигурации. Сохрани — переключай одним кликом.",
        "page.games.title": "Игры для Smart Focus",
        "page.games.subtitle": "Оверлей появится, когда заголовок активного окна содержит одну из этих строк.",
        "page.about.title": "О программе",
        "g.hotkey_toggle": "Хоткей: показать/скрыть:",
        "g.hotkey_settings": "Хоткей: открыть настройки:",
        "g.interval": "Интервал обновления:",
        "g.corner_snap": "Прилипание к углу:",
        "g.corner_margin": "Отступ от края:",
        "g.behaviour": "Поведение:",
        "g.sound": "Звук:",
        "g.system": "Система:",
        "g.language": "Язык интерфейса:",
        "g.ping_host": "Хост для ping:",
        "g.window": "Окно:",
        "g.config_section": "Конфигурация",
        "g.export": "↓  Экспорт",
        "g.import": "↑  Импорт",
        "g.reset": "↺  Сбросить к дефолту",
        "g.smart_hide": "Показывать только в играх (Smart Focus)",
        "g.voice": "Голос при перегреве GPU",
        "g.taskbar": "Значок на панели задач",
        "g.always_on_top": "Поверх всех окон",
        "g.click_through": "Сквозные клики (мышь проходит через оверлей)",
        "g.drag_lock": "Блокировать перетаскивание",
        "g.autohide": "Авто-скрытие через (сек, 0 = выкл):",
        "snap.none": "— не прилипать",
        "snap.tl": "↖ Верхний левый",
        "snap.tr": "↗ Верхний правый",
        "snap.bl": "↙ Нижний левый",
        "snap.br": "↘ Нижний правый",
        "d.opacity": "Прозрачность:",
        "d.accent": "Акцентный цвет:",
        "d.quick_color": "Быстрый цвет:",
        "d.font_scale": "Масштаб шрифта:",
        "d.effects": "Эффекты:",
        "d.layout": "Раскладка:",
        "d.bg": "Обои окна:",
        "d.corner_radius": "Скругление углов:",
        "d.shadow": "Интенсивность тени:",
        "d.border_style": "Стиль бордера:",
        "d.window_mode": "Размер окна:",
        "d.fixed_w": "Ширина (фикс):",
        "d.fixed_h": "Высота (фикс):",
        "d.compact": "Компактный режим",
        "d.border_rot": "Вращающийся conic-бордер (WOW)",
        "d.particles": "Светящиеся частицы",
        "d.choose_bg": "📁  Выбрать фон",
        "d.clear_bg": "✕  Убрать",
        "wm.auto": "Автоматически",
        "wm.xs": "XS · 280×260",
        "wm.s": "S · 340×320",
        "wm.m": "M · 420×400",
        "wm.l": "L · 520×500",
        "wm.xl": "XL · 640×620",
        "wm.fixed": "Фиксированный (свой размер)",
        "wm.free": "Свободный (тяни за край)",
        "bs.solid": "Сплошной",
        "bs.dashed": "Пунктирный",
        "bs.neon": "Неоновый glow",
        "bs.none": "Без бордера",
        "mod.gpu": "GPU индикатор (кольцо)",
        "mod.cpu": "CPU карточка",
        "mod.ram": "RAM карточка",
        "mod.network": "Сеть (ping / ↑ / ↓)",
        "mod.music": "Медиа (трек)",
        "mod.visualizer": "Аудио-визуализатор",
        "mod.ai": "AI ассистент Silphiette",
        "mod.battery": "Батарея (для ноутбуков)",
        "mod.disk_io": "Диск I/O (чтение / запись)",
        "mod.cpu_temp": "Температура CPU (если доступна)",
        "mod.sparklines": "Мини-графики (sparklines)",
        "mod.clock": "Часы (HH:MM:SS)",
        "mod.peak": "Пиковые значения за сессию",
        "mod.clock_seconds": "Показывать секунды на часах",
        "pr.save": "💾  Сохранить сюда",
        "pr.load": "▶   Загрузить",
        "pr.rename": "✎  Переименовать",
        "pr.empty": "— пусто —",
        "about.header": "Phantom Overlay · Hyper Edition",
        "about.body": "Phantom — кастомный внутриигровой HUD нового поколения. Полная редактируемость: круговой GPU-gauge, живой preview в настройках, профили, 8 тем-пресетов, RU/EN, резайз окна, модульный порядок виджетов.",
        "about.hotkeys": "Хоткеи настраиваются во вкладке «Общие».",
        "about.license": "Лицензия: MIT · PyQt6, psutil, ping3, winsdk, pypresence\nАвтор: iq28qi",
        "games.add_placeholder": "Название или часть названия игры…",
        "games.add": "✚  Добавить",
        "games.remove": "🗑  Удалить",
        "reset.msg": "Настройки сброшены к значениям по умолчанию.",
        "reset.title": "Сброс",
    },
    "en": {
        "app.title": "PHANTOM",
        "app.waiting_media": "🎵  Waiting for media…",
        "app.ai_working": "🤖  Silphiette: working…",
        "settings.title": "Phantom · Settings",
        "settings.done": "✔  Done",
        "settings.live_preview": "LIVE PREVIEW",
        "settings.live_hint": "Changes apply instantly.\nThemes on the Presets tab.",
        "settings.search": "Search settings…",
        "nav.general": "General",
        "nav.design": "Design",
        "nav.layout": "Layout",
        "nav.modules": "Modules",
        "nav.thresholds": "Thresholds",
        "nav.presets": "Presets",
        "nav.profiles": "Profiles",
        "nav.games": "Games",
        "nav.about": "About",
        "search_ph": "Search settings…",
        "settings": "Settings",
        "hide": "Hide",
        "quit": "Quit",
        "wait_media": "Waiting for media…",
        "working": "working…",
        "page.layout.title": "Layout & window",
        "page.layout.subtitle": "Module order, window size, layout profiles. Reorder modules with arrows.",
        "layout.order": "Module order",
        "layout.order_hint": "Arrows ↑ ↓ reorder. Checkbox — whether module is visible.",
        "layout.window": "Window size & mode",
        "layout.profiles": "Layout profiles",
        "layout.profile_save": "💾 Save",
        "layout.profile_load": "▶ Load",
        "layout.profile_rename": "✎ Rename",
        "layout.profile_empty": "— empty —",
        "layout.profile_saved": "Profile saved",
        "layout.profile_loaded": "Profile loaded",
        "layout.rename_title": "Profile name",
        "layout.rename_prompt": "New name:",
        "page.general.title": "General",
        "page.general.subtitle": "Hotkeys, language, update interval, window behaviour, config transfer.",
        "page.design.title": "Design & appearance",
        "page.design.subtitle": "Accent, opacity, window shape, effects, background.",
        "page.modules.title": "Overlay modules",
        "page.modules.subtitle": "Which blocks to show and in what order. Arrows ↑ ↓ reorder.",
        "page.thresholds.title": "Alert thresholds",
        "page.thresholds.subtitle": "Warn — card turns yellow, Critical — red (+ voice for GPU).",
        "page.presets.title": "Theme presets",
        "page.presets.subtitle": "Click — instantly applies accent, opacity and effects.",
        "page.profiles.title": "Layout profiles",
        "page.profiles.subtitle": "Three slots for a full config snapshot. Save — switch with one click.",
        "page.games.title": "Smart Focus games",
        "page.games.subtitle": "Overlay appears when the active window title contains one of these strings.",
        "page.about.title": "About",
        "g.hotkey_toggle": "Hotkey: show/hide:",
        "g.hotkey_settings": "Hotkey: open settings:",
        "g.interval": "Update interval:",
        "g.corner_snap": "Snap to corner:",
        "g.corner_margin": "Corner margin:",
        "g.behaviour": "Behaviour:",
        "g.sound": "Sound:",
        "g.system": "System:",
        "g.language": "Interface language:",
        "g.ping_host": "Ping host:",
        "g.window": "Window:",
        "g.config_section": "Configuration",
        "g.export": "↓  Export",
        "g.import": "↑  Import",
        "g.reset": "↺  Reset to defaults",
        "g.smart_hide": "Show only in games (Smart Focus)",
        "g.voice": "Voice on GPU overheat",
        "g.taskbar": "Show in taskbar",
        "g.always_on_top": "Always on top",
        "g.click_through": "Click-through (mouse passes through)",
        "g.drag_lock": "Lock dragging",
        "g.autohide": "Auto-hide after (sec, 0 = off):",
        "snap.none": "— don't snap",
        "snap.tl": "↖ Top-left",
        "snap.tr": "↗ Top-right",
        "snap.bl": "↙ Bottom-left",
        "snap.br": "↘ Bottom-right",
        "d.opacity": "Opacity:",
        "d.accent": "Accent color:",
        "d.quick_color": "Quick color:",
        "d.font_scale": "Font scale:",
        "d.effects": "Effects:",
        "d.layout": "Layout:",
        "d.bg": "Background image:",
        "d.corner_radius": "Corner radius:",
        "d.shadow": "Shadow intensity:",
        "d.border_style": "Border style:",
        "d.window_mode": "Window size:",
        "d.fixed_w": "Width (fixed):",
        "d.fixed_h": "Height (fixed):",
        "d.compact": "Compact mode",
        "d.border_rot": "Rotating conic border (WOW)",
        "d.particles": "Glowing particles",
        "d.choose_bg": "📁  Choose bg",
        "d.clear_bg": "✕  Clear",
        "wm.auto": "Auto",
        "wm.xs": "XS · 280×260",
        "wm.s": "S · 340×320",
        "wm.m": "M · 420×400",
        "wm.l": "L · 520×500",
        "wm.xl": "XL · 640×620",
        "wm.fixed": "Fixed (custom size)",
        "wm.free": "Free (drag edges)",
        "bs.solid": "Solid",
        "bs.dashed": "Dashed",
        "bs.neon": "Neon glow",
        "bs.none": "None",
        "mod.gpu": "GPU ring",
        "mod.cpu": "CPU card",
        "mod.ram": "RAM card",
        "mod.network": "Network (ping / ↑ / ↓)",
        "mod.music": "Media (track)",
        "mod.visualizer": "Audio visualizer",
        "mod.ai": "Silphiette AI assistant",
        "mod.battery": "Battery (for laptops)",
        "mod.disk_io": "Disk I/O (read / write)",
        "mod.cpu_temp": "CPU temperature",
        "mod.sparklines": "Mini sparklines",
        "mod.clock": "Clock (HH:MM:SS)",
        "mod.peak": "Session peak values",
        "mod.clock_seconds": "Show seconds on clock",
        "pr.save": "💾  Save here",
        "pr.load": "▶   Load",
        "pr.rename": "✎  Rename",
        "pr.empty": "— empty —",
        "about.header": "Phantom Overlay · Hyper Edition",
        "about.body": "Phantom — a next-gen fully customizable in-game HUD. Circular GPU gauge, live preview in settings, profiles, 8 themes, RU/EN, window resize, modular widget order.",
        "about.hotkeys": "Hotkeys are configured on the General tab.",
        "about.license": "License: MIT · PyQt6, psutil, ping3, winsdk, pypresence\nAuthor: iq28qi",
        "games.add_placeholder": "Game name or substring…",
        "games.add": "✚  Add",
        "games.remove": "🗑  Remove",
        "reset.msg": "Settings reset to defaults.",
        "reset.title": "Reset",
    },
}


# ---- window-mode size table ----
WINDOW_SIZES: dict = {
    "xs": (280, 260),
    "s":  (340, 320),
    "m":  (420, 400),
    "l":  (520, 500),
    "xl": (640, 620),
}


_CURRENT_LANG = "ru"


def tr(key: str) -> str:
    """Resolve an i18n key against the current language with RU fallback."""
    lang = _CURRENT_LANG if _CURRENT_LANG in TRANSLATIONS else "ru"
    return TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["ru"].get(key, key)


def set_language(code: str) -> None:
    global _CURRENT_LANG
    _CURRENT_LANG = code if code in TRANSLATIONS else "ru"


# Theme presets — применяются к config поверх текущих значений.
THEME_PRESETS: dict = {
    "Neon Mint":   {"accent_color": "#00ff99", "opacity": 235, "animated_border": True,  "particles": True,  "compact_mode": False, "bg_image": ""},
    "Ultraviolet": {"accent_color": "#a78bfa", "opacity": 235, "animated_border": True,  "particles": True,  "compact_mode": False, "bg_image": ""},
    "Cyber Cyan":  {"accent_color": "#22d3ee", "opacity": 240, "animated_border": True,  "particles": True,  "compact_mode": False, "bg_image": ""},
    "Magma":       {"accent_color": "#ff7a59", "opacity": 230, "animated_border": True,  "particles": False, "compact_mode": False, "bg_image": ""},
    "Sakura":      {"accent_color": "#ff6ba8", "opacity": 225, "animated_border": True,  "particles": True,  "compact_mode": True,  "bg_image": ""},
    "Matrix":      {"accent_color": "#29ff7a", "opacity": 245, "animated_border": True,  "particles": True,  "compact_mode": False, "bg_image": ""},
    "Stealth":     {"accent_color": "#9aa4c7", "opacity": 210, "animated_border": False, "particles": False, "compact_mode": True,  "bg_image": ""},
    "Gold":        {"accent_color": "#f5c24c", "opacity": 235, "animated_border": True,  "particles": True,  "compact_mode": False, "bg_image": ""},
}


def log_err(prefix: str, exc: BaseException) -> None:
    """Единая точка логирования ошибок."""
    try:
        sys.stderr.write(f"[phantom][{prefix}] {type(exc).__name__}: {exc}\n")
    except Exception:
        pass


# ==========================================================
#               ВШИТЫЕ ШРИФТЫ (bundled fonts)
# ==========================================================
# Значения по умолчанию — системные шрифты Windows.
# После `load_bundled_fonts()` подменяются на Inter / JetBrains Mono,
# если их .ttf лежат в папке `fonts/` рядом с phantom.py.
UI_FONT_FAMILY: str = "Segoe UI"
MONO_FONT_FAMILY: str = "Consolas"
_FONTS_LOADED: bool = False


def _bundled_fonts_dir() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "fonts")


def load_bundled_fonts() -> None:
    """Регистрирует вшитые .ttf через QFontDatabase и обновляет UI/MONO family."""
    global UI_FONT_FAMILY, MONO_FONT_FAMILY, _FONTS_LOADED
    if _FONTS_LOADED:
        return
    fonts_dir = _bundled_fonts_dir()
    if not os.path.isdir(fonts_dir):
        _FONTS_LOADED = True
        return

    def _register(filename: str) -> str | None:
        path = os.path.join(fonts_dir, filename)
        if not os.path.exists(path):
            return None
        try:
            fid = QFontDatabase.addApplicationFont(path)
            if fid < 0:
                return None
            fams = QFontDatabase.applicationFontFamilies(fid)
            return fams[0] if fams else None
        except Exception as e:
            log_err("fonts.register", e)
            return None

    try:
        ui = _register("Inter.ttf")
        if ui:
            UI_FONT_FAMILY = ui
        mono = _register("JetBrainsMono.ttf")
        if mono:
            MONO_FONT_FAMILY = mono
    except Exception as e:
        log_err("fonts.load", e)
    _FONTS_LOADED = True


def _qss_ui_font_family() -> str:
    """Стилевое значение для `font-family` — кастомный первым, системный фолбэк."""
    if UI_FONT_FAMILY != "Segoe UI":
        return f"'{UI_FONT_FAMILY}', 'Segoe UI'"
    return "'Segoe UI'"


def _qss_mono_font_family() -> str:
    if MONO_FONT_FAMILY != "Consolas":
        return f"'{MONO_FONT_FAMILY}', 'Consolas'"
    return "'Consolas'"


# ==========================================================
#               ЦВЕТОВОЙ РЕЖИМ (пороги / градиент)
# ==========================================================
_COLOR_MODE: str = "steps"  # steps | gradient


def set_color_mode(mode: str) -> None:
    """Переключить глобальный режим маппинга цвета по нагрузке."""
    global _COLOR_MODE
    _COLOR_MODE = mode if mode in ("steps", "gradient") else "steps"


def load_config() -> dict:
    cfg = {**DEFAULT_CONFIG, "target_games": list(DEFAULT_CONFIG["target_games"])}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg.update(data)
            games = cfg.get("target_games") or DEFAULT_CONFIG["target_games"]
            cfg["target_games"] = [str(g).strip() for g in games if str(g).strip()]
        except (OSError, json.JSONDecodeError) as e:
            log_err("config.load", e)
    return cfg


def save_config(config: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except OSError as e:
        log_err("config.save", e)


# ==========================================================
#              ПАЛИТРА / ВСПОМОГАТЕЛЬНЫЕ
# ==========================================================
def _mix(c1: QColor, c2: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red()   * (1 - t) + c2.red()   * t),
        int(c1.green() * (1 - t) + c2.green() * t),
        int(c1.blue()  * (1 - t) + c2.blue()  * t),
        int(c1.alpha() * (1 - t) + c2.alpha() * t),
    )


def _color_for_load(percent: float, accent: QColor, warn: float = 70, crit: float = 90) -> QColor:
    yellow = QColor("#ffcc66")
    red = QColor("#ff5c5c")
    if _COLOR_MODE == "gradient":
        # Чистый линейный градиент accent → yellow → red по всему диапазону 0-100%.
        t = max(0.0, min(1.0, float(percent) / 100.0))
        if t < 0.5:
            return _mix(accent, yellow, t * 2.0)
        return _mix(yellow, red, (t - 0.5) * 2.0)
    if percent < warn:
        return _mix(accent, yellow, (percent / max(1.0, warn)) * 0.35)
    if percent < crit:
        return _mix(yellow, red, (percent - warn) / max(1.0, crit - warn))
    return red


def _color_for_temp(temp: int, accent: QColor, warn: int = 70, crit: int = 85) -> QColor:
    cool = QColor("#4cd9ff")
    yellow = QColor("#ffcc66")
    red = QColor("#ff5c5c")
    if _COLOR_MODE == "gradient":
        # Линейный градиент cool → accent → yellow → red от 20°C до crit+15°C.
        lo, hi = 20.0, float(crit) + 15.0
        t = max(0.0, min(1.0, (float(temp) - lo) / max(1.0, hi - lo)))
        if t < 0.33:
            return _mix(cool, accent, t / 0.33)
        if t < 0.66:
            return _mix(accent, yellow, (t - 0.33) / 0.33)
        return _mix(yellow, red, (t - 0.66) / 0.34)
    if temp <= 45:
        return _mix(cool, accent, temp / 45.0)
    if temp <= warn:
        return accent
    if temp <= crit:
        return _mix(accent, yellow, (temp - warn) / max(1, crit - warn))
    return red


def _fmt_bytes(v: float) -> str:
    v = float(v)
    for unit in ("B", "KB", "MB", "GB"):
        if v < 1024 or unit == "GB":
            return f"{v:.0f} {unit}" if unit == "B" else f"{v:.1f} {unit}"
        v /= 1024.0
    return f"{v:.1f} GB"


# ==========================================================
#              МИКРО-АНИМАЦИИ (hover lift)
# ==========================================================
class HoverGlow(QObject):
    """
    Цепляет к виджету QGraphicsDropShadowEffect с анимированным blurRadius
    на `Enter` / `Leave`. Даёт ощущение «поднятой» карточки без изменений
    layout'а. Работает через event-filter, чтобы не трогать paintEvent/enterEvent
    виджета и не ломать его наследников.
    """

    _ENABLED: bool = True

    def __init__(
        self,
        widget: QWidget,
        accent: str = "#00ff99",
        base_blur: float = 0.0,
        hover_blur: float = 22.0,
        duration_ms: int = 180,
    ) -> None:
        super().__init__(widget)
        color = QColor(accent)
        color.setAlpha(180)
        self._effect = QGraphicsDropShadowEffect(widget)
        self._effect.setColor(color)
        self._effect.setBlurRadius(base_blur)
        self._effect.setOffset(0, 0)
        widget.setGraphicsEffect(self._effect)

        self._anim = QPropertyAnimation(self._effect, b"blurRadius", self)
        self._anim.setDuration(duration_ms)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._base_blur = float(base_blur)
        self._hover_blur = float(hover_blur)
        self._hovered = False
        widget.installEventFilter(self)

    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        """Глобально включить/выключить micro-animations (например, через настройки)."""
        cls._ENABLED = bool(enabled)

    def set_accent(self, accent: str) -> None:
        color = QColor(accent)
        color.setAlpha(180)
        self._effect.setColor(color)

    def set_blur_range(self, base: float, hover: float) -> None:
        self._base_blur = float(base)
        self._hover_blur = float(hover)
        self._animate_to(self._hover_blur if self._hovered else self._base_blur)

    def _animate_to(self, target: float) -> None:
        if not HoverGlow._ENABLED:
            self._anim.stop()
            self._effect.setBlurRadius(self._base_blur)
            return
        self._anim.stop()
        self._anim.setStartValue(self._effect.blurRadius())
        self._anim.setEndValue(target)
        self._anim.start()

    def eventFilter(self, _obj, event):  # type: ignore[override]
        t = event.type()
        if t == QEvent.Type.Enter:
            self._hovered = True
            self._animate_to(self._hover_blur)
        elif t == QEvent.Type.Leave:
            self._hovered = False
            self._animate_to(self._base_blur)
        return False


# ==========================================================
#               ЯДРО АССИСТЕНТА / DISCORD
# ==========================================================
class PhantomCore:
    """Голосовые алерты (pyttsx3), Discord RPC (pypresence) и управление медиа
    через Windows SDK. Умеет безопасно деградировать, если какая-то из
    подсистем недоступна на этой машине (например, AMD-карта без NVML или
    не-Windows хост)."""

    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 180)
        except Exception as e:
            log_err("tts.init", e)
            self.engine = None
        self.last_speech_time = 0
        self.rpc = None
        self.discord_connected = False

    def init_discord(self, client_id: str) -> None:
        if not client_id:
            return
        try:
            self.rpc = Presence(client_id)
            self.rpc.connect()
            self.discord_connected = True
        except Exception as e:
            log_err("discord.connect", e)
            self.discord_connected = False

    def update_discord(self, state: str, details: str) -> None:
        if not (self.discord_connected and self.rpc):
            return
        try:
            self.rpc.update(state=state, details=details, large_image="logo")
        except Exception as e:
            log_err("discord.update", e)

    def say(self, text: str) -> None:
        if self.engine is None:
            return
        if time.time() - self.last_speech_time < 15:
            return
        self.last_speech_time = time.time()

        def _speak():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                log_err("tts.say", e)

        threading.Thread(target=_speak, daemon=True).start()


# ==========================================================
#                 ПОТОК МОНИТОРИНГА ЖЕЛЕЗА
# ==========================================================
class HardwareMonitorThread(QThread):
    """Фоновой поток сбора телеметрии: CPU/RAM/GPU/Temp/Disk/Net/Battery/Ping.

    На каждой итерации эмитит :pyattr:`data_updated` со словарём значений,
    который потребляет главный UI-поток. Любой сбой конкретного измерения
    (NVML, sensors_temperatures, ping и т.д.) логируется, но не валит цикл."""

    data_updated = pyqtSignal(dict)

    def __init__(self, interval_ms: int = 1000, ping_host: str = "8.8.8.8"):
        super().__init__()
        self.running = True
        self._interval = max(200, int(interval_ms)) / 1000.0
        self._ping_host = (ping_host or "8.8.8.8").strip()
        self.nvml_initialized = False
        self.loop = asyncio.new_event_loop()
        self._prev_net = None
        self._prev_net_time = None
        self._prev_disk = None
        self._prev_disk_time = None
        try:
            import pynvml
            pynvml.nvmlInit()
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.nvml_initialized = True
            self.pynvml = pynvml
        except Exception as e:
            log_err("nvml.init", e)

    def set_interval_ms(self, interval_ms: int) -> None:
        self._interval = max(200, int(interval_ms)) / 1000.0

    def set_ping_host(self, host: str) -> None:
        self._ping_host = (host or "8.8.8.8").strip()

    def stop(self) -> None:
        self.running = False

    def run(self):
        asyncio.set_event_loop(self.loop)
        while self.running:
            data: dict = {}

            try:
                data["cpu"] = psutil.cpu_percent()
                data["ram"] = psutil.virtual_memory().percent
            except Exception as e:
                log_err("psutil", e)
                data["cpu"] = 0; data["ram"] = 0

            # CPU temp (best-effort, cross-platform)
            data["cpu_temp"] = None
            try:
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    for key in ("coretemp", "cpu_thermal", "k10temp", "acpitz"):
                        if key in temps and temps[key]:
                            data["cpu_temp"] = int(temps[key][0].current)
                            break
            except Exception as e:
                log_err("cpu_temp", e)

            # Battery (laptops)
            data["battery_percent"] = None
            data["battery_plugged"] = None
            try:
                bat = psutil.sensors_battery()
                if bat is not None:
                    data["battery_percent"] = int(bat.percent)
                    data["battery_plugged"] = bool(bat.power_plugged)
            except Exception as e:
                log_err("battery", e)

            # GPU (NVIDIA)
            if self.nvml_initialized:
                try:
                    data["gpu_temp"] = self.pynvml.nvmlDeviceGetTemperature(
                        self.gpu_handle, self.pynvml.NVML_TEMPERATURE_GPU
                    )
                    data["gpu_util"] = self.pynvml.nvmlDeviceGetUtilizationRates(
                        self.gpu_handle
                    ).gpu
                except Exception as e:
                    log_err("nvml.read", e)
                    data["gpu_temp"], data["gpu_util"] = 0, 0
            else:
                data["gpu_temp"], data["gpu_util"] = None, None

            # Ping
            try:
                host = getattr(self, "_ping_host", "8.8.8.8") or "8.8.8.8"
                p = ping(host, timeout=1)
                data["ping"] = int(p * 1000) if p else None
            except Exception as e:
                log_err("ping", e)
                data["ping"] = None

            # Network rates
            try:
                counters = psutil.net_io_counters()
                now = time.time()
                if self._prev_net is not None and self._prev_net_time is not None:
                    dt = max(0.001, now - self._prev_net_time)
                    data["net_up"] = (counters.bytes_sent - self._prev_net.bytes_sent) / dt / 1024.0
                    data["net_down"] = (counters.bytes_recv - self._prev_net.bytes_recv) / dt / 1024.0
                else:
                    data["net_up"], data["net_down"] = 0.0, 0.0
                self._prev_net = counters
                self._prev_net_time = now
            except Exception as e:
                log_err("net", e)
                data["net_up"], data["net_down"] = 0.0, 0.0

            # Disk I/O
            try:
                dio = psutil.disk_io_counters()
                now = time.time()
                if dio is not None and self._prev_disk is not None and self._prev_disk_time is not None:
                    dt = max(0.001, now - self._prev_disk_time)
                    data["disk_read"] = (dio.read_bytes - self._prev_disk.read_bytes) / dt
                    data["disk_write"] = (dio.write_bytes - self._prev_disk.write_bytes) / dt
                else:
                    data["disk_read"], data["disk_write"] = 0.0, 0.0
                if dio is not None:
                    self._prev_disk = dio
                    self._prev_disk_time = now
            except Exception as e:
                log_err("disk", e)
                data["disk_read"], data["disk_write"] = 0.0, 0.0

            # Music
            try:
                data["music"] = self.loop.run_until_complete(self.get_music_info())
            except Exception as e:
                log_err("media", e)
                data["music"] = "No Media"

            # Active window
            try:
                win = gw.getActiveWindow()
                data["active_title"] = win.title if win else ""
            except Exception as e:
                log_err("gw", e)
                data["active_title"] = ""

            self.data_updated.emit(data)
            slept = 0.0
            while self.running and slept < self._interval:
                time.sleep(0.1)
                slept += 0.1

    async def get_music_info(self):
        if not HAS_WINSDK:
            return ""
        try:
            sessions = await SessionManager.request_async()
            curr = sessions.get_current_session()
            if curr:
                info = await curr.try_get_media_properties_async()
                return f"{info.artist or 'Unknown'} — {info.title or 'Track'}"
            return ""
        except Exception as e:
            log_err("winsdk.media", e)
            return ""


# ==========================================================
#                   ВИДЖЕТЫ: БАЗОВЫЕ
# ==========================================================
class Sparkline(QWidget):
    """Мини-график на N точек с автоматическим глоу — рисуется ровно внутри
    выделенного rect, без осей, подписей и прочего шума."""

    def __init__(self, capacity: int = 60, color: str = "#00ff99", parent=None):
        super().__init__(parent)
        self._buf: deque[float] = deque(maxlen=capacity)
        self._color = QColor(color)
        self.setMinimumHeight(22)
        self.setMaximumHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def push(self, value: float) -> None:
        try:
            self._buf.append(max(0.0, min(100.0, float(value))))
        except (TypeError, ValueError):
            self._buf.append(0.0)
        self.update()

    def paintEvent(self, _event):
        if len(self._buf) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width(); h = self.height()
        n = self._buf.maxlen or 60
        step = w / (n - 1)
        start_x = w - step * (len(self._buf) - 1)
        pts = []
        for i, v in enumerate(self._buf):
            x = start_x + i * step
            y = h - (v / 100.0) * (h - 2) - 1
            pts.append(QPointF(x, y))
        if not pts:
            return

        fill_path = QPainterPath()
        fill_path.moveTo(pts[0].x(), h)
        for p in pts:
            fill_path.lineTo(p)
        fill_path.lineTo(pts[-1].x(), h)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        c1 = QColor(self._color); c1.setAlpha(130)
        c2 = QColor(self._color); c2.setAlpha(0)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        painter.fillPath(fill_path, QBrush(grad))

        line_path = QPainterPath(); line_path.moveTo(pts[0])
        for p in pts[1:]:
            line_path.lineTo(p)
        pen = QPen(self._color)
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(line_path)


class StatusDot(QWidget):
    """Маленькая круглая «лампочка» состояния в заголовке: зелёная в норме,
    жёлтая при warn, красная при crit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#00ff99")
        self._pulse = 0.0
        self.setFixedSize(14, 14)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)

    def set_color(self, color: str) -> None:
        self._color = QColor(color); self.update()

    def _tick(self) -> None:
        self._pulse = (self._pulse + 0.08) % (2 * math.pi)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        alpha = int(60 + 80 * (0.5 + 0.5 * math.sin(self._pulse)))
        halo = QRadialGradient(w/2, h/2, w/2)
        c_in = QColor(self._color); c_in.setAlpha(alpha)
        c_out = QColor(self._color); c_out.setAlpha(0)
        halo.setColorAt(0.0, c_in); halo.setColorAt(1.0, c_out)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(halo))
        p.drawEllipse(0, 0, w, h)
        p.setBrush(QColor(self._color))
        p.drawEllipse(int(w/2 - 3), int(h/2 - 3), 6, 6)


class IconButton(QToolButton):
    """Флэт-кнопка 22×22 с единственным глифом/эмодзи внутри. Стилизована
    под header оверлея и использует :class:`HoverGlow` для мягкого lift'а
    при наведении."""

    def __init__(self, glyph: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setText(glyph); self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoRaise(True); self.setFixedSize(22, 22)
        self.setStyleSheet(
            f"""
            QToolButton {{
                color: rgba(255,255,255,160);
                background: rgba(255,255,255,10);
                border: 1px solid rgba(255,255,255,18);
                border-radius: 6px;
                font-family: {_qss_ui_font_family()}; font-weight: 800; font-size: 11px;
            }}
            QToolButton:hover {{
                color: #ffffff;
                background: rgba(255,255,255,28);
                border: 1px solid rgba(255,255,255,40);
            }}
            QToolButton:pressed {{ background: rgba(255,255,255,48); }}
            """
        )
        # Лёгкий glow-lift при наведении.
        self._hover_glow = HoverGlow(self, accent="#ffffff", base_blur=0.0, hover_blur=12.0, duration_ms=140)


class Marquee(QLabel):
    """QLabel с горизонтальной прокруткой текста влево, когда строка не
    помещается в видимую ширину. Используется для длинных названий треков."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full = ""
        self._offset = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def setText(self, text: str) -> None:  # type: ignore[override]
        if text == self._full:
            return
        self._full = text or ""
        self._offset = 0
        fm = self.fontMetrics()
        if fm.horizontalAdvance(self._full) > self.width() - 4:
            self._timer.start(45)
        else:
            self._timer.stop()
        super().setText(self._full)

    def _tick(self) -> None:
        self._offset = (self._offset + 1) % max(1, self.fontMetrics().horizontalAdvance(self._full + "   "))
        self.update()

    def paintEvent(self, event):
        if not self._timer.isActive():
            return super().paintEvent(event)
        p = QPainter(self)
        p.setPen(self.palette().color(self.foregroundRole()))
        p.setFont(self.font())
        text = self._full + "     " + self._full
        fm = self.fontMetrics()
        y = (self.height() + fm.ascent() - fm.descent()) // 2
        p.drawText(-self._offset, y, text)


class Chip(QLabel):
    """Стильный pill-chip для вторичных метрик (battery / disk / cpu temp)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._accent = "#00ff99"
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont(UI_FONT_FAMILY, 9); f.setWeight(QFont.Weight.ExtraBold)
        self.setFont(f)
        self._refresh()

    def set_accent(self, color: str) -> None:
        self._accent = color; self._refresh()

    def _refresh(self) -> None:
        self.setStyleSheet(
            "color: rgba(255,255,255,210); "
            "background: rgba(255,255,255,12); "
            "border: 1px solid rgba(255,255,255,24); "
            "border-radius: 9px; padding: 3px 10px;"
        )


# ==========================================================
#                 ВИДЖЕТЫ: МЕТРИКИ
# ==========================================================
class MetricCard(QWidget):
    """Карточка метрики (CPU / RAM) с анимированным процентом, сопутствующим
    текстом, опциональной sparkline-историей, HoverGlow-эффектом и цветовой
    индикацией — steps или gradient, в зависимости от глобального режима
    :data:`_COLOR_MODE`."""

    def __init__(self, icon: str, name: str, accent: str = "#00ff99",
                 show_sparkline: bool = True,
                 warn: float = 80.0, crit: float = 95.0, parent=None):
        super().__init__(parent)
        self._icon = icon; self._name = name
        self._accent = QColor(accent)
        self._warn = warn; self._crit = crit
        self._value_anim = 0.0
        self._value_target = 0.0
        self._value_text = "--"; self._secondary_text = ""
        self._critical = False
        self._anim = QPropertyAnimation(self, b"animatedValue")
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._build_ui(show_sparkline)
        # Мягкий glow-lift при наведении на карточку.
        self._hover_glow = HoverGlow(self, accent=accent, base_blur=0.0, hover_blur=26.0, duration_ms=220)

    def get_animated_value(self) -> float: return self._value_anim
    def set_animated_value(self, v: float) -> None:
        self._value_anim = max(0.0, min(100.0, float(v)))
        self.update()
    animatedValue = pyqtProperty(float, fget=get_animated_value, fset=set_animated_value)

    def _build_ui(self, show_sparkline: bool) -> None:
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10); root.setSpacing(4)
        top = QHBoxLayout(); top.setContentsMargins(0, 0, 0, 0); top.setSpacing(8)

        self.lbl_icon = QLabel(self._icon)
        self.lbl_icon.setStyleSheet("font-family: 'Inter', 'Segoe UI'; font-size: 14px;")
        self.lbl_name = QLabel(self._name)
        self.lbl_name.setStyleSheet(
            "color: rgba(255,255,255,170); font-family: 'Inter', 'Segoe UI'; "
            "font-size: 10px; font-weight: 800; letter-spacing: 1.8px;"
        )
        self.lbl_value = QLabel("--")
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        f = QFont(UI_FONT_FAMILY, 15); f.setWeight(QFont.Weight.Black)
        self.lbl_value.setFont(f)
        self.lbl_value.setStyleSheet(f"color: {self._accent.name()};")

        self.lbl_secondary = QLabel("")
        self.lbl_secondary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_secondary.setStyleSheet(
            "color: rgba(255,255,255,120); font-family: 'Inter', 'Segoe UI'; "
            "font-size: 10px; font-weight: 600;"
        )

        left = QVBoxLayout(); left.setContentsMargins(0, 0, 0, 0); left.setSpacing(0)
        name_row = QHBoxLayout(); name_row.setContentsMargins(0, 0, 0, 0); name_row.setSpacing(6)
        name_row.addWidget(self.lbl_icon); name_row.addWidget(self.lbl_name); name_row.addStretch(1)
        left.addLayout(name_row); left.addWidget(self.lbl_secondary)

        right = QVBoxLayout(); right.setContentsMargins(0, 0, 0, 0); right.setSpacing(0)
        right.addStretch(1); right.addWidget(self.lbl_value)

        top.addLayout(left, 1); top.addLayout(right, 0)
        root.addLayout(top)

        self.sparkline = Sparkline(color=self._accent.name())
        self.sparkline.setVisible(show_sparkline)
        root.addWidget(self.sparkline)

    def set_accent(self, color: str) -> None:
        self._accent = QColor(color)
        self.sparkline.set_color(color)
        self._refresh_value_style()
        if hasattr(self, "_hover_glow"):
            self._hover_glow.set_accent(color)
        self.update()

    def set_sparkline_visible(self, visible: bool) -> None:
        self.sparkline.setVisible(visible)

    def set_thresholds(self, warn: float, crit: float) -> None:
        self._warn = float(warn); self._crit = float(crit)
        self._refresh_value_style(); self.update()

    def set_value(self, percent: float, text: str, secondary: str = "",
                  critical_override: bool = False) -> None:
        try:
            self._value_target = max(0.0, min(100.0, float(percent)))
        except (TypeError, ValueError):
            self._value_target = 0.0
        self._value_text = text
        self._secondary_text = secondary
        self._critical = critical_override or (self._value_target >= self._crit)
        self.lbl_value.setText(text)
        self.lbl_secondary.setText(secondary)
        self._refresh_value_style()
        self.sparkline.push(self._value_target)
        self._anim.stop()
        self._anim.setStartValue(self._value_anim)
        self._anim.setEndValue(self._value_target)
        self._anim.start()

    def _refresh_value_style(self) -> None:
        color = _color_for_load(self._value_target, self._accent, self._warn, self._crit)
        if self._critical:
            color = QColor("#ff5c5c")
        self.lbl_value.setStyleSheet(f"color: {color.name()};")

    def paintEvent(self, _event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        radius = 12.0
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor(30, 30, 40, 235))
        bg.setColorAt(1.0, QColor(18, 18, 26, 235))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(bg))
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        hi = QPen(QColor(255, 255, 255, 22)); hi.setWidthF(1.0)
        p.setPen(hi); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)

        track_h = 4.0
        spark_h = 22.0 if self.sparkline.isVisible() else 0.0
        track_y = h - spark_h - 10
        track_rect = QRectF(14, track_y, w - 28, track_h)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(track_rect, track_h/2, track_h/2)

        filled_w = (self._value_anim / 100.0) * (w - 28)
        if filled_w > 1.0:
            fg = _color_for_load(self._value_anim, self._accent, self._warn, self._crit)
            if self._critical:
                fg = QColor("#ff5c5c")
            grad = QLinearGradient(14, 0, 14 + filled_w, 0)
            c1 = QColor(fg); c1.setAlpha(230)
            c2 = QColor(fg); c2.setAlpha(255)
            grad.setColorAt(0.0, c1); grad.setColorAt(1.0, c2)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(14, track_y, filled_w, track_h), track_h/2, track_h/2)
            dot_r = 5.0
            dot_grad = QRadialGradient(14 + filled_w, track_y + track_h/2, dot_r*2)
            g_in = QColor(fg); g_in.setAlpha(200)
            g_out = QColor(fg); g_out.setAlpha(0)
            dot_grad.setColorAt(0.0, g_in); dot_grad.setColorAt(1.0, g_out)
            p.setBrush(QBrush(dot_grad))
            p.drawEllipse(QPointF(14 + filled_w, track_y + track_h/2), dot_r*2, dot_r*2)


class CircularGauge(QWidget):
    """Круговая индикация температуры/нагрузки GPU с центральной подписью и
    мягким glow под дугу. Цвет дуги считается по :func:`_color_for_temp`."""

    def __init__(self, accent: str = "#00ff99",
                 warn: int = 75, crit: int = 85, parent=None):
        super().__init__(parent)
        self._accent = QColor(accent)
        self._warn = warn; self._crit = crit
        self._temp = 0; self._util = 0
        self._anim_util = 0.0; self._available = False
        self.setFixedSize(96, 96)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._anim = QPropertyAnimation(self, b"animatedUtil")
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_animated_util(self) -> float: return self._anim_util
    def set_animated_util(self, v: float) -> None:
        self._anim_util = max(0.0, min(100.0, float(v))); self.update()
    animatedUtil = pyqtProperty(float, fget=get_animated_util, fset=set_animated_util)

    def set_accent(self, color: str) -> None:
        self._accent = QColor(color); self.update()

    def set_thresholds(self, warn: int, crit: int) -> None:
        self._warn = int(warn); self._crit = int(crit); self.update()

    def set_values(self, temp, util) -> None:
        if temp is None or util is None:
            self._available = False; self.update(); return
        self._available = True
        self._temp = int(temp)
        new_util = int(util)
        self._anim.stop()
        self._anim.setStartValue(self._anim_util)
        self._anim.setEndValue(float(new_util))
        self._anim.start()
        self._util = new_util

    def paintEvent(self, _event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w/2, h/2
        radius = min(w, h)/2 - 6

        track_pen = QPen(QColor(255,255,255,32)); track_pen.setWidth(6)
        p.setPen(track_pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), radius, radius)

        color = _color_for_temp(self._temp if self._available else 40, self._accent,
                                 self._warn, self._crit)

        glow = QRadialGradient(cx, cy, radius + 8)
        g1 = QColor(color); g1.setAlpha(0)
        g2 = QColor(color); g2.setAlpha(60)
        g3 = QColor(color); g3.setAlpha(0)
        glow.setColorAt(0.55, g1); glow.setColorAt(0.75, g2); glow.setColorAt(1.0, g3)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(cx, cy), radius + 8, radius + 8)

        rect = QRectF(cx - radius, cy - radius, radius*2, radius*2)
        arc_pen = QPen(color); arc_pen.setWidth(6)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(arc_pen); p.setBrush(Qt.BrushStyle.NoBrush)
        start_angle = 90*16
        span = -int((self._anim_util/100.0) * 360*16) if self._available else 0
        p.drawArc(rect, start_angle, span)

        p.setPen(QColor(255, 255, 255, 240))
        fb = QFont(UI_FONT_FAMILY, 18); fb.setWeight(QFont.Weight.Black); p.setFont(fb)
        txt = f"{self._temp}°" if self._available else "N/A"
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)

        p.setPen(QColor(255, 255, 255, 130))
        fl = QFont(UI_FONT_FAMILY, 8); fl.setWeight(QFont.Weight.ExtraBold)
        fl.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        p.setFont(fl)
        p.drawText(QRectF(rect.left(), rect.bottom() - 26, rect.width(), 14),
                   Qt.AlignmentFlag.AlignCenter, "GPU")


# ==========================================================
#                   ВИДЖЕТЫ: WOW-ЭФФЕКТЫ
# ==========================================================
class ParticleField(QWidget):
    """Лёгкий слой со светящимися частицами-искрами."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._accent = QColor("#00ff99")
        self._enabled = True
        self._particles: list[dict] = []
        self._phase = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(55)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if self._enabled:
            if not self._timer.isActive():
                self._timer.start(55)
        else:
            self._timer.stop()
        self.update()

    def set_accent(self, color: str) -> None:
        self._accent = QColor(color); self.update()

    def _ensure_particles(self) -> None:
        target = 18 if self.width() > 200 else 10
        while len(self._particles) < target:
            self._particles.append(self._spawn())
        self._particles = self._particles[:target]

    def _spawn(self) -> dict:
        return {
            "x": random.uniform(0, max(1, self.width())),
            "y": random.uniform(0, max(1, self.height())),
            "vx": random.uniform(-0.18, 0.18),
            "vy": random.uniform(-0.24, -0.05),
            "r": random.uniform(1.2, 2.4),
            "phase": random.uniform(0, 2*math.pi),
        }

    def _tick(self) -> None:
        if not self._enabled:
            return
        self._phase += 0.04
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["phase"] += 0.07
            if p["y"] < -4 or p["x"] < -4 or p["x"] > self.width() + 4:
                p.update(self._spawn())
                p["y"] = self.height() + random.uniform(0, 12)
        self.update()

    def resizeEvent(self, event):
        self._ensure_particles()
        super().resizeEvent(event)

    def paintEvent(self, _event):
        if not self._enabled or not self._particles:
            return
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for particle in self._particles:
            a = 120 + int(80 * math.sin(particle["phase"]))
            a = max(30, min(220, a))
            r = particle["r"]
            grad = QRadialGradient(particle["x"], particle["y"], r * 4)
            c1 = QColor(self._accent); c1.setAlpha(a)
            c2 = QColor(self._accent); c2.setAlpha(0)
            grad.setColorAt(0.0, c1); grad.setColorAt(1.0, c2)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(grad))
            p.drawEllipse(QPointF(particle["x"], particle["y"]), r*4, r*4)
            p.setBrush(QColor(255, 255, 255, min(255, a + 50)))
            p.drawEllipse(QPointF(particle["x"], particle["y"]), r*0.7, r*0.7)


class MusicVisualizer(QWidget):
    """14-bar псевдо-спектр (косметический, на синусоидах)."""

    def __init__(self, accent: str = "#00ff99", parent=None):
        super().__init__(parent)
        self._accent = QColor(accent)
        self._bars = 14
        self._values = [0.0] * self._bars
        self._target = [0.0] * self._bars
        self._phase = 0.0
        self._active = True
        self.setMinimumHeight(26); self.setMaximumHeight(26)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def set_accent(self, color: str) -> None:
        self._accent = QColor(color); self.update()

    def set_active(self, active: bool) -> None:
        self._active = bool(active)

    def _tick(self) -> None:
        self._phase += 0.18
        for i in range(self._bars):
            if self._active:
                base = 0.35 + 0.35 * math.sin(self._phase + i*0.7)
                highs = 0.25 * math.sin(self._phase*1.7 + i*1.3)
                noise = random.uniform(-0.08, 0.08)
                self._target[i] = max(0.02, min(1.0, base + highs + noise))
            else:
                self._target[i] = 0.02
            # smooth
            self._values[i] += (self._target[i] - self._values[i]) * 0.35
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        gap = 3.0
        bw = max(2.0, (w - gap*(self._bars - 1)) / self._bars)
        for i, v in enumerate(self._values):
            bh = max(2.0, v * h)
            x = i * (bw + gap)
            y = h - bh
            grad = QLinearGradient(0, y, 0, h)
            c1 = QColor(self._accent); c1.setAlpha(230)
            c2 = QColor(self._accent); c2.setAlpha(90)
            grad.setColorAt(0.0, c1); grad.setColorAt(1.0, c2)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(x, y, bw, bh), bw/2, bw/2)


class ClockWidget(QLabel):
    """HH:MM:SS clock, optional seconds, uses accent colour."""

    def __init__(self, accent: str = "#00ff99", show_seconds: bool = True, parent=None):
        super().__init__(parent)
        self._accent = accent
        self._seconds = show_seconds
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont(MONO_FONT_FAMILY, 14); f.setWeight(QFont.Weight.Black)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        self.setFont(f)
        self._apply_style()
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"color: {self._accent}; background: rgba(255,255,255,12); "
            "border: 1px solid rgba(255,255,255,24); border-radius: 10px; "
            "padding: 6px 14px; letter-spacing: 2px;"
        )

    def _tick(self) -> None:
        fmt = "%H:%M:%S" if self._seconds else "%H:%M"
        self.setText(time.strftime(fmt))

    def set_accent(self, color: str) -> None:
        self._accent = color
        self._apply_style()

    def set_show_seconds(self, flag: bool) -> None:
        self._seconds = bool(flag)
        self._tick()


class PeakValuesWidget(QLabel):
    """Compact line: max CPU / RAM / GPU / ping seen this session."""

    def __init__(self, accent: str = "#00ff99", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._cpu = 0.0; self._ram = 0.0; self._gpu_t = 0.0; self._ping = 0.0
        f = QFont(MONO_FONT_FAMILY, 9); f.setWeight(QFont.Weight.DemiBold)
        self.setFont(f)
        self._apply_style()
        self._refresh()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"color: rgba(255,255,255,200); background: rgba(255,255,255,10); "
            f"border: 1px solid {self._accent}; border-radius: 8px; padding: 4px 10px;"
        )

    def set_accent(self, color: str) -> None:
        self._accent = color
        self._apply_style()

    def push(self, cpu: float = None, ram: float = None, gpu_t: float = None, ping_ms: float = None) -> None:
        if cpu is not None and cpu > self._cpu: self._cpu = cpu
        if ram is not None and ram > self._ram: self._ram = ram
        if gpu_t is not None and gpu_t > self._gpu_t: self._gpu_t = gpu_t
        if ping_ms is not None and ping_ms > self._ping: self._ping = ping_ms
        self._refresh()

    def reset_peak(self) -> None:
        self._cpu = 0.0; self._ram = 0.0; self._gpu_t = 0.0; self._ping = 0.0
        self._refresh()

    def _refresh(self) -> None:
        self.setText(
            f"▲ PEAK  CPU {int(self._cpu)}%   RAM {int(self._ram)}%   "
            f"GPU {int(self._gpu_t)}°   PING {int(self._ping)}ms"
        )


# ==========================================================
#                   SETTINGS-СПЕЦ. ВИДЖЕТЫ
# ==========================================================
class KeybindRecorder(QLineEdit):
    """QLineEdit, который ловит реальные нажатия клавиш."""

    hotkey_changed = pyqtSignal(str)

    def __init__(self, initial: str, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value = initial
        self._recording = False
        self._update_display()
        self.setMinimumHeight(34)

    def _update_display(self) -> None:
        if self._recording:
            self.setText("…нажмите сочетание…")
        else:
            self.setText(self._value.upper() if self._value else "—")

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._recording = True
        self._update_display()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._recording = False
        self._update_display()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._recording = True
        self._update_display()

    def keyPressEvent(self, event):
        if not self._recording:
            super().keyPressEvent(event); return
        key = event.key()
        if key in (Qt.Key.Key_Escape, Qt.Key.Key_Tab):
            self._recording = False; self._update_display(); self.clearFocus(); return
        if key in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return  # ждём не-модификатор

        mods = event.modifiers()
        parts = []
        if mods & Qt.KeyboardModifier.ControlModifier: parts.append("ctrl")
        if mods & Qt.KeyboardModifier.AltModifier: parts.append("alt")
        if mods & Qt.KeyboardModifier.ShiftModifier: parts.append("shift")
        if mods & Qt.KeyboardModifier.MetaModifier: parts.append("win")

        key_name = QKeySequence(key).toString().lower()
        if not key_name:
            return
        parts.append(key_name)

        self._value = "+".join(parts)
        self._recording = False
        self._update_display()
        self.hotkey_changed.emit(self._value)
        self.clearFocus()


class ThresholdEditor(QWidget):
    """Пара слайдеров warn/crit с живыми value-label'ами."""

    changed = pyqtSignal(int, int)

    def __init__(self, title: str, warn: int, crit: int,
                 vmin: int = 30, vmax: int = 100, unit: str = "%", parent=None):
        super().__init__(parent)
        self._unit = unit
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        title_lbl = QLabel(title); title_lbl.setObjectName("threshold_section")
        title_lbl.setStyleSheet(
            "QLabel { color: #ffffff; font-family: 'Inter', 'Segoe UI'; font-size: 12px; "
            "font-weight: 900; letter-spacing: 0.8px; background: transparent; }"
        )
        root.addWidget(title_lbl)

        row_warn = self._row("⚠  Warn", warn, vmin, vmax, "#ffcc66")
        self.slider_warn = row_warn[0]; self.lbl_warn = row_warn[1]
        root.addLayout(row_warn[2])

        row_crit = self._row("🔥  Critical", crit, vmin, vmax, "#ff5c5c")
        self.slider_crit = row_crit[0]; self.lbl_crit = row_crit[1]
        root.addLayout(row_crit[2])

        self.slider_warn.valueChanged.connect(self._emit)
        self.slider_crit.valueChanged.connect(self._emit)

    def _row(self, label: str, value: int, vmin: int, vmax: int, color: str):
        row = QHBoxLayout(); row.setSpacing(8)
        lbl = QLabel(label); lbl.setFixedWidth(90)
        lbl.setStyleSheet(f"color: {color}; font-family: 'Inter', 'Segoe UI'; font-size: 11px; font-weight: 900; background: transparent;")
        s = QSlider(Qt.Orientation.Horizontal); s.setRange(vmin, vmax); s.setValue(int(value))
        val = QLabel(f"{value}{self._unit}"); val.setFixedWidth(52)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val.setStyleSheet("color: #ffffff; font-family: 'Inter', 'Segoe UI'; font-weight: 900; font-size: 12px; background: transparent;")
        s.valueChanged.connect(lambda v, lb=val: lb.setText(f"{v}{self._unit}"))
        row.addWidget(lbl); row.addWidget(s, 1); row.addWidget(val)
        return s, val, row

    def _emit(self, _val=None) -> None:
        w = self.slider_warn.value(); c = self.slider_crit.value()
        if w > c:
            c = w; self.slider_crit.blockSignals(True)
            self.slider_crit.setValue(c); self.slider_crit.blockSignals(False)
            self.lbl_crit.setText(f"{c}{self._unit}")
        self.changed.emit(w, c)


class PresetCard(QPushButton):
    """Карточка темы-пресета с свотчем цвета."""

    def __init__(self, name: str, preset: dict, parent=None):
        super().__init__(parent)
        self._name = name; self._preset = preset
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setMinimumHeight(76); self.setMinimumWidth(150)
        self._refresh_style()
        # Glow-lift по цвету пресета, чтобы подсветка совпадала с акцентом карточки.
        self._hover_glow = HoverGlow(
            self, accent=str(preset.get("accent_color", "#00ff99")),
            base_blur=0.0, hover_blur=24.0, duration_ms=200,
        )

    def _refresh_style(self) -> None:
        accent = self._preset.get("accent_color", "#00ff99")
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #14141c;
                color: #ffffff;
                border: 1px solid rgba(255,255,255,18);
                border-radius: 12px;
                text-align: left;
                padding: 10px 12px 10px 44px;
                font-family: 'Inter', 'Segoe UI'; font-weight: 900; font-size: 12px;
                letter-spacing: 0.6px;
            }}
            QPushButton:hover {{
                border: 1px solid {accent};
                background: rgba(20,20,28,200);
            }}
            QPushButton:checked {{
                border: 2px solid {accent};
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(20,20,28,240), stop:1 rgba(20,20,28,200));
            }}
            """
        )
        self.setText(f"  {self._name}")

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # swatch circle (top-left)
        accent = QColor(self._preset.get("accent_color", "#00ff99"))
        glow = QRadialGradient(22, self.height()/2, 22)
        g1 = QColor(accent); g1.setAlpha(180)
        g2 = QColor(accent); g2.setAlpha(0)
        glow.setColorAt(0.0, g1); glow.setColorAt(1.0, g2)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(22, self.height()/2), 20, 20)
        p.setBrush(accent)
        p.drawEllipse(QPointF(22, self.height()/2), 9, 9)
        # subtitle
        p.setPen(QColor(255,255,255,130))
        sub_font = QFont(UI_FONT_FAMILY, 8); sub_font.setWeight(QFont.Weight.DemiBold)
        p.setFont(sub_font)
        p.drawText(QRectF(44, self.height()/2 + 4, self.width()-48, 18),
                   Qt.AlignmentFlag.AlignLeft,
                   f"opacity {self._preset.get('opacity', 235)}  ·  {accent.name()}")


# ==========================================================
#                 ЖИВОЙ ПРЕВЬЮ-ОВЕРЛЕЙ
# ==========================================================
class LivePreview(QFrame):
    """Мини-копия оверлея внутри окна настроек, реактивная к config."""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.setObjectName("live_preview")
        self.setMinimumWidth(260); self.setMinimumHeight(300)
        self.setFrameStyle(QFrame.Shape.NoFrame)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(8)

        header = QHBoxLayout(); header.setSpacing(6)
        self.dot = StatusDot()
        self.lbl_title = QLabel("PHANTOM · LIVE")
        tf = QFont(UI_FONT_FAMILY, 10); tf.setWeight(QFont.Weight.Black)
        tf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
        self.lbl_title.setFont(tf)
        self.lbl_title.setStyleSheet("color: #ffffff;")
        header.addWidget(self.dot); header.addWidget(self.lbl_title); header.addStretch(1)
        root.addLayout(header)

        body = QHBoxLayout(); body.setSpacing(10)
        self.gauge = CircularGauge(accent=config["accent_color"],
                                   warn=config.get("gpu_warn", 75),
                                   crit=config.get("gpu_crit", 85))
        self.gauge.setFixedSize(74, 74)
        body.addWidget(self.gauge, 0, Qt.AlignmentFlag.AlignTop)

        cards = QVBoxLayout(); cards.setSpacing(6)
        self.card_cpu = MetricCard("🧠", "CPU", accent=config["accent_color"],
                                   show_sparkline=config.get("show_sparklines", True),
                                   warn=config.get("cpu_warn", 80), crit=config.get("cpu_crit", 95))
        self.card_ram = MetricCard("💾", "RAM", accent=config["accent_color"],
                                   show_sparkline=config.get("show_sparklines", True),
                                   warn=config.get("ram_warn", 80), crit=config.get("ram_crit", 92))
        self.card_cpu.setMinimumHeight(56); self.card_ram.setMinimumHeight(56)
        cards.addWidget(self.card_cpu); cards.addWidget(self.card_ram)
        body.addLayout(cards, 1)
        root.addLayout(body)

        self.visualizer = MusicVisualizer(accent=config["accent_color"])
        self.visualizer.setFixedHeight(22)
        root.addWidget(self.visualizer)

        # fill data
        self._seed_timer = QTimer(self)
        self._seed_timer.timeout.connect(self._seed_data)
        self._seed_timer.start(420)
        self._seed_data()
        self.apply_config(config)

    def _seed_data(self) -> None:
        cpu = 35 + random.random()*35
        ram = 48 + random.random()*20
        gpu_t = 58 + int(random.random()*18)
        gpu_u = 35 + int(random.random()*55)
        self.card_cpu.set_value(cpu, f"{cpu:.0f}%", "2.45 GHz")
        self.card_ram.set_value(ram, f"{ram:.0f}%", "8.1 / 16 GB")
        self.gauge.set_values(gpu_t, gpu_u)
        if gpu_t > self.config.get("gpu_crit", 85):
            self.dot.set_color("#ff5c5c")
        elif gpu_t > self.config.get("gpu_warn", 75):
            self.dot.set_color("#ffcc66")
        else:
            self.dot.set_color(self.config["accent_color"])

    def apply_config(self, cfg: dict) -> None:
        self.config = cfg
        accent = cfg["accent_color"]
        self.card_cpu.set_accent(accent); self.card_ram.set_accent(accent)
        self.card_cpu.set_thresholds(cfg.get("cpu_warn", 80), cfg.get("cpu_crit", 95))
        self.card_ram.set_thresholds(cfg.get("ram_warn", 80), cfg.get("ram_crit", 92))
        self.card_cpu.set_sparkline_visible(cfg.get("show_sparklines", True))
        self.card_ram.set_sparkline_visible(cfg.get("show_sparklines", True))
        self.gauge.set_accent(accent)
        self.gauge.set_thresholds(cfg.get("gpu_warn", 75), cfg.get("gpu_crit", 85))
        self.visualizer.set_accent(accent)
        self.visualizer.setVisible(cfg.get("show_visualizer", True))
        self.card_cpu.setVisible(cfg.get("show_cpu", True))
        self.card_ram.setVisible(cfg.get("show_ram", True))
        self.gauge.setVisible(cfg.get("show_gpu", True))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        radius = 14.0
        path = QPainterPath(); path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        p.setClipPath(path)

        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor(22, 22, 32, 255))
        bg.setColorAt(1.0, QColor(9, 9, 14, 255))
        p.fillRect(self.rect(), QBrush(bg))

        accent = QColor(self.config["accent_color"])
        accent_glow = QRadialGradient(0, 0, max(w, h))
        c1 = QColor(accent); c1.setAlpha(90)
        c2 = QColor(accent); c2.setAlpha(0)
        accent_glow.setColorAt(0.0, c1); accent_glow.setColorAt(0.9, c2)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(accent_glow))
        p.drawRect(self.rect())

        cool = QColor("#5a7dff")
        cool_glow = QRadialGradient(float(w), float(h), max(w, h)*0.9)
        cc1 = QColor(cool); cc1.setAlpha(60)
        cc2 = QColor(cool); cc2.setAlpha(0)
        cool_glow.setColorAt(0.0, cc1); cool_glow.setColorAt(1.0, cc2)
        p.setBrush(QBrush(cool_glow))
        p.drawRect(self.rect())

        # animated border (simplified for preview)
        pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 110), 1.5)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w-1, h-1), radius, radius)


# ==========================================================
#                     ГЛАВНЫЕ ПАНЕЛИ
# ==========================================================
class GlassPanel(QWidget):
    """Премиум-фон: градиент + glow + шум + опциональный вращающийся conic-бордер."""

    # Общий для всех инстансов тайл шума. Генерируется один раз и тайлится через
    # QBrush — это на порядки дешевле, чем регенерировать per-pixel при каждом
    # ресайзе окна.
    _NOISE_TILE: QPixmap | None = None
    _NOISE_TILE_SIZE: int = 256

    def __init__(self, parent=None):
        super().__init__(parent)
        self._accent = QColor("#00ff99")
        self._bg_pixmap: QPixmap | None = None
        self._unlocked = False
        self._border_angle = 0.0
        self._animated_border = True
        self._critical = False
        self._corner_radius = 20.0
        self._border_style = "solid"  # solid | dashed | neon | none

        self._border_timer = QTimer(self)
        self._border_timer.timeout.connect(self._spin_border)
        self._border_timer.start(90)

    def set_corner_radius(self, radius: int) -> None:
        self._corner_radius = float(max(2, min(80, int(radius))))
        self.update()

    def set_border_style(self, style: str) -> None:
        self._border_style = style if style in ("solid", "dashed", "neon", "none") else "solid"
        self.update()

    def set_accent(self, color: str) -> None:
        self._accent = QColor(color); self.update()

    def set_background_image(self, path: str) -> None:
        if path and os.path.exists(path):
            self._bg_pixmap = QPixmap(path)
        else:
            self._bg_pixmap = None
        self.update()

    def set_unlocked(self, unlocked: bool) -> None:
        self._unlocked = bool(unlocked); self.update()

    def set_animated_border(self, enabled: bool) -> None:
        self._animated_border = bool(enabled)
        if enabled:
            if not self._border_timer.isActive():
                self._border_timer.start(90)
        else:
            self._border_timer.stop()
        self.update()

    def set_critical(self, critical: bool) -> None:
        self._critical = bool(critical); self.update()

    def _spin_border(self) -> None:
        self._border_angle = (self._border_angle + 2.2) % 360
        if self._animated_border:
            self.update()

    @classmethod
    def _get_noise_tile(cls) -> QPixmap:
        """Лениво собираем один бесшовный тайл шума и переиспользуем его повсюду."""
        if cls._NOISE_TILE is not None and not cls._NOISE_TILE.isNull():
            return cls._NOISE_TILE
        size = cls._NOISE_TILE_SIZE
        img = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        rnd = random.Random(42)
        # Плотность подобрана так, чтобы итоговая картинка выглядела идентично
        # старому варианту (~1 пиксель на каждые 28 пикселей площади).
        for _ in range(size * size // 28):
            x = rnd.randint(0, size - 1); y = rnd.randint(0, size - 1)
            a = rnd.randint(6, 18)
            img.setPixelColor(x, y, QColor(255, 255, 255, a))
        cls._NOISE_TILE = QPixmap.fromImage(img)
        return cls._NOISE_TILE

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        radius = float(self._corner_radius)
        path = QPainterPath(); path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        p.setClipPath(path)

        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor(22, 22, 32, 245))
        bg.setColorAt(1.0, QColor(9, 9, 14, 245))
        p.fillRect(self.rect(), QBrush(bg))

        if self._bg_pixmap is not None and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.setOpacity(0.35); p.drawPixmap(0, 0, scaled); p.setOpacity(1.0)

        accent_glow = QRadialGradient(0, 0, max(w, h))
        c1 = QColor(self._accent); c1.setAlpha(80)
        c2 = QColor(self._accent); c2.setAlpha(0)
        accent_glow.setColorAt(0.0, c1); accent_glow.setColorAt(0.9, c2)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(accent_glow))
        p.drawRect(self.rect())

        cool = QColor("#5a7dff")
        cool_glow = QRadialGradient(float(w), float(h), max(w, h)*0.9)
        cc1 = QColor(cool); cc1.setAlpha(60)
        cc2 = QColor(cool); cc2.setAlpha(0)
        cool_glow.setColorAt(0.0, cc1); cool_glow.setColorAt(1.0, cc2)
        p.setBrush(QBrush(cool_glow))
        p.drawRect(self.rect())

        if self._critical:
            red = QColor("#ff5c5c")
            r_glow = QRadialGradient(w/2, h/2, max(w, h))
            r1 = QColor(red); r1.setAlpha(70)
            r2 = QColor(red); r2.setAlpha(0)
            r_glow.setColorAt(0.0, r1); r_glow.setColorAt(1.0, r2)
            p.setBrush(QBrush(r_glow)); p.drawRect(self.rect())

        # Тайлим один кэшированный пиксмап шума через QBrush —
        # O(1) на отрисовку независимо от размера окна.
        p.fillRect(self.rect(), QBrush(self._get_noise_tile()))

        p.setPen(QPen(QColor(255, 255, 255, 24), 1))
        p.drawLine(int(radius/2), 1, int(w - radius/2), 1)

        # ---- Border ----
        if self._border_style == "none" and not self._animated_border:
            return
        if self._animated_border:
            cg = QConicalGradient(w/2, h/2, self._border_angle)
            a = QColor(self._accent)
            transparent = QColor(self._accent); transparent.setAlpha(0)
            cg.setColorAt(0.00, transparent)
            cg.setColorAt(0.20, a)
            cg.setColorAt(0.40, transparent)
            cg.setColorAt(0.60, a)
            cg.setColorAt(0.80, transparent)
            cg.setColorAt(1.00, transparent)
            border_pen = QPen(QBrush(cg), 2.0 if not self._unlocked else 2.4)
            if self._unlocked or self._border_style == "dashed":
                border_pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(border_pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(1, 1, w-2, h-2), radius-1, radius-1)
        elif self._border_style == "neon":
            for i, alpha in enumerate((28, 48, 90, 180)):
                c = QColor(self._accent); c.setAlpha(alpha)
                pen = QPen(c); pen.setWidth(5 - i)
                p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(QRectF(0.5 + i*0.4, 0.5 + i*0.4,
                                         w - 1 - i*0.8, h - 1 - i*0.8),
                                  max(radius - i*0.5, 1), max(radius - i*0.5, 1))
        else:
            border = QColor(self._accent) if (self._unlocked or self._border_style == "dashed") else QColor(255, 255, 255, 36)
            pen = QPen(border); pen.setWidth(2 if self._unlocked or self._border_style == "dashed" else 1)
            if self._unlocked or self._border_style == "dashed":
                pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(0.5, 0.5, w-1, h-1), radius, radius)


# ==========================================================
#                   ДИАЛОГ НАСТРОЕК
# ==========================================================
class ModernSettings(QDialog):
    """Phantom Control Center: sidebar-навигация + stacked страницы
    («Основные», «Дизайн», «Раскладка», «Пресеты», «Пороги», «Игры»,
    «О программе») с live preview. Все изменения коммитятся через
    :meth:`_commit`, мгновенно пробрасываются в оверлей и автосохраняются
    в ``phantom_config.json``."""

    def __init__(self, current_config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Phantom Control Center")
        self.setMinimumSize(1060, 620)
        self.config = current_config
        self.parent_overlay = parent
        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))
        self._build_ui()
        self._apply_styles()

    # ----- structure -----
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # sidebar
        side = QWidget(); side.setObjectName("side"); side.setFixedWidth(210)
        side_l = QVBoxLayout(side)
        side_l.setContentsMargins(18, 22, 14, 22); side_l.setSpacing(12)

        brand = QLabel("⚙  PHANTOM"); brand.setObjectName("brand")
        subtitle = QLabel(f"v{APP_VERSION}"); subtitle.setObjectName("brand_version")
        side_l.addWidget(brand); side_l.addWidget(subtitle); side_l.addSpacing(10)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(tr("search_ph"))
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setObjectName("side_search")
        self.search_box.textChanged.connect(self._filter_nav)
        side_l.addWidget(self.search_box)

        self.nav = QListWidget(); self.nav.setObjectName("nav")
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        self._nav_keys = ["general", "design", "layout", "modules", "thresholds", "presets", "games", "about"]
        self._nav_icons = {
            "general": "⚙", "design": "🎨", "layout": "🧭", "modules": "🧩",
            "thresholds": "📊", "presets": "🎭", "games": "🎮", "about": "ℹ",
        }
        for key in self._nav_keys:
            QListWidgetItem(f"{self._nav_icons[key]}   {tr('nav.' + key)}", self.nav)
        self.nav.setCurrentRow(0)
        side_l.addWidget(self.nav, 1)

        btn_close = QPushButton("✔  Готово")
        btn_close.setMinimumHeight(38); btn_close.setObjectName("done_btn")
        btn_close.clicked.connect(self.accept)
        side_l.addWidget(btn_close)

        # content stack
        self.stack = QStackedWidget(); self.stack.setObjectName("stack")
        self._build_page_general()
        self._build_page_design()
        self._build_page_layout()
        self._build_page_modules()
        self._build_page_thresholds()
        self._build_page_presets()
        self._build_page_games()
        self._build_page_about()
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)

        # live preview (always on the right)
        preview_holder = QWidget(); preview_holder.setFixedWidth(300)
        preview_holder.setObjectName("preview_holder")
        ph_l = QVBoxLayout(preview_holder)
        ph_l.setContentsMargins(16, 22, 22, 22); ph_l.setSpacing(10)
        ph_title = QLabel("LIVE PREVIEW"); ph_title.setObjectName("live_title")
        ph_l.addWidget(ph_title)
        self.preview = LivePreview(self.config)
        ph_l.addWidget(self.preview, 1)
        ph_tip = QLabel("Изменения применяются мгновенно.\nПресеты — во вкладке «Пресеты»."); ph_tip.setObjectName("live_hint")
        ph_tip.setWordWrap(True)
        ph_l.addWidget(ph_tip)

        root.addWidget(side)
        root.addWidget(self.stack, 1)
        root.addWidget(preview_holder)

    # ----- page scaffolding -----
    def _page_scaffold(self, title: str, subtitle: str = "") -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget(); scroll.setWidget(inner)
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 26, 32, 28); lay.setSpacing(14)

        t = QLabel(title); t.setObjectName("page_title")
        lay.addWidget(t)
        if subtitle:
            s = QLabel(subtitle); s.setWordWrap(True); s.setObjectName("page_subtitle")
            lay.addWidget(s)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,20); border: none;")
        lay.addWidget(sep); lay.addSpacing(4)

        page_root = QVBoxLayout(page); page_root.setContentsMargins(0, 0, 0, 0); page_root.setSpacing(0)
        page_root.addWidget(scroll)
        return page, lay

    # ---------- Page: General ----------
    def _build_page_general(self) -> None:
        page, lay = self._page_scaffold(
            "Общие настройки",
            "Хоткеи, интервал обновления, системное поведение и перенос конфигурации."
        )
        form = QFormLayout(); form.setSpacing(14)

        self.rec_toggle = KeybindRecorder(self.config.get("hotkey_toggle", "ctrl+shift+p"))
        self.rec_toggle.hotkey_changed.connect(lambda h: self._commit("hotkey_toggle", h, rehook=True))
        form.addRow("Хоткей: показать/скрыть:", self.rec_toggle)

        self.rec_settings = KeybindRecorder(self.config.get("hotkey_settings", "ctrl+shift+o"))
        self.rec_settings.hotkey_changed.connect(lambda h: self._commit("hotkey_settings", h, rehook=True))
        form.addRow("Хоткей: открыть настройки:", self.rec_settings)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(250, 5000); self.spin_interval.setSingleStep(100)
        self.spin_interval.setSuffix("  мс")
        self.spin_interval.setValue(int(self.config.get("update_interval_ms", 1000)))
        self.spin_interval.valueChanged.connect(lambda v: self._commit("update_interval_ms", int(v), apply_interval=True))
        form.addRow("Интервал обновления:", self.spin_interval)

        self.combo_corner = QComboBox()
        for code, label in [
            ("none", "— не прилипать"),
            ("tl", "↖ Верхний левый"),
            ("tr", "↗ Верхний правый"),
            ("bl", "↙ Нижний левый"),
            ("br", "↘ Нижний правый"),
        ]:
            self.combo_corner.addItem(label, code)
        idx = self.combo_corner.findData(self.config.get("corner_snap", "none"))
        if idx >= 0: self.combo_corner.setCurrentIndex(idx)
        self.combo_corner.currentIndexChanged.connect(
            lambda _i: self._commit("corner_snap", self.combo_corner.currentData(), apply_geometry=True)
        )
        form.addRow("Прилипание к углу:", self.combo_corner)

        self.spin_margin = QSpinBox()
        self.spin_margin.setRange(0, 200); self.spin_margin.setSuffix("  px")
        self.spin_margin.setValue(int(self.config.get("corner_margin", 24)))
        self.spin_margin.valueChanged.connect(lambda v: self._commit("corner_margin", int(v), apply_geometry=True))
        form.addRow("Отступ от края:", self.spin_margin)

        self.cb_smart = QCheckBox("Показывать только в играх (Smart Focus)")
        self.cb_smart.setChecked(bool(self.config.get("smart_hide", False)))
        self.cb_smart.stateChanged.connect(lambda s: self._commit("smart_hide", bool(s)))
        form.addRow("Поведение:", self.cb_smart)

        self.cb_voice = QCheckBox("Голос при перегреве GPU")
        self.cb_voice.setChecked(bool(self.config.get("enable_voice", True)))
        self.cb_voice.stateChanged.connect(lambda s: self._commit("enable_voice", bool(s)))
        form.addRow("Звук:", self.cb_voice)

        self.cb_taskbar = QCheckBox(tr("g.taskbar"))
        self.cb_taskbar.setChecked(bool(self.config.get("show_in_taskbar", False)))
        self.cb_taskbar.stateChanged.connect(lambda s: self._commit("show_in_taskbar", bool(s), rewindow=True))
        form.addRow(tr("g.system"), self.cb_taskbar)

        self.cb_on_top = QCheckBox(tr("g.always_on_top"))
        self.cb_on_top.setChecked(bool(self.config.get("always_on_top", True)))
        self.cb_on_top.stateChanged.connect(lambda s: self._commit("always_on_top", bool(s), rewindow=True))
        form.addRow("", self.cb_on_top)

        self.cb_click_through = QCheckBox(tr("g.click_through"))
        self.cb_click_through.setChecked(bool(self.config.get("click_through", False)))
        self.cb_click_through.stateChanged.connect(lambda s: self._commit("click_through", bool(s), rewindow=True))
        form.addRow("", self.cb_click_through)

        self.cb_drag_lock = QCheckBox(tr("g.drag_lock"))
        self.cb_drag_lock.setChecked(bool(self.config.get("drag_lock", False)))
        self.cb_drag_lock.stateChanged.connect(lambda s: self._commit("drag_lock", bool(s)))
        form.addRow("", self.cb_drag_lock)

        self.spin_autohide = QSpinBox()
        self.spin_autohide.setRange(0, 300); self.spin_autohide.setSuffix(" s")
        self.spin_autohide.setValue(int(self.config.get("auto_hide_secs", 0)))
        self.spin_autohide.valueChanged.connect(lambda v: self._commit("auto_hide_secs", int(v)))
        form.addRow(tr("g.autohide"), self.spin_autohide)

        self.combo_lang = QComboBox()
        self.combo_lang.addItem("Русский", "ru")
        self.combo_lang.addItem("English", "en")
        idx = self.combo_lang.findData(self.config.get("language", "ru"))
        if idx >= 0: self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentIndexChanged.connect(
            lambda _i: self._commit("language", self.combo_lang.currentData(), relang=True)
        )
        form.addRow(tr("g.language"), self.combo_lang)

        self.input_ping = QLineEdit()
        self.input_ping.setText(str(self.config.get("ping_host", "8.8.8.8")))
        self.input_ping.setPlaceholderText("8.8.8.8")
        self.input_ping.editingFinished.connect(
            lambda: self._commit("ping_host", self.input_ping.text().strip() or "8.8.8.8", apply_interval=True)
        )
        form.addRow(tr("g.ping_host"), self.input_ping)

        lay.addLayout(form); lay.addSpacing(12)

        # import / export / reset
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background: rgba(255,255,255,14);")
        lay.addWidget(sep)
        io_label = QLabel("Конфигурация")
        io_label.setStyleSheet("color: #e6e9f2; font-weight: 800; letter-spacing: 0.6px; margin-top: 4px;")
        lay.addWidget(io_label)

        io_row = QHBoxLayout(); io_row.setSpacing(8)
        btn_export = QPushButton("⬇  Экспорт")
        btn_export.clicked.connect(self._export_config)
        btn_import = QPushButton("⬆  Импорт")
        btn_import.clicked.connect(self._import_config)
        btn_reset = QPushButton("↻  Сбросить к дефолту")
        btn_reset.setObjectName("reset_btn")
        btn_reset.clicked.connect(self._reset_config)
        io_row.addWidget(btn_export); io_row.addWidget(btn_import); io_row.addWidget(btn_reset); io_row.addStretch(1)
        lay.addLayout(io_row)

        lay.addStretch(1)
        self.stack.addWidget(page)

    # ---------- Page: Design ----------
    def _build_page_design(self) -> None:
        page, lay = self._page_scaffold(
            "Дизайн и внешний вид",
            "Акцентный цвет, масштаб шрифта, эффекты и фон."
        )
        form = QFormLayout(); form.setSpacing(16)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(60, 255)
        self.slider_opacity.setValue(int(self.config.get("opacity", 235)))
        self.slider_opacity.valueChanged.connect(lambda v: self._commit("opacity", int(v), save=False, apply_live=True))
        self.slider_opacity.sliderReleased.connect(lambda: save_config(self.config))
        form.addRow("Прозрачность:", self.slider_opacity)

        self.accent_swatch = QPushButton(); self.accent_swatch.setFixedHeight(32)
        self._refresh_accent_swatch()
        self.accent_swatch.clicked.connect(self._pick_accent)
        form.addRow("Акцентный цвет:", self.accent_swatch)

        # quick preset pills
        preset_row = QHBoxLayout(); preset_row.setSpacing(8)
        for name, hex_ in [
            ("Neon Mint", "#00ff99"), ("Ultraviolet", "#a78bfa"),
            ("Cyber Cyan", "#22d3ee"), ("Magma", "#ff7a59"),
            ("Sakura", "#ff6ba8"), ("Gold", "#f5c24c"),
        ]:
            btn = QPushButton(); btn.setFixedSize(34, 22); btn.setToolTip(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: {hex_}; border: 1px solid rgba(255,255,255,50); border-radius: 4px; }}"
                f"QPushButton:hover {{ border: 1px solid rgba(255,255,255,120); }}"
            )
            btn.clicked.connect(lambda _c=False, h=hex_: self._set_accent(h))
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        form.addRow("Быстрый цвет:", preset_row)

        self.spin_font = QDoubleSpinBox()
        self.spin_font.setRange(0.8, 1.4); self.spin_font.setSingleStep(0.05)
        self.spin_font.setValue(float(self.config.get("font_scale", 1.0)))
        self.spin_font.setSuffix("×")
        self.spin_font.valueChanged.connect(lambda v: self._commit("font_scale", float(v)))
        form.addRow("Масштаб шрифта:", self.spin_font)

        self.cb_border = QCheckBox("Вращающийся conic-бордер (WOW)")
        self.cb_border.setChecked(bool(self.config.get("animated_border", True)))
        self.cb_border.stateChanged.connect(lambda s: self._commit("animated_border", bool(s)))
        form.addRow("Эффекты:", self.cb_border)

        self.cb_particles = QCheckBox("Светящиеся частицы")
        self.cb_particles.setChecked(bool(self.config.get("particles", True)))
        self.cb_particles.stateChanged.connect(lambda s: self._commit("particles", bool(s)))
        form.addRow("", self.cb_particles)

        self.cb_compact = QCheckBox(tr("d.compact"))
        self.cb_compact.setChecked(bool(self.config.get("compact_mode", False)))
        self.cb_compact.stateChanged.connect(lambda s: self._commit("compact_mode", bool(s)))
        form.addRow(tr("d.layout"), self.cb_compact)

        self.slider_radius = QSlider(Qt.Orientation.Horizontal)
        self.slider_radius.setRange(2, 80)
        self.slider_radius.setValue(int(self.config.get("corner_radius", 18)))
        self.slider_radius.valueChanged.connect(lambda v: self._commit("corner_radius", int(v)))
        form.addRow(tr("d.corner_radius"), self.slider_radius)

        self.slider_shadow = QSlider(Qt.Orientation.Horizontal)
        self.slider_shadow.setRange(0, 100)
        self.slider_shadow.setValue(int(self.config.get("shadow_intensity", 48)))
        self.slider_shadow.valueChanged.connect(lambda v: self._commit("shadow_intensity", int(v)))
        form.addRow(tr("d.shadow"), self.slider_shadow)

        self.combo_border = QComboBox()
        for code, key in [("solid", "bs.solid"), ("dashed", "bs.dashed"),
                          ("neon", "bs.neon"), ("none", "bs.none")]:
            self.combo_border.addItem(tr(key), code)
        idx = self.combo_border.findData(self.config.get("border_style", "solid"))
        if idx >= 0: self.combo_border.setCurrentIndex(idx)
        self.combo_border.currentIndexChanged.connect(
            lambda _i: self._commit("border_style", self.combo_border.currentData())
        )
        form.addRow(tr("d.border_style"), self.combo_border)

        self.cb_clock_sec = QCheckBox(tr("mod.clock_seconds"))
        self.cb_clock_sec.setChecked(bool(self.config.get("clock_seconds", True)))
        self.cb_clock_sec.stateChanged.connect(lambda s: self._commit("clock_seconds", bool(s)))
        form.addRow("", self.cb_clock_sec)

        # Цветовой режим (пороги vs градиент)
        self.combo_color_mode = QComboBox()
        self.combo_color_mode.addItem("Пороги (warn / crit)", "steps")
        self.combo_color_mode.addItem("Плавный градиент", "gradient")
        cm_idx = self.combo_color_mode.findData(self.config.get("color_mode", "steps"))
        if cm_idx >= 0:
            self.combo_color_mode.setCurrentIndex(cm_idx)
        self.combo_color_mode.currentIndexChanged.connect(
            lambda _i: self._commit("color_mode", str(self.combo_color_mode.currentData()))
        )
        form.addRow("Цвет метрик:", self.combo_color_mode)

        # Микро-анимации hover (лёгкий glow-lift на карточках/кнопках)
        self.cb_hover_anim = QCheckBox("Подсветка при наведении")
        self.cb_hover_anim.setChecked(bool(self.config.get("hover_microanim", True)))
        self.cb_hover_anim.stateChanged.connect(
            lambda s: self._commit("hover_microanim", bool(s))
        )
        form.addRow("", self.cb_hover_anim)

        # bg image
        bg_row = QHBoxLayout()
        btn_bg = QPushButton("🖼  Выбрать фон"); btn_bg.setMinimumHeight(32)
        btn_bg.clicked.connect(self._choose_background)
        btn_clear = QPushButton("✖  Убрать"); btn_clear.setMinimumHeight(32)
        btn_clear.clicked.connect(self._clear_background)
        bg_row.addWidget(btn_bg); bg_row.addWidget(btn_clear)
        form.addRow("Обои окна:", bg_row)

        lay.addLayout(form); lay.addStretch(1)
        self.stack.addWidget(page)

    def _filter_nav(self, text: str) -> None:
        text = (text or "").strip().lower()
        for i in range(self.nav.count()):
            item = self.nav.item(i)
            visible = True if not text else (text in item.text().lower())
            item.setHidden(not visible)

    # ---------- Page: Layout ----------
    def _build_page_layout(self) -> None:
        page, lay = self._page_scaffold(tr("page.layout.title"), tr("page.layout.subtitle"))

        # Module order section
        hdr = QLabel(tr("layout.order"))
        hdr.setStyleSheet("color:#ffffff; font-weight:900; letter-spacing:0.8px; background:transparent;")
        lay.addWidget(hdr)
        hint = QLabel(tr("layout.order_hint"))
        hint.setStyleSheet("color:#a8b2d1; font-size:11px; background:transparent;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self._order_list = QListWidget()
        self._order_list.setFrameShape(QFrame.Shape.NoFrame)
        self._order_list.setMinimumHeight(240)
        self._order_labels = {
            "header": "⚡ Header (title + buttons)",
            "chips": "🔋 Chips (battery / CPU temp / disk)",
            "clock": "🕒 Clock",
            "body": "🧠 Body (GPU gauge + CPU/RAM)",
            "peak": "▲ Peak values",
            "visualizer": "🎛 Visualizer",
            "network": "🌐 Network",
            "music": "🎵 Music",
            "ai": "🤖 AI assistant",
        }
        self._fill_order_list()
        lay.addWidget(self._order_list)

        arrows = QHBoxLayout(); arrows.setSpacing(8)
        btn_up = QPushButton("▲"); btn_up.setFixedWidth(48)
        btn_up.clicked.connect(lambda: self._reorder_module(-1))
        btn_down = QPushButton("▼"); btn_down.setFixedWidth(48)
        btn_down.clicked.connect(lambda: self._reorder_module(+1))
        arrows.addWidget(btn_up); arrows.addWidget(btn_down); arrows.addStretch(1)
        lay.addLayout(arrows)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background: rgba(255,255,255,14);")
        lay.addWidget(sep)

        # Window size section
        hdr2 = QLabel(tr("layout.window"))
        hdr2.setStyleSheet("color:#ffffff; font-weight:900; letter-spacing:0.8px; background:transparent;")
        lay.addWidget(hdr2)

        form = QFormLayout(); form.setSpacing(10)
        self.combo_window_mode = QComboBox()
        for code, key in [("auto", "wm.auto"), ("xs", "wm.xs"), ("s", "wm.s"),
                          ("m", "wm.m"), ("l", "wm.l"), ("xl", "wm.xl"),
                          ("free", "wm.free"), ("fixed", "wm.fixed")]:
            self.combo_window_mode.addItem(tr(key), code)
        idx = self.combo_window_mode.findData(self.config.get("window_mode", "auto"))
        if idx >= 0: self.combo_window_mode.setCurrentIndex(idx)
        self.combo_window_mode.currentIndexChanged.connect(
            lambda _i: self._commit("window_mode", self.combo_window_mode.currentData())
        )
        form.addRow(tr("d.window_mode"), self.combo_window_mode)

        self.spin_fw = QSpinBox(); self.spin_fw.setRange(220, 2400); self.spin_fw.setSuffix(" px")
        self.spin_fw.setValue(int(self.config.get("fixed_width", 440)))
        self.spin_fw.valueChanged.connect(lambda v: self._commit("fixed_width", int(v)))
        form.addRow(tr("d.fixed_w"), self.spin_fw)

        self.spin_fh = QSpinBox(); self.spin_fh.setRange(200, 1800); self.spin_fh.setSuffix(" px")
        self.spin_fh.setValue(int(self.config.get("fixed_height", 420)))
        self.spin_fh.valueChanged.connect(lambda v: self._commit("fixed_height", int(v)))
        form.addRow(tr("d.fixed_h"), self.spin_fh)
        lay.addLayout(form)

        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setStyleSheet("background: rgba(255,255,255,14);")
        lay.addWidget(sep2)

        # Layout profiles section
        hdr3 = QLabel(tr("layout.profiles"))
        hdr3.setStyleSheet("color:#ffffff; font-weight:900; letter-spacing:0.8px; background:transparent;")
        lay.addWidget(hdr3)

        self._profile_rows = {}
        names = self.config.get("profile_names", {}) or {}
        profiles = self.config.get("profiles", {}) or {}
        for slot in ("slot1", "slot2", "slot3"):
            row = QHBoxLayout(); row.setSpacing(8)
            lbl_name = QLabel(names.get(slot, slot.capitalize()))
            lbl_name.setStyleSheet("color:#ffffff; font-weight:800; min-width:120px;")
            status = QLabel("✓" if profiles.get(slot) else tr("layout.profile_empty"))
            status.setStyleSheet("color:#a8b2d1; font-size:11px;")
            btn_save = QPushButton(tr("layout.profile_save"))
            btn_save.clicked.connect(lambda _c=False, s=slot: self._profile_save(s))
            btn_load = QPushButton(tr("layout.profile_load"))
            btn_load.clicked.connect(lambda _c=False, s=slot: self._profile_load(s))
            btn_ren = QPushButton(tr("layout.profile_rename"))
            btn_ren.clicked.connect(lambda _c=False, s=slot: self._profile_rename(s))
            row.addWidget(lbl_name); row.addWidget(status, 1)
            row.addWidget(btn_save); row.addWidget(btn_load); row.addWidget(btn_ren)
            lay.addLayout(row)
            self._profile_rows[slot] = (lbl_name, status)

        lay.addStretch(1)
        self.stack.addWidget(page)

    def _fill_order_list(self) -> None:
        self._order_list.clear()
        order = list(self.config.get("module_order", []))
        for key in self._order_labels.keys():
            if key not in order:
                order.append(key)
        for key in order:
            item = QListWidgetItem(self._order_labels.get(key, key))
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._order_list.addItem(item)

    def _reorder_module(self, delta: int) -> None:
        row = self._order_list.currentRow()
        if row < 0:
            return
        new_row = row + delta
        if new_row < 0 or new_row >= self._order_list.count():
            return
        item = self._order_list.takeItem(row)
        self._order_list.insertItem(new_row, item)
        self._order_list.setCurrentRow(new_row)
        order = [self._order_list.item(i).data(Qt.ItemDataRole.UserRole)
                 for i in range(self._order_list.count())]
        self._commit("module_order", order)

    def _profile_save(self, slot: str) -> None:
        snap = {k: v for k, v in self.config.items() if k not in ("profiles", "profile_names")}
        self.config.setdefault("profiles", {})[slot] = snap
        save_config(self.config)
        if slot in self._profile_rows:
            self._profile_rows[slot][1].setText("✓ " + tr("layout.profile_saved"))

    def _profile_load(self, slot: str) -> None:
        snap = (self.config.get("profiles", {}) or {}).get(slot) or {}
        if not snap:
            return
        preserved_profiles = self.config.get("profiles", {})
        preserved_names = self.config.get("profile_names", {})
        self.config.clear()
        self.config.update({**DEFAULT_CONFIG, **snap})
        self.config["profiles"] = preserved_profiles
        self.config["profile_names"] = preserved_names
        save_config(self.config)
        if self.parent_overlay:
            self.parent_overlay.apply_config()
            self.parent_overlay.apply_interval()
            self.parent_overlay.register_hotkey()
            self.parent_overlay.apply_window_flags()
        self.preview.apply_config(self.config)
        if slot in self._profile_rows:
            self._profile_rows[slot][1].setText("✓ " + tr("layout.profile_loaded"))

    def _profile_rename(self, slot: str) -> None:
        current = self.config.get("profile_names", {}).get(slot, slot.capitalize())
        new_name, ok = QInputDialog.getText(self, tr("layout.rename_title"),
                                            tr("layout.rename_prompt"), text=current)
        if not ok or not new_name.strip():
            return
        self.config.setdefault("profile_names", {})[slot] = new_name.strip()
        save_config(self.config)
        if slot in self._profile_rows:
            self._profile_rows[slot][0].setText(new_name.strip())

    # ---------- Page: Modules ----------
    def _build_page_modules(self) -> None:
        page, lay = self._page_scaffold(
            "Модули оверлея",
            "Какие блоки отображать. Отключённые модули не занимают место и не потребляют ресурсы."
        )
        grid = QGridLayout(); grid.setHorizontalSpacing(14); grid.setVerticalSpacing(12)

        toggles = [
            ("show_gpu", tr("mod.gpu")),
            ("show_cpu", tr("mod.cpu")),
            ("show_ram", tr("mod.ram")),
            ("show_clock", tr("mod.clock")),
            ("show_peak", tr("mod.peak")),
            ("show_network", tr("mod.network")),
            ("show_music", tr("mod.music")),
            ("show_visualizer", tr("mod.visualizer")),
            ("show_ai", tr("mod.ai")),
            ("show_battery", tr("mod.battery")),
            ("show_disk_io", tr("mod.disk_io")),
            ("show_cpu_temp", tr("mod.cpu_temp")),
            ("show_sparklines", tr("mod.sparklines")),
        ]
        self._module_checkboxes: dict[str, QCheckBox] = {}
        for i, (key, label) in enumerate(toggles):
            cb = QCheckBox(label)
            cb.setChecked(bool(self.config.get(key, True)))
            cb.stateChanged.connect(lambda s, k=key: self._commit(k, bool(s)))
            self._module_checkboxes[key] = cb
            grid.addWidget(cb, i // 2, i % 2)

        lay.addLayout(grid); lay.addStretch(1)
        self.stack.addWidget(page)

    # ---------- Page: Thresholds ----------
    def _build_page_thresholds(self) -> None:
        page, lay = self._page_scaffold(
            "Пороги тревог",
            "Warn — карточка окрашивается в жёлтый, Critical — в красный (+ голос для GPU, если включён)."
        )

        self.th_cpu = ThresholdEditor("CPU — загрузка", self.config.get("cpu_warn", 80), self.config.get("cpu_crit", 95))
        self.th_cpu.changed.connect(lambda w, c: self._commit_pair("cpu_warn", w, "cpu_crit", c))
        lay.addWidget(self.th_cpu)

        self.th_ram = ThresholdEditor("RAM — заполнение", self.config.get("ram_warn", 80), self.config.get("ram_crit", 92))
        self.th_ram.changed.connect(lambda w, c: self._commit_pair("ram_warn", w, "ram_crit", c))
        lay.addWidget(self.th_ram)

        self.th_gpu = ThresholdEditor("GPU — температура °C", self.config.get("gpu_warn", 75), self.config.get("gpu_crit", 85),
                                       vmin=40, vmax=100, unit="°")
        self.th_gpu.changed.connect(lambda w, c: self._commit_pair("gpu_warn", w, "gpu_crit", c))
        lay.addWidget(self.th_gpu)

        self.th_ping = ThresholdEditor("Ping — мс", self.config.get("ping_warn", 60), self.config.get("ping_crit", 120),
                                        vmin=10, vmax=400, unit="ms")
        self.th_ping.changed.connect(lambda w, c: self._commit_pair("ping_warn", w, "ping_crit", c))
        lay.addWidget(self.th_ping)

        lay.addStretch(1)
        self.stack.addWidget(page)

    # ---------- Page: Presets ----------
    def _build_page_presets(self) -> None:
        page, lay = self._page_scaffold(
            "Темы-пресеты",
            "Одним кликом применяют полный визуальный комплект: акцент, прозрачность, эффекты и раскладку."
        )

        grid = QGridLayout(); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(12)
        self._preset_cards: list[PresetCard] = []
        current = self.config.get("theme_preset", "Neon Mint")
        for i, (name, preset) in enumerate(THEME_PRESETS.items()):
            card = PresetCard(name, preset)
            card.setChecked(name == current)
            card.clicked.connect(lambda _c=False, n=name: self._apply_preset(n))
            self._preset_cards.append(card)
            grid.addWidget(card, i // 3, i % 3)
        lay.addLayout(grid)

        lay.addStretch(1)
        self.stack.addWidget(page)

    # ---------- Page: Games ----------
    def _build_page_games(self) -> None:
        page, lay = self._page_scaffold(
            "Игры для Smart Focus",
            "Оверлей появится, когда заголовок активного окна содержит одну из этих строк (регистр не важен)."
        )
        self.games_list = QListWidget()
        for g in self.config.get("target_games", []):
            QListWidgetItem(g, self.games_list)
        lay.addWidget(self.games_list, 1)

        row = QHBoxLayout()
        self.games_input = QLineEdit()
        self.games_input.setPlaceholderText("Название или часть названия игры…")
        self.games_input.returnPressed.connect(self._add_game)
        btn_add = QPushButton("➕  Добавить"); btn_add.clicked.connect(self._add_game)
        btn_rm = QPushButton("🗑  Удалить"); btn_rm.clicked.connect(self._remove_game)
        row.addWidget(self.games_input, 1); row.addWidget(btn_add); row.addWidget(btn_rm)
        lay.addLayout(row)

        self.stack.addWidget(page)

    # ---------- Page: About ----------
    def _build_page_about(self) -> None:
        page, lay = self._page_scaffold("О программе")
        accent = self.config["accent_color"]
        info = QTextEdit(); info.setReadOnly(True); info.setFrameStyle(QFrame.Shape.NoFrame)
        info.setHtml(
            f"""
            <div style="color:#ffffff;font-family:'Segoe UI';">
              <div style="font-size:22px;font-weight:900;color:{accent};">👻 Phantom Overlay · Hyper Edition</div>
              <div style="color:#a8b2d1;font-size:11px;margin-top:2px;">v{APP_VERSION}</div>

              <p style="color:#b6beda;font-size:12px;line-height:1.6;margin-top:18px;">
                Phantom — кастомный внутриигровой HUD нового поколения с
                полностью настраиваемым визуалом: круговой GPU-gauge, анимация
                значений, летающие частицы, conic-бордер, музыкальный
                визуализатор, 8 тем-пресетов и живой preview прямо в настройках.
              </p>

              <p style="color:#8891b0;font-size:11px;">
                <b>Хоткей:</b> Ctrl+Shift+P по дефолту. Настраивается через
                реальный recorder клавиш во вкладке «Общие».
                <br>Все настройки сохраняются в <code>phantom_config.json</code>.
              </p>

              <p style="color:#8891b0;font-size:11px;margin-top:18px;">
                Лицензия: MIT · PyQt6, psutil, ping3, winsdk, pypresence
                <br>Автор: iq28qi
              </p>
            </div>
            """
        )
        lay.addWidget(info, 1)
        self.stack.addWidget(page)

    # ---------- commit helpers ----------
    def _commit(self, key: str, value, save: bool = True, apply_live: bool = True,
                rehook: bool = False, rewindow: bool = False,
                apply_interval: bool = False, apply_geometry: bool = False,
                relang: bool = False) -> None:
        self.config[key] = value
        if save:
            save_config(self.config)
        if relang:
            set_language(str(value))
        if apply_live and self.parent_overlay:
            self.parent_overlay.apply_config()
        if rehook and self.parent_overlay:
            self.parent_overlay.register_hotkey()
        if rewindow and self.parent_overlay:
            self.parent_overlay.apply_window_flags()
        if apply_interval and self.parent_overlay:
            self.parent_overlay.apply_interval()
        if apply_geometry and self.parent_overlay:
            self.parent_overlay.apply_corner_snap()
        self.preview.apply_config(self.config)
        self._apply_styles()
        if relang:
            self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        try:
            self.setWindowTitle(tr("settings.title"))
            for i, key in enumerate(getattr(self, "_nav_keys", [])):
                self.nav.item(i).setText(f"{self._nav_icons[key]}   {tr('nav.' + key)}")
            if hasattr(self, "search_box"):
                self.search_box.setPlaceholderText(tr("search_ph"))
        except Exception as e:
            log_err("retranslate", e)

    def _commit_pair(self, k1, v1, k2, v2) -> None:
        self.config[k1] = int(v1); self.config[k2] = int(v2)
        save_config(self.config)
        if self.parent_overlay:
            self.parent_overlay.apply_config()
        self.preview.apply_config(self.config)

    # ---------- accent ----------
    def _refresh_accent_swatch(self) -> None:
        c = self.config.get("accent_color", "#00ff99")
        self.accent_swatch.setText(f"  {c.upper()}")
        self.accent_swatch.setStyleSheet(
            f"QPushButton {{ background-color: {c}; color: #0d0d12; "
            f"font-weight: 900; border: 1px solid rgba(255,255,255,40); "
            f"border-radius: 8px; letter-spacing: 1px; }}"
            f"QPushButton:hover {{ border: 1px solid rgba(255,255,255,90); }}"
        )

    def _set_accent(self, hex_: str) -> None:
        self.config["accent_color"] = hex_
        save_config(self.config)
        self._refresh_accent_swatch()
        self._apply_styles()
        if self.parent_overlay:
            self.parent_overlay.apply_config()
            self.parent_overlay.rebuild_tray_menu_styles()
        self.preview.apply_config(self.config)

    def _pick_accent(self) -> None:
        initial = QColor(self.config.get("accent_color", "#00ff99"))
        color = QColorDialog.getColor(initial, self, "Выберите акцентный цвет")
        if color.isValid():
            self._set_accent(color.name())

    # ---------- bg image ----------
    def _choose_background(self) -> None:
        fname, _ = QFileDialog.getOpenFileName(self, "Выбрать фон", "", "Images (*.png *.jpg *.jpeg)")
        if fname:
            self._commit("bg_image", fname)

    def _clear_background(self) -> None:
        self._commit("bg_image", "")

    # ---------- games ----------
    def _add_game(self) -> None:
        name = self.games_input.text().strip()
        if not name: return
        self.games_input.clear()
        QListWidgetItem(name, self.games_list)
        self._commit_games()

    def _remove_game(self) -> None:
        for item in self.games_list.selectedItems():
            self.games_list.takeItem(self.games_list.row(item))
        self._commit_games()

    def _commit_games(self) -> None:
        games = [self.games_list.item(i).text() for i in range(self.games_list.count())]
        self.config["target_games"] = games
        save_config(self.config)

    # ---------- presets ----------
    def _apply_preset(self, name: str) -> None:
        preset = THEME_PRESETS.get(name)
        if not preset: return
        for k, v in preset.items():
            self.config[k] = v
        self.config["theme_preset"] = name
        save_config(self.config)
        self._refresh_accent_swatch()
        self.slider_opacity.blockSignals(True); self.slider_opacity.setValue(int(self.config["opacity"])); self.slider_opacity.blockSignals(False)
        self.cb_border.blockSignals(True); self.cb_border.setChecked(bool(self.config["animated_border"])); self.cb_border.blockSignals(False)
        self.cb_particles.blockSignals(True); self.cb_particles.setChecked(bool(self.config["particles"])); self.cb_particles.blockSignals(False)
        self.cb_compact.blockSignals(True); self.cb_compact.setChecked(bool(self.config["compact_mode"])); self.cb_compact.blockSignals(False)
        for card in self._preset_cards:
            card.setChecked(card._name == name)
        if self.parent_overlay:
            self.parent_overlay.apply_config()
            self.parent_overlay.rebuild_tray_menu_styles()
        self.preview.apply_config(self.config)
        self._apply_styles()

    # ---------- import / export / reset ----------
    def _export_config(self) -> None:
        fname, _ = QFileDialog.getSaveFileName(self, "Экспорт конфигурации", "phantom_config.json", "JSON (*.json)")
        if not fname: return
        try:
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Экспорт", f"Конфигурация сохранена:\n{fname}")
        except OSError as e:
            log_err("export", e)
            QMessageBox.warning(self, "Экспорт", f"Не удалось сохранить файл: {e}")

    def _import_config(self) -> None:
        fname, _ = QFileDialog.getOpenFileName(self, "Импорт конфигурации", "", "JSON (*.json)")
        if not fname: return
        try:
            with open(fname, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in DEFAULT_CONFIG or k == "target_games":
                    self.config[k] = v
            save_config(self.config)
            if self.parent_overlay:
                self.parent_overlay.apply_config()
                self.parent_overlay.register_hotkey()
                self.parent_overlay.apply_interval()
                self.parent_overlay.apply_window_flags()
                self.parent_overlay.apply_corner_snap()
            self._apply_styles()
            self.preview.apply_config(self.config)
            QMessageBox.information(self, "Импорт", "Конфигурация импортирована.\nПерезайдите в окно настроек, чтобы увидеть все поля.")
        except (OSError, json.JSONDecodeError) as e:
            log_err("import", e)
            QMessageBox.warning(self, "Импорт", f"Не удалось прочитать файл: {e}")

    def _reset_config(self) -> None:
        ans = QMessageBox.question(
            self, "Сброс",
            "Сбросить настройки до значений по умолчанию?\nТекущая конфигурация будет перезаписана.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes: return
        for k, v in DEFAULT_CONFIG.items():
            self.config[k] = list(v) if isinstance(v, list) else v
        save_config(self.config)
        if self.parent_overlay:
            self.parent_overlay.apply_config()
            self.parent_overlay.register_hotkey()
            self.parent_overlay.apply_interval()
            self.parent_overlay.apply_window_flags()
            self.parent_overlay.apply_corner_snap()
        self._apply_styles()
        self.preview.apply_config(self.config)
        QMessageBox.information(self, "Сброс", "Настройки сброшены к значениям по умолчанию.")

    # ---------- styles ----------
    def _apply_styles(self) -> None:
        accent = self.config.get("accent_color", "#00ff99")
        self.setStyleSheet(
            f"""
            QDialog {{ background-color: #0b0b10; color: #e6e9f2; }}
            QWidget {{ color: #e6e9f2; }}
            QWidget#side {{ background-color: #0e0e14; border-right: 1px solid #1a1a24; }}
            QWidget#preview_holder {{ background-color: #09090d; border-left: 1px solid #1a1a24; }}
            QStackedWidget#stack {{ background-color: #0b0b10; }}
            QLabel {{ color: #c7cde3; font-family: 'Inter', 'Segoe UI'; font-size: 12px; font-weight: 600; background: transparent; }}
            QLabel#page_title {{ color: #ffffff; font-family: 'Inter', 'Segoe UI'; font-size: 20px; font-weight: 900; letter-spacing: 0.6px; }}
            QLabel#page_subtitle {{ color: #8891b0; font-size: 11px; font-weight: 500; }}
            QLabel#threshold_section {{ color: #ffffff; font-family: 'Inter', 'Segoe UI'; font-size: 12px; font-weight: 900; letter-spacing: 0.8px; }}
            QLabel#brand {{ color: {accent}; font-family: 'Inter', 'Segoe UI'; font-size: 14px; font-weight: 900; letter-spacing: 2.5px; }}
            QLabel#brand_version {{ color: #8891b0; font-size: 10px; letter-spacing: 0.6px; font-weight: 600; }}
            QLabel#live_title {{ color: #8891b0; font-family: 'Inter', 'Segoe UI'; font-size: 10px; font-weight: 900; letter-spacing: 2.2px; }}
            QLabel#live_hint {{ color: #6b7596; font-size: 10px; font-weight: 500; }}
            QListWidget#nav {{ background: transparent; color: #a8b2d1; font-family: 'Inter', 'Segoe UI';
                font-size: 12px; font-weight: 700; border: none; outline: 0; }}
            QListWidget#nav::item {{ padding: 10px 12px; border-radius: 8px; margin: 3px 0; }}
            QListWidget#nav::item:hover {{ background: rgba(255,255,255,10); color: #ffffff; }}
            QListWidget#nav::item:selected {{ background: rgba(255,255,255,14); color: {accent};
                border-left: 2px solid {accent}; }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: #14141c; color: {accent};
                border: 1px solid #1f1f27; border-radius: 8px; padding: 7px 10px;
                font-family: 'Inter', 'Segoe UI'; font-weight: 800; font-size: 12px; }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
                border: 1px solid {accent}; }}
            QComboBox::drop-down {{ border: none; width: 18px; }}
            QComboBox QAbstractItemView {{ background-color: #14141c; color: #ffffff;
                selection-background-color: {accent}; selection-color: #0b0b10;
                border: 1px solid #1f1f27; }}
            QSlider::groove:horizontal {{ border-radius: 4px; height: 8px; background: #1f1f27; }}
            QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {accent}, stop:1 rgba(255,255,255,220)); border-radius: 4px; }}
            QSlider::handle:horizontal {{ background: #ffffff; width: 18px; height: 18px;
                margin: -6px 0; border-radius: 9px; border: 2px solid {accent}; }}
            QPushButton {{ background-color: #14141c; color: {accent};
                border: 1px solid rgba(255,255,255,24); border-radius: 10px;
                padding: 7px 14px; font-weight: 800; font-family: 'Inter', 'Segoe UI'; }}
            QPushButton:hover {{ background-color: rgba(0,255,153,18); border: 1px solid {accent}; }}
            QPushButton#done_btn {{ background-color: {accent}; color: #0b0b10; border: none; letter-spacing: 0.8px; }}
            QPushButton#done_btn:hover {{ background-color: rgba(255,255,255,230); color: #0b0b10; }}
            QPushButton#reset_btn {{ color: #ff8888; border-color: rgba(255,90,90,60); }}
            QPushButton#reset_btn:hover {{ background: rgba(255,90,90,30); border-color: #ff5c5c; color: #ffffff; }}
            QCheckBox {{ color: #ffffff; font-family: 'Inter', 'Segoe UI'; font-size: 12px; spacing: 10px; background: transparent; }}
            QCheckBox::indicator {{ width: 38px; height: 20px; border-radius: 10px;
                background-color: #1f1f27; border: 1px solid #2a2a36; }}
            QCheckBox::indicator:checked {{ background-color: {accent}; border: 1px solid {accent}; }}
            QListWidget {{ background-color: #14141c; color: #e6e9f2;
                border: 1px solid #1f1f27; border-radius: 10px; padding: 6px;
                font-family: 'Inter', 'Segoe UI'; font-size: 12px; }}
            QListWidget::item {{ padding: 7px 10px; border-radius: 6px; }}
            QListWidget::item:selected {{ background: {accent}; color: #0b0b10; font-weight: 900; }}
            QTextEdit {{ background: transparent; border: none; }}
            QScrollArea {{ background: transparent; border: none; }}
            QFrame#live_preview {{ background: transparent; }}
            QScrollBar:vertical {{ background: transparent; width: 10px; }}
            QScrollBar::handle:vertical {{ background: rgba(255,255,255,30); border-radius: 5px; }}
            QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,60); }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            """
        )


# ==========================================================
#                    ГЛАВНЫЙ ОВЕРЛЕЙ
# ==========================================================
class PhantomOverlay(QMainWindow):
    """Главное окно оверлея.

    Собирает все виджеты внутри :class:`GlassPanel`, запускает
    :class:`HardwareMonitorThread`, слушает глобальные хоткеи через
    ``keyboard``, управляет треем и Smart Focus (авто-скрытие вне игр).
    Живёт поверх всех окон (WindowStaysOnTopHint) и перерисовывается
    на каждое событие :pyattr:`HardwareMonitorThread.data_updated`."""

    toggle_signal = pyqtSignal()
    settings_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config = load_config()
        set_language(self.config.get("language", "ru"))
        self.core = PhantomCore()
        if self.config.get("discord_enabled") and self.config.get("discord_client_id"):
            self.core.init_discord(self.config["discord_client_id"])
        self.is_locked = True
        self.manual_hidden = False
        self.dragPos = QPoint()
        self.current_toggle_hotkey = None
        self.current_settings_hotkey = None
        self._start_time = time.time()
        self._prev_ai_text = ""
        self._last_activity = time.time()
        self._autohidden = False

        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))

        self.apply_window_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._build_ui()

        self.move(self.config.get("pos_x", 100), self.config.get("pos_y", 100))
        self.setup_tray()
        self.apply_config()
        self.apply_corner_snap()

        self.toggle_signal.connect(self.do_toggle_visibility)
        self.settings_signal.connect(self.open_settings)
        self.register_hotkey()

        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._refresh_uptime)
        self._uptime_timer.start(1000)

        self._autohide_timer = QTimer(self)
        self._autohide_timer.timeout.connect(self._check_autohide)
        self._autohide_timer.start(1500)

        self.fade_in_anim()

        self.monitor_thread = HardwareMonitorThread(
            interval_ms=int(self.config.get("update_interval_ms", 1000)),
            ping_host=str(self.config.get("ping_host", "8.8.8.8")),
        )
        self.monitor_thread.data_updated.connect(self.update_ui)
        self.monitor_thread.start()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        self.panel = GlassPanel()
        self.panel.setObjectName("glass_panel")
        self.setCentralWidget(self.panel)

        self._root_layout = QVBoxLayout(self.panel)
        self._root_layout.setContentsMargins(18, 14, 18, 14); self._root_layout.setSpacing(10)

        self.particles = ParticleField(self.panel)
        self.particles.lower()
        self.particles.setGeometry(0, 0, self.width(), self.height())

        accent = self.config.get("accent_color", "#00ff99")

        # --- Header ---
        self.w_header = QWidget()
        header = QHBoxLayout(self.w_header); header.setContentsMargins(0,0,0,0); header.setSpacing(8)
        self.status_dot = StatusDot()
        self.lbl_title = QLabel("PHANTOM")
        tfont = QFont(UI_FONT_FAMILY, 12); tfont.setWeight(QFont.Weight.Black)
        tfont.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0)
        self.lbl_title.setFont(tfont); self.lbl_title.setStyleSheet("color: #ffffff;")
        self.lbl_uptime = QLabel("00:00")
        ufont = QFont(MONO_FONT_FAMILY, 9); ufont.setWeight(QFont.Weight.DemiBold)
        self.lbl_uptime.setFont(ufont)
        self.lbl_uptime.setStyleSheet(
            "color: rgba(255,255,255,140); background: rgba(255,255,255,14); "
            "border: 1px solid rgba(255,255,255,24); border-radius: 8px; padding: 2px 8px;"
        )
        self.btn_settings = IconButton("⚙", tr("settings"))
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_hide = IconButton("—", tr("hide"))
        self.btn_hide.clicked.connect(lambda: self.toggle_signal.emit())
        self.btn_quit = IconButton("✕", tr("quit"))
        self.btn_quit.clicked.connect(self._quit_app)
        header.addWidget(self.status_dot); header.addWidget(self.lbl_title)
        header.addSpacing(6); header.addWidget(self.lbl_uptime); header.addStretch(1)
        header.addWidget(self.btn_settings); header.addWidget(self.btn_hide); header.addWidget(self.btn_quit)

        # --- Chips ---
        self.w_chips = QWidget()
        chips_row = QHBoxLayout(self.w_chips); chips_row.setContentsMargins(0,0,0,0); chips_row.setSpacing(6)
        self.chip_battery = Chip(); self.chip_battery.setText("🔋 —")
        self.chip_cpu_temp = Chip(); self.chip_cpu_temp.setText("🌡 —")
        self.chip_disk = Chip(); self.chip_disk.setText("💽 —")
        chips_row.addWidget(self.chip_battery); chips_row.addWidget(self.chip_cpu_temp)
        chips_row.addWidget(self.chip_disk); chips_row.addStretch(1)

        # --- Clock ---
        self.w_clock = ClockWidget(accent=accent, show_seconds=bool(self.config.get("clock_seconds", True)))

        # --- Body (gauge + cpu/ram) ---
        self.w_body = QWidget()
        body = QHBoxLayout(self.w_body); body.setContentsMargins(0,0,0,0); body.setSpacing(12)
        self.gauge = CircularGauge(accent=accent,
                                   warn=self.config.get("gpu_warn", 75),
                                   crit=self.config.get("gpu_crit", 85))
        body.addWidget(self.gauge, 0, Qt.AlignmentFlag.AlignTop)
        cards_col = QVBoxLayout(); cards_col.setSpacing(8)
        show_spark = bool(self.config.get("show_sparklines", True))
        self.card_cpu = MetricCard("🧠", "CPU", accent=accent, show_sparkline=show_spark,
                                   warn=self.config.get("cpu_warn", 80), crit=self.config.get("cpu_crit", 95))
        self.card_ram = MetricCard("💾", "RAM", accent=accent, show_sparkline=show_spark,
                                   warn=self.config.get("ram_warn", 80), crit=self.config.get("ram_crit", 92))
        cards_col.addWidget(self.card_cpu); cards_col.addWidget(self.card_ram)
        body.addLayout(cards_col, 1)

        # --- Peak ---
        self.w_peak = PeakValuesWidget(accent=accent)

        # --- Visualizer ---
        self.visualizer = MusicVisualizer(accent=accent)

        # --- Network ---
        self.lbl_net = QLabel()
        nfont = QFont(MONO_FONT_FAMILY, 9); nfont.setWeight(QFont.Weight.DemiBold)
        self.lbl_net.setFont(nfont)
        self.lbl_net.setText("🌐  —  ·  ↑ 0 KB/s  ·  ↓ 0 KB/s")
        self.lbl_net.setStyleSheet(
            "color: rgba(255,255,255,170); background: rgba(255,255,255,10); "
            "border: 1px solid rgba(255,255,255,20); border-radius: 8px; padding: 4px 10px;"
        )

        # --- Music ---
        self.lbl_music = Marquee()
        mfont = QFont(UI_FONT_FAMILY, 10); mfont.setItalic(True); mfont.setWeight(QFont.Weight.Medium)
        self.lbl_music.setFont(mfont)
        self.lbl_music.setStyleSheet("color: rgba(255,255,255,180);")
        self.lbl_music.setFixedHeight(18)
        self.lbl_music.setText("🎵  " + tr("wait_media"))

        # --- AI ---
        self.lbl_ai = QLabel("🤖  Silphiette: " + tr("working"))
        afont = QFont(UI_FONT_FAMILY, 10); afont.setWeight(QFont.Weight.DemiBold); afont.setItalic(True)
        self.lbl_ai.setFont(afont)
        self.lbl_ai.setStyleSheet("color: #ffcc66;")
        self.lbl_ai.setWordWrap(True)

        # Map module keys -> widgets
        self._modules = {
            "header": self.w_header,
            "chips": self.w_chips,
            "clock": self.w_clock,
            "body": self.w_body,
            "peak": self.w_peak,
            "visualizer": self.visualizer,
            "network": self.lbl_net,
            "music": self.lbl_music,
            "ai": self.lbl_ai,
        }
        self.sep = QFrame(); self.sep.setFixedHeight(1)
        self.sep.setStyleSheet("background: rgba(255,255,255,22); border: none;")

        self._rebuild_module_order()

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(48); self._shadow.setXOffset(0); self._shadow.setYOffset(10)
        self._shadow.setColor(QColor(0, 0, 0, 210))
        self.panel.setGraphicsEffect(self._shadow)

        self._resize_for_mode()

    def _rebuild_module_order(self) -> None:
        """Re-lay out all module widgets in the user-defined order."""
        layout = self._root_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        order = list(self.config.get("module_order", []))
        for key in list(self._modules.keys()):
            if key not in order:
                order.append(key)
        first = True
        for key in order:
            w = self._modules.get(key)
            if w is None:
                continue
            if not first and key in ("body", "visualizer"):
                s = QFrame(); s.setFixedHeight(1)
                s.setStyleSheet("background: rgba(255,255,255,22); border: none;")
                layout.addWidget(s)
            layout.addWidget(w)
            first = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "particles"):
            self.particles.setGeometry(0, 0, self.width(), self.height())

    def _resize_for_mode(self) -> None:
        mode = self.config.get("window_mode", "auto")
        if mode == "fixed":
            w = int(self.config.get("fixed_width", 440))
            h = int(self.config.get("fixed_height", 420))
            self.setFixedSize(max(220, w), max(200, h))
            return
        # allow resize in other modes
        self.setMinimumSize(220, 200)
        self.setMaximumSize(16777215, 16777215)
        if mode in WINDOW_SIZES:
            w, h = WINDOW_SIZES[mode]
            self.resize(w, h)
        elif self.config.get("compact_mode", False):
            self.resize(300, 320)
        else:
            self.resize(360, 380)

    # ---------- hotkeys ----------
    def register_hotkey(self):
        try:
            for existing in (self.current_toggle_hotkey, self.current_settings_hotkey):
                if existing:
                    try:
                        keyboard.remove_hotkey(existing)
                    except Exception as e:
                        log_err("hotkey.remove", e)
            self.current_toggle_hotkey = self.config.get("hotkey_toggle", "ctrl+shift+p")
            self.current_settings_hotkey = self.config.get("hotkey_settings", "")
            if self.current_toggle_hotkey:
                keyboard.add_hotkey(self.current_toggle_hotkey,
                                    lambda: self.toggle_signal.emit())
            if self.current_settings_hotkey:
                keyboard.add_hotkey(self.current_settings_hotkey,
                                    lambda: self.settings_signal.emit())
        except Exception as e:
            log_err("hotkey.add", e)

    # ---------- window flags ----------
    def apply_window_flags(self):
        base = Qt.WindowType.FramelessWindowHint
        if self.config.get("always_on_top", True):
            base |= Qt.WindowType.WindowStaysOnTopHint
        if not self.config.get("show_in_taskbar", False):
            base |= Qt.WindowType.Tool
        else:
            base |= Qt.WindowType.Window
        self.setWindowFlags(base)
        click_through = bool(self.config.get("click_through", False))
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            self.is_locked or click_through,
        )
        if self.isVisible():
            self.hide(); self.show()

    # ---------- corner snap ----------
    def apply_corner_snap(self) -> None:
        corner = self.config.get("corner_snap", "none")
        if corner == "none":
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        g = screen.availableGeometry()
        m = int(self.config.get("corner_margin", 24))
        w = self.width() or 360
        h = self.height() or 380
        if corner == "tl":
            x, y = g.x() + m, g.y() + m
        elif corner == "tr":
            x, y = g.x() + g.width() - w - m, g.y() + m
        elif corner == "bl":
            x, y = g.x() + m, g.y() + g.height() - h - m
        elif corner == "br":
            x, y = g.x() + g.width() - w - m, g.y() + g.height() - h - m
        else:
            return
        self.move(x, y)
        self.config["pos_x"], self.config["pos_y"] = x, y
        save_config(self.config)

    # ---------- animations ----------
    def fade_in_anim(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(700)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(max(0.1, self.config["opacity"] / 255.0))
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

    def do_toggle_visibility(self):
        self.manual_hidden = not self.manual_hidden
        if not self.manual_hidden:
            self.show(); self.fade_in_anim()
        else:
            self.hide()

    # ---------- config ----------
    def apply_interval(self) -> None:
        try:
            self.monitor_thread.set_interval_ms(int(self.config.get("update_interval_ms", 1000)))
            self.monitor_thread.set_ping_host(str(self.config.get("ping_host", "8.8.8.8")))
        except Exception as e:
            log_err("interval.apply", e)

    def apply_config(self):
        set_language(self.config.get("language", "ru"))
        set_color_mode(str(self.config.get("color_mode", "steps")))
        HoverGlow.set_enabled(bool(self.config.get("hover_microanim", True)))
        if not hasattr(self, "anim") or self.anim.state() != QPropertyAnimation.State.Running:
            self.setWindowOpacity(max(0.1, self.config["opacity"] / 255.0))
        accent = self.config.get("accent_color", "#00ff99")
        show_spark = bool(self.config.get("show_sparklines", True))

        # accents
        self.card_cpu.set_accent(accent); self.card_ram.set_accent(accent)
        self.gauge.set_accent(accent); self.visualizer.set_accent(accent)
        self.particles.set_accent(accent)
        self.panel.set_accent(accent)
        self.chip_battery.set_accent(accent); self.chip_cpu_temp.set_accent(accent); self.chip_disk.set_accent(accent)
        self.w_clock.set_accent(accent); self.w_peak.set_accent(accent)

        # thresholds
        self.card_cpu.set_thresholds(self.config.get("cpu_warn", 80), self.config.get("cpu_crit", 95))
        self.card_ram.set_thresholds(self.config.get("ram_warn", 80), self.config.get("ram_crit", 92))
        self.gauge.set_thresholds(self.config.get("gpu_warn", 75), self.config.get("gpu_crit", 85))

        # visibility (cards inside body)
        self.card_cpu.setVisible(self.config.get("show_cpu", True))
        self.card_ram.setVisible(self.config.get("show_ram", True))
        self.gauge.setVisible(self.config.get("show_gpu", True))
        self.card_cpu.set_sparkline_visible(show_spark)
        self.card_ram.set_sparkline_visible(show_spark)

        # chips inside chips-row
        self.chip_battery.setVisible(bool(self.config.get("show_battery", True)))
        self.chip_cpu_temp.setVisible(bool(self.config.get("show_cpu_temp", True)))
        self.chip_disk.setVisible(bool(self.config.get("show_disk_io", True)))

        # module-level visibility (each whole block)
        module_visible = {
            "header": True,
            "chips": any([self.chip_battery.isVisible(), self.chip_cpu_temp.isVisible(), self.chip_disk.isVisible()]),
            "clock": bool(self.config.get("show_clock", True)),
            "body": any([self.gauge.isVisible(), self.card_cpu.isVisible(), self.card_ram.isVisible()]),
            "peak": bool(self.config.get("show_peak", False)),
            "visualizer": bool(self.config.get("show_visualizer", True)),
            "network": bool(self.config.get("show_network", True)),
            "music": bool(self.config.get("show_music", True)),
            "ai": bool(self.config.get("show_ai", True)),
        }
        for key, widget in self._modules.items():
            widget.setVisible(module_visible.get(key, True))

        self.w_clock.set_show_seconds(bool(self.config.get("clock_seconds", True)))

        # rebuild layout order
        self._rebuild_module_order()

        # flair
        self.panel.set_animated_border(bool(self.config.get("animated_border", True)))
        self.panel.set_background_image(self.config.get("bg_image", ""))
        self.panel.set_unlocked(not self.is_locked)
        self.panel.set_corner_radius(int(self.config.get("corner_radius", 18)))
        self.panel.set_border_style(str(self.config.get("border_style", "solid")))
        self.particles.set_enabled(bool(self.config.get("particles", True)))

        # shadow intensity
        try:
            intensity = int(self.config.get("shadow_intensity", 48))
            self._shadow.setBlurRadius(max(0, intensity))
            self._shadow.setColor(QColor(0, 0, 0, min(255, 80 + intensity*3)))
        except Exception as e:
            log_err("shadow", e)

        # font scale
        scale = float(self.config.get("font_scale", 1.0))
        self.lbl_title.setFont(self._scaled_title_font(scale))

        # buttons retranslation
        self.btn_settings.setToolTip(tr("settings"))
        self.btn_hide.setToolTip(tr("hide"))
        self.btn_quit.setToolTip(tr("quit"))

        self._resize_for_mode()

    def _scaled_title_font(self, scale: float) -> QFont:
        f = QFont(UI_FONT_FAMILY, max(8, int(12 * scale)))
        f.setWeight(QFont.Weight.Black)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0 * scale)
        return f

    # ---------- drag ----------
    def _drag_enabled(self) -> bool:
        return (not self.is_locked) and (not bool(self.config.get("drag_lock", False)))

    def mousePressEvent(self, event):
        self._last_activity = time.time()
        if self._drag_enabled() and event.button() == Qt.MouseButton.LeftButton:
            self.dragPos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        self._last_activity = time.time()
        if self._drag_enabled() and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.dragPos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_enabled() and event.button() == Qt.MouseButton.LeftButton:
            self.config["pos_x"], self.config["pos_y"] = self.x(), self.y()
            save_config(self.config)

    def enterEvent(self, event):
        self._last_activity = time.time()
        if self._autohidden:
            self._autohidden = False
            self.setWindowOpacity(max(0.1, self.config.get("opacity", 235) / 255.0))
        super().enterEvent(event)

    def _check_autohide(self) -> None:
        try:
            secs = int(self.config.get("auto_hide_secs", 0))
        except Exception:
            secs = 0
        if secs <= 0 or self.manual_hidden:
            return
        idle = time.time() - self._last_activity
        if idle > secs and not self._autohidden:
            self._autohidden = True
            self.setWindowOpacity(0.18)
        elif idle <= secs and self._autohidden:
            self._autohidden = False
            self.setWindowOpacity(max(0.1, self.config.get("opacity", 235) / 255.0))

    # ---------- tray ----------
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists("icon.png"):
            self.tray_icon.setIcon(QIcon("icon.png"))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        self.tray_menu = QMenu()
        self.lock_action = QAction("🛠 Режим перетаскивания", self)
        self.lock_action.triggered.connect(self.toggle_lock)
        self.tray_menu.addAction(self.lock_action)

        self.hide_action = QAction("👁 Скрыть / показать", self)
        self.hide_action.triggered.connect(lambda: self.toggle_signal.emit())
        self.tray_menu.addAction(self.hide_action)

        self.tray_menu.addSeparator()

        music_play = QAction("⏯ Play / Pause", self)
        music_play.triggered.connect(lambda: self._safe_media_key("play/pause media"))
        self.tray_menu.addAction(music_play)
        music_next = QAction("⏭ Следующий", self)
        music_next.triggered.connect(lambda: self._safe_media_key("next track"))
        self.tray_menu.addAction(music_next)
        music_prev = QAction("⏮ Предыдущий", self)
        music_prev.triggered.connect(lambda: self._safe_media_key("previous track"))
        self.tray_menu.addAction(music_prev)

        self.tray_menu.addSeparator()

        presets_menu = QMenu("🎭 Тема", self.tray_menu)
        for name in THEME_PRESETS.keys():
            act = QAction(name, self); act.triggered.connect(lambda _c=False, n=name: self._apply_theme_preset(n))
            presets_menu.addAction(act)
        self.tray_menu.addMenu(presets_menu)

        self.tray_menu.addAction(QAction("⚙ Настройки", self, triggered=self.open_settings))
        self.tray_menu.addAction(QAction("❌ Выход", self, triggered=self._quit_app))

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        self.rebuild_tray_menu_styles()

    def rebuild_tray_menu_styles(self) -> None:
        accent = self.config.get("accent_color", "#00ff99")
        self.tray_menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: #0b0b10; color: #ffffff;
                border: 1px solid #1a1a24; border-radius: 10px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 26px; border-radius: 6px; margin: 2px 4px;
                font-family: 'Inter', 'Segoe UI'; font-weight: 700;
            }}
            QMenu::item:selected {{ background-color: {accent}; color: #0b0b10; font-weight: 900; }}
            QMenu::separator {{ height: 1px; background: #1f1f27; margin: 4px 10px; }}
            """
        )

    def _apply_theme_preset(self, name: str) -> None:
        preset = THEME_PRESETS.get(name)
        if not preset:
            return
        for k, v in preset.items():
            self.config[k] = v
        self.config["theme_preset"] = name
        save_config(self.config)
        self.apply_config()
        self.rebuild_tray_menu_styles()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_signal.emit()

    def _safe_media_key(self, key: str) -> None:
        try:
            keyboard.send(key)
        except Exception as e:
            log_err("media.key", e)

    def _quit_app(self) -> None:
        try:
            if hasattr(self, "monitor_thread"):
                self.monitor_thread.stop(); self.monitor_thread.wait(2000)
        except Exception as e:
            log_err("quit.thread", e)
        QApplication.instance().quit()

    def open_settings(self):
        dlg = ModernSettings(self.config, self)
        dlg.exec()

    def toggle_lock(self):
        self.is_locked = not self.is_locked
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.is_locked)
        self.lock_action.setText(
            "🔒 Закрепить окно" if not self.is_locked else "🛠 Режим перетаскивания"
        )
        self.apply_config()

    # ---------- uptime ----------
    def _refresh_uptime(self) -> None:
        secs = int(time.time() - self._start_time)
        h, rem = divmod(secs, 3600); m, s = divmod(rem, 60)
        if h:
            self.lbl_uptime.setText(f"⏱ {h:02d}:{m:02d}:{s:02d}")
        else:
            self.lbl_uptime.setText(f"⏱ {m:02d}:{s:02d}")

    # ---------- data ----------
    def update_ui(self, data: dict):
        accent = self.config.get("accent_color", "#00ff99")

        gpu_temp = data.get("gpu_temp")
        gpu_util = data.get("gpu_util")
        gpu_crit = int(self.config.get("gpu_crit", 85))
        gpu_warn = int(self.config.get("gpu_warn", 75))

        self.gauge.set_values(gpu_temp, gpu_util)

        # critical state for panel (red pulsing overlay)
        critical_now = False
        if isinstance(gpu_temp, int):
            if gpu_temp > gpu_crit:
                self.status_dot.set_color("#ff5c5c"); critical_now = True
                if self.config.get("enable_voice", True):
                    self.core.say("Внимание! Видеокарта перегревается.")
            elif gpu_temp > gpu_warn:
                self.status_dot.set_color("#ffcc66")
            else:
                self.status_dot.set_color(accent)
        else:
            self.status_dot.set_color(accent)
        self.panel.set_critical(critical_now)

        # CPU
        cpu = float(data.get("cpu", 0) or 0)
        try:
            cpu_freq = psutil.cpu_freq()
            freq_text = f"{cpu_freq.current/1000:.2f} GHz" if cpu_freq else "загрузка"
        except Exception:
            freq_text = "загрузка"
        self.card_cpu.set_value(cpu, f"{cpu:.0f}%", secondary=freq_text,
                                critical_override=cpu >= self.config.get("cpu_crit", 95))

        # RAM
        ram = float(data.get("ram", 0) or 0)
        try:
            vm = psutil.virtual_memory()
            ram_sec = f"{vm.used/(1024**3):.1f} / {vm.total/(1024**3):.1f} GB"
        except Exception:
            ram_sec = "память"
        self.card_ram.set_value(ram, f"{ram:.0f}%", secondary=ram_sec,
                                critical_override=ram >= self.config.get("ram_crit", 92))

        # CHIPS: battery / cpu_temp / disk
        bat = data.get("battery_percent")
        bat_plugged = data.get("battery_plugged")
        if isinstance(bat, int):
            icon = "🔌" if bat_plugged else "🔋"
            self.chip_battery.setText(f"{icon} {bat}%")
        else:
            self.chip_battery.setText("🔋 —")

        cpu_t = data.get("cpu_temp")
        if isinstance(cpu_t, int):
            self.chip_cpu_temp.setText(f"🌡 CPU {cpu_t}°")
        else:
            self.chip_cpu_temp.setText("🌡 CPU —")

        read = float(data.get("disk_read", 0.0) or 0.0)
        write = float(data.get("disk_write", 0.0) or 0.0)
        self.chip_disk.setText(f"💽 R {_fmt_bytes(read)}/s · W {_fmt_bytes(write)}/s")

        # NET
        ping_val = data.get("ping")
        up = float(data.get("net_up", 0.0) or 0.0)
        down = float(data.get("net_down", 0.0) or 0.0)
        ping_text = f"{ping_val} ms" if isinstance(ping_val, int) else "—"
        ping_color = accent
        if isinstance(ping_val, int):
            if ping_val > self.config.get("ping_crit", 120): ping_color = "#ff5c5c"
            elif ping_val > self.config.get("ping_warn", 60): ping_color = "#ffcc66"
        self.lbl_net.setText(f"🌐  {ping_text}   ·   ↑ {up:5.0f} KB/s   ·   ↓ {down:5.0f} KB/s")
        self.lbl_net.setStyleSheet(
            f"color: {ping_color}; background: rgba(255,255,255,10); "
            "border: 1px solid rgba(255,255,255,20); border-radius: 8px; padding: 4px 10px;"
        )

        # PEAK values
        gpu_t_val = gpu_temp if isinstance(gpu_temp, int) else None
        ping_num = ping_val if isinstance(ping_val, int) else None
        self.w_peak.push(cpu=cpu, ram=ram, gpu_t=gpu_t_val, ping_ms=ping_num)

        # MUSIC + visualizer
        music = (data.get("music", "") or "").strip()
        self.lbl_music.setText(f"🎵  {music}" if music else "🎵  —")
        self.visualizer.set_active(bool(music) and "—" not in music[:2])

        # AI
        if self.config.get("show_ai", True):
            ai_text = self._compose_ai_status(gpu_temp, cpu, ram, ping_val, bat)
            if ai_text != self._prev_ai_text:
                self._prev_ai_text = ai_text
                self.lbl_ai.setText(ai_text)

        # DISCORD (if enabled)
        try:
            if self.config.get("discord_enabled"):
                temp_str = f"{gpu_temp}°C" if isinstance(gpu_temp, int) else "N/A"
                self.core.update_discord(state=f"GPU: {temp_str}", details=(music[:35] or "—"))
        except Exception as e:
            log_err("discord.update.ui", e)

        # SMART FOCUS
        if (
            self.config.get("smart_hide", False)
            and self.is_locked
            and not self.manual_hidden
        ):
            active = (data.get("active_title") or "").lower()
            games = [g.lower() for g in self.config.get("target_games", []) if g]
            is_gaming = any(g in active for g in games)
            self.setVisible(is_gaming)

    def _compose_ai_status(self, gpu_temp, cpu, ram, ping_val, battery) -> str:
        if isinstance(gpu_temp, int) and gpu_temp > self.config.get("gpu_crit", 85):
            return "🤖  Silphiette: перегрев GPU! Снизь нагрузку."
        if cpu >= self.config.get("cpu_crit", 95):
            return "🤖  Silphiette: CPU на 100% — фоновые задачи?"
        if ram >= self.config.get("ram_crit", 92):
            return "🤖  Silphiette: память почти закончилась."
        if isinstance(ping_val, int) and ping_val > self.config.get("ping_crit", 120):
            return "🤖  Silphiette: сеть не в форме — высокий пинг."
        if isinstance(battery, int) and battery <= 15:
            return "🤖  Silphiette: батарея разряжается — подключи питание."
        return "🤖  Silphiette: система в норме."

    # ---------- shutdown ----------
    def closeEvent(self, event):
        try:
            if hasattr(self, "monitor_thread"):
                self.monitor_thread.stop(); self.monitor_thread.wait(2000)
        except Exception as e:
            log_err("close.thread", e)
        super().closeEvent(event)


# ==========================================================
#                          MAIN
# ==========================================================
def _install_excepthook() -> None:
    def _hook(exc_type, exc, tb):
        sys.stderr.write("[phantom][unhandled] " + "".join(traceback.format_exception(exc_type, exc, tb)))
    sys.excepthook = _hook


if __name__ == "__main__":
    _install_excepthook()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    # Регистрируем вшитые шрифты до построения UI, чтобы все QFont/styleSheet
    # подтянули Inter / JetBrains Mono сразу при первой отрисовке.
    load_bundled_fonts()
    overlay = PhantomOverlay()
    overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    overlay.show()
    sys.exit(app.exec())