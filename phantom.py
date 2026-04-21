import sys
import os
import json
import time
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
    QCheckBox, QHBoxLayout, QLineEdit, QTabWidget, QSpinBox, QListWidget,
    QListWidgetItem, QColorDialog, QGraphicsDropShadowEffect, QSizePolicy,
    QFrame, QTextEdit
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QPoint, QPropertyAnimation, QEasingCurve,
    QRectF, QTimer
)
from PyQt6.QtGui import (
    QAction, QIcon, QColor, QPainter, QLinearGradient, QPen, QBrush, QPainterPath,
)

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as SessionManager,
    )
    HAS_WINSDK = True
except ImportError:
    HAS_WINSDK = False


# ==========================================================
#                      НАСТРОЙКИ (CONFIG)
# ==========================================================
CONFIG_FILE = "phantom_config.json"

APP_VERSION = "4.1.0 — Polished Edition"

DEFAULT_CONFIG = {
    "opacity": 200,
    "theme": "dark",
    "bg_image": "",
    "accent_color": "#00ff99",
    "show_ai": True,
    "smart_hide": False,
    "enable_voice": True,
    "show_in_taskbar": False,
    "show_sparklines": True,
    "show_network_rate": True,
    "compact_mode": False,
    "hotkey_toggle": "ctrl+shift+p",
    "update_interval_ms": 1000,
    "pos_x": 100,
    "pos_y": 100,
    "target_games": [
        "CS2", "Counter-Strike", "Dota 2", "Genshin Impact", "Minecraft",
        "GTA 5", "Cyberpunk 2077", "Valorant", "Fortnite", "Apex Legends",
    ],
}


def log_err(prefix: str, exc: BaseException) -> None:
    """Единая точка логирования ошибок — без голых except."""
    try:
        sys.stderr.write(f"[phantom][{prefix}] {type(exc).__name__}: {exc}\n")
    except Exception:
        pass


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = {**DEFAULT_CONFIG, **data}
            # гарантируем, что список игр есть и валиден
            games = merged.get("target_games") or DEFAULT_CONFIG["target_games"]
            merged["target_games"] = [str(g).strip() for g in games if str(g).strip()]
            return merged
        except (OSError, json.JSONDecodeError) as e:
            log_err("config.load", e)
    return {**DEFAULT_CONFIG, "target_games": list(DEFAULT_CONFIG["target_games"])}


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except OSError as e:
        log_err("config.save", e)


# ==========================================================
#               ЯДРО АССИСТЕНТА И DISCORD
# ==========================================================
class PhantomCore:
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

    def init_discord(self, client_id: str):
        if not client_id or "CLIENT_ID" in client_id:
            return
        try:
            self.rpc = Presence(client_id)
            self.rpc.connect()
            self.discord_connected = True
        except Exception as e:
            log_err("discord.connect", e)
            self.discord_connected = False

    def update_discord(self, state, details):
        if not (self.discord_connected and self.rpc):
            return
        try:
            self.rpc.update(state=state, details=details, large_image="logo")
        except Exception as e:
            log_err("discord.update", e)

    def say(self, text):
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
    data_updated = pyqtSignal(dict)

    def __init__(self, interval_ms: int = 1000):
        super().__init__()
        self.running = True
        self._interval = max(200, int(interval_ms)) / 1000.0
        self.nvml_initialized = False
        self.loop = asyncio.new_event_loop()
        self._prev_net = None
        self._prev_net_time = None
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

    def stop(self) -> None:
        self.running = False

    def run(self):
        asyncio.set_event_loop(self.loop)
        while self.running:
            data: dict = {}

            # CPU / RAM
            try:
                data["cpu"] = psutil.cpu_percent()
                data["ram"] = psutil.virtual_memory().percent
            except Exception as e:
                log_err("psutil", e)
                data["cpu"] = random.randint(18, 25)
                data["ram"] = random.randint(45, 50)

            # GPU
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

            # PING
            try:
                p = ping("8.8.8.8", timeout=1)
                data["ping"] = int(p * 1000) if p else None
            except Exception as e:
                log_err("ping", e)
                data["ping"] = None

            # NET RATE (KB/s)
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

            # MUSIC
            try:
                data["music"] = self.loop.run_until_complete(self.get_music_info())
            except Exception as e:
                log_err("media", e)
                data["music"] = "No Media"

            # ACTIVE WINDOW
            try:
                win = gw.getActiveWindow()
                data["active_title"] = win.title if win else ""
            except Exception as e:
                log_err("gw", e)
                data["active_title"] = ""

            self.data_updated.emit(data)
            # небольшими «шагами», чтобы stop() сработал быстро
            slept = 0.0
            while self.running and slept < self._interval:
                time.sleep(0.1)
                slept += 0.1

    async def get_music_info(self):
        if not HAS_WINSDK:
            return "Media API unavailable"
        try:
            sessions = await SessionManager.request_async()
            curr = sessions.get_current_session()
            if curr:
                info = await curr.try_get_media_properties_async()
                return f"🎵 {info.artist or 'Unknown'} — {info.title or 'Track'}"
            return "⏸ Тишина"
        except Exception as e:
            log_err("winsdk.media", e)
            return "No Media"


# ==========================================================
#                   КАСТОМНЫЕ ВИДЖЕТЫ
# ==========================================================
class Sparkline(QWidget):
    """Мини-график последних N значений метрики (0..100)."""

    def __init__(self, capacity: int = 60, color: str = "#00ff99", parent=None):
        super().__init__(parent)
        self._buf: deque[float] = deque(maxlen=capacity)
        self._color = QColor(color)
        self.setMinimumHeight(24)
        self.setMaximumHeight(24)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

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

        w = self.width()
        h = self.height()
        n = self._buf.maxlen or 60
        step = w / (n - 1)

        # путь под заливку
        path = QPainterPath()
        fill_path = QPainterPath()

        start_x = w - step * (len(self._buf) - 1)
        pts = []
        for i, v in enumerate(self._buf):
            x = start_x + i * step
            y = h - (v / 100.0) * (h - 2) - 1
            pts.append((x, y))

        if not pts:
            return

        path.moveTo(pts[0][0], pts[0][1])
        fill_path.moveTo(pts[0][0], h)
        fill_path.lineTo(pts[0][0], pts[0][1])
        for x, y in pts[1:]:
            path.lineTo(x, y)
            fill_path.lineTo(x, y)
        fill_path.lineTo(pts[-1][0], h)
        fill_path.closeSubpath()

        # градиентная заливка под линией
        grad = QLinearGradient(0, 0, 0, h)
        c1 = QColor(self._color)
        c1.setAlpha(120)
        c2 = QColor(self._color)
        c2.setAlpha(0)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        painter.fillPath(fill_path, QBrush(grad))

        # сама линия
        pen = QPen(self._color)
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)


class MetricBar(QWidget):
    """Строка-метрика: иконка + название слева, значение справа, градиентный бар снизу."""

    def __init__(self, icon: str, name: str, accent: str = "#00ff99",
                 show_sparkline: bool = True, parent=None):
        super().__init__(parent)
        self._accent = QColor(accent)
        self._value = 0.0
        self._value_text = "--"
        self._critical = False

        self._icon = icon
        self._name = name

        self._build_ui(show_sparkline)

    def _build_ui(self, show_sparkline: bool) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)

        self.lbl_name = QLabel(f"{self._icon}  {self._name}")
        self.lbl_name.setStyleSheet(
            "color: rgba(255,255,255,210); font-family: 'Segoe UI'; "
            "font-size: 12px; font-weight: 600; letter-spacing: 0.3px;"
        )
        self.lbl_value = QLabel("--")
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_value.setStyleSheet(
            f"color: {self._accent.name()}; font-family: 'Segoe UI'; "
            "font-size: 12px; font-weight: 700;"
        )
        top.addWidget(self.lbl_name, 1)
        top.addWidget(self.lbl_value, 0)
        root.addLayout(top)

        self.sparkline = Sparkline(color=self._accent.name())
        self.sparkline.setVisible(show_sparkline)
        root.addWidget(self.sparkline)

        self.setMinimumHeight(32)

    def set_accent(self, color: str) -> None:
        self._accent = QColor(color)
        self.lbl_value.setStyleSheet(
            f"color: {self._accent.name()}; font-family: 'Segoe UI'; "
            "font-size: 12px; font-weight: 700;"
        )
        self.sparkline.set_color(color)
        self.update()

    def set_sparkline_visible(self, visible: bool) -> None:
        self.sparkline.setVisible(visible)

    def set_value(self, percent: float, text: str, critical: bool = False) -> None:
        try:
            self._value = max(0.0, min(100.0, float(percent)))
        except (TypeError, ValueError):
            self._value = 0.0
        self._value_text = text
        self._critical = bool(critical)
        self.lbl_value.setText(text)
        if critical:
            self.lbl_value.setStyleSheet(
                "color: #ff5c5c; font-family: 'Segoe UI'; font-size: 12px; font-weight: 800;"
            )
        else:
            self.lbl_value.setStyleSheet(
                f"color: {self._accent.name()}; font-family: 'Segoe UI'; "
                "font-size: 12px; font-weight: 700;"
            )
        self.sparkline.push(self._value)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_h = 4
        bar_y = h - bar_h

        # фон бара
        bg = QColor(255, 255, 255, 28)
        rect_bg = QRectF(0, bar_y, w, bar_h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect_bg, bar_h / 2, bar_h / 2)

        # заливка
        filled_w = max(0.0, min(1.0, self._value / 100.0)) * w
        if filled_w > 1.0:
            rect_fg = QRectF(0, bar_y, filled_w, bar_h)
            grad = QLinearGradient(0, 0, w, 0)
            if self._critical:
                grad.setColorAt(0.0, QColor("#ff6b6b"))
                grad.setColorAt(1.0, QColor("#ffb26b"))
            else:
                c1 = QColor(self._accent)
                c2 = QColor(self._accent)
                c2.setAlpha(160)
                grad.setColorAt(0.0, c1)
                grad.setColorAt(1.0, c2)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(rect_fg, bar_h / 2, bar_h / 2)


class StatusDot(QWidget):
    """Пульсирующая точка-индикатор здоровья системы."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#00ff99")
        self._pulse = 0.0
        self.setFixedSize(12, 12)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def _tick(self) -> None:
        self._pulse = (self._pulse + 0.06) % (2 * 3.14159)
        self.update()

    def paintEvent(self, _event):
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        alpha = int(80 + 80 * (0.5 + 0.5 * math.sin(self._pulse)))
        halo = QColor(self._color)
        halo.setAlpha(alpha)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(0, 0, w, h)

        core = QColor(self._color)
        painter.setBrush(core)
        painter.drawEllipse(3, 3, w - 6, h - 6)


# ==========================================================
#               ДИАЛОГ НАСТРОЕК (CONTROL CENTER)
# ==========================================================
class ModernSettings(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Phantom Control Center")
        self.setMinimumSize(560, 520)
        self.config = current_config
        self.parent_overlay = parent

        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))

        self._build_ui()
        self._apply_styles()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(18, 16, 18, 16)
        self.main_layout.setSpacing(12)

        title = QLabel("⚙  Phantom Control Center")
        title.setStyleSheet(
            f"font-size: 17px; font-weight: 800; color: {self.config['accent_color']};"
        )
        subtitle = QLabel(f"v{APP_VERSION}")
        subtitle.setStyleSheet("color: #8891b0; font-size: 11px;")

        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(title)
        head.addWidget(subtitle)
        self.main_layout.addLayout(head)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs, 1)

        self._build_tab_general()
        self._build_tab_design()
        self._build_tab_games()
        self._build_tab_about()

        # нижняя панель с кнопкой Закрыть
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.btn_close = QPushButton("✔  Готово")
        self.btn_close.setMinimumHeight(36)
        self.btn_close.clicked.connect(self.accept)
        bottom.addWidget(self.btn_close)
        self.main_layout.addLayout(bottom)

    def _build_tab_general(self) -> None:
        tab = QWidget()
        lay = QFormLayout(tab)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        # Хоткей — сохраняем по потере фокуса / Enter, а не на каждый символ
        self.input_hotkey = QLineEdit(self.config.get("hotkey_toggle", "ctrl+shift+p"))
        self.input_hotkey.editingFinished.connect(self._commit_hotkey)
        lay.addRow("Хоткей (скрыть/показать):", self.input_hotkey)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(250, 5000)
        self.spin_interval.setSingleStep(100)
        self.spin_interval.setSuffix(" мс")
        self.spin_interval.setValue(int(self.config.get("update_interval_ms", 1000)))
        self.spin_interval.valueChanged.connect(self._commit_interval)
        lay.addRow("Интервал обновления:", self.spin_interval)

        self.cb_smart = QCheckBox("Показывать только в играх (Smart Focus)")
        self.cb_smart.setChecked(bool(self.config.get("smart_hide", False)))
        self.cb_smart.stateChanged.connect(lambda s: self._commit_bool("smart_hide", s))
        lay.addRow("Поведение:", self.cb_smart)

        self.cb_ai = QCheckBox("Текстовый AI ассистент")
        self.cb_ai.setChecked(bool(self.config.get("show_ai", True)))
        self.cb_ai.stateChanged.connect(lambda s: self._commit_bool("show_ai", s))
        lay.addRow("Интерфейс:", self.cb_ai)

        self.cb_voice = QCheckBox("Голосовое предупреждение о перегреве")
        self.cb_voice.setChecked(bool(self.config.get("enable_voice", True)))
        self.cb_voice.stateChanged.connect(lambda s: self._commit_bool("enable_voice", s))
        lay.addRow("Звук:", self.cb_voice)

        self.cb_taskbar = QCheckBox("Показывать значок на панели задач")
        self.cb_taskbar.setChecked(bool(self.config.get("show_in_taskbar", False)))
        self.cb_taskbar.stateChanged.connect(self._commit_taskbar)
        lay.addRow("Система:", self.cb_taskbar)

        self.tabs.addTab(tab, "⚙  Общие")

    def _build_tab_design(self) -> None:
        tab = QWidget()
        lay = QFormLayout(tab)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(60, 255)
        self.slider_opacity.setValue(int(self.config.get("opacity", 200)))
        self.slider_opacity.valueChanged.connect(self._commit_opacity_live)
        self.slider_opacity.sliderReleased.connect(lambda: save_config(self.config))
        lay.addRow("Прозрачность панели:", self.slider_opacity)

        # акцентный цвет
        self.accent_swatch = QPushButton()
        self.accent_swatch.setFixedHeight(28)
        self._refresh_accent_swatch()
        self.accent_swatch.clicked.connect(self._pick_accent)
        lay.addRow("Акцентный цвет:", self.accent_swatch)

        self.cb_spark = QCheckBox("Показывать мини-графики (sparklines)")
        self.cb_spark.setChecked(bool(self.config.get("show_sparklines", True)))
        self.cb_spark.stateChanged.connect(lambda s: self._commit_bool("show_sparklines", s))
        lay.addRow("Графики:", self.cb_spark)

        self.cb_net = QCheckBox("Показывать скорость сети (↑/↓)")
        self.cb_net.setChecked(bool(self.config.get("show_network_rate", True)))
        self.cb_net.stateChanged.connect(lambda s: self._commit_bool("show_network_rate", s))
        lay.addRow("Сеть:", self.cb_net)

        self.cb_compact = QCheckBox("Компактный режим (узкая панель)")
        self.cb_compact.setChecked(bool(self.config.get("compact_mode", False)))
        self.cb_compact.stateChanged.connect(lambda s: self._commit_bool("compact_mode", s))
        lay.addRow("Раскладка:", self.cb_compact)

        btn_layout = QHBoxLayout()
        self.btn_bg = QPushButton("🖼  Выбрать фон")
        self.btn_bg.setMinimumHeight(34)
        self.btn_bg.clicked.connect(self._choose_background)
        self.btn_clear_bg = QPushButton("✖  Сбросить")
        self.btn_clear_bg.setMinimumHeight(34)
        self.btn_clear_bg.clicked.connect(self._clear_background)
        btn_layout.addWidget(self.btn_bg)
        btn_layout.addWidget(self.btn_clear_bg)
        lay.addRow("Обои окна:", btn_layout)

        self.tabs.addTab(tab, "🎨  Дизайн")

    def _build_tab_games(self) -> None:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        hint = QLabel(
            "Smart Focus показывает оверлей только когда активное окно "
            "содержит одну из этих строк. Регистр не важен."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8891b0; font-size: 11px;")
        lay.addWidget(hint)

        self.games_list = QListWidget()
        for g in self.config.get("target_games", []):
            self.games_list.addItem(QListWidgetItem(g))
        lay.addWidget(self.games_list, 1)

        row = QHBoxLayout()
        self.games_input = QLineEdit()
        self.games_input.setPlaceholderText("Название или часть названия игры…")
        self.games_input.returnPressed.connect(self._add_game)
        btn_add = QPushButton("➕  Добавить")
        btn_add.clicked.connect(self._add_game)
        btn_rm = QPushButton("🗑  Удалить")
        btn_rm.clicked.connect(self._remove_game)
        row.addWidget(self.games_input, 1)
        row.addWidget(btn_add)
        row.addWidget(btn_rm)
        lay.addLayout(row)

        self.tabs.addTab(tab, "🎮  Игры")

    def _build_tab_about(self) -> None:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        title = QLabel("👻 Phantom Overlay")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {self.config['accent_color']};"
        )
        version = QLabel(f"Версия: {APP_VERSION}")
        version.setStyleSheet("color: #a8b2d1; font-size: 12px;")

        info = QTextEdit()
        info.setReadOnly(True)
        info.setFrameStyle(QFrame.Shape.NoFrame)
        info.setHtml(
            """
            <p style="color:#a8b2d1;font-family:'Segoe UI';font-size:12px;line-height:1.55;">
            <b>Phantom Overlay</b> — лёгкий внутриигровой оверлей с мониторингом
            железа, AI-ассистентом Silphiette, Discord Rich Presence и контролем
            медиа. Этот релиз — «Polished Edition» с кастомными градиентными
            прогресс-барами, мини-графиками истории, настраиваемым акцентным
            цветом и редактируемым списком игр.
            </p>
            <p style="color:#8891b0;font-family:'Segoe UI';font-size:11px;">
            Горячая клавиша по умолчанию: <b>Ctrl + Shift + P</b>. Настройки
            сохраняются автоматически в <code>phantom_config.json</code>.
            </p>
            <p style="color:#8891b0;font-family:'Segoe UI';font-size:11px;">
            Сделано с любовью на PyQt6. Лицензия MIT.
            </p>
            """
        )

        lay.addWidget(title)
        lay.addWidget(version)
        lay.addSpacing(6)
        lay.addWidget(info, 1)

        self.tabs.addTab(tab, "ℹ️  О программе")

    # ---------- handlers ----------
    def _refresh_accent_swatch(self) -> None:
        c = self.config.get("accent_color", "#00ff99")
        self.accent_swatch.setText(f"  {c.upper()}")
        self.accent_swatch.setStyleSheet(
            f"QPushButton {{ background-color: {c}; color: #0d0d12; "
            f"font-weight: 800; border: 1px solid rgba(255,255,255,40); border-radius: 6px; }}"
            f"QPushButton:hover {{ border: 1px solid rgba(255,255,255,90); }}"
        )

    def _pick_accent(self) -> None:
        initial = QColor(self.config.get("accent_color", "#00ff99"))
        color = QColorDialog.getColor(initial, self, "Выберите акцентный цвет")
        if color.isValid():
            self.config["accent_color"] = color.name()
            save_config(self.config)
            self._refresh_accent_swatch()
            if self.parent_overlay:
                self.parent_overlay.apply_config()

    def _commit_opacity_live(self, val: int) -> None:
        self.config["opacity"] = int(val)
        if self.parent_overlay:
            self.parent_overlay.apply_config()

    def _commit_interval(self, val: int) -> None:
        self.config["update_interval_ms"] = int(val)
        save_config(self.config)
        if self.parent_overlay:
            self.parent_overlay.apply_interval()

    def _commit_hotkey(self) -> None:
        text = self.input_hotkey.text().strip()
        if not text:
            return
        self.config["hotkey_toggle"] = text
        save_config(self.config)
        if self.parent_overlay:
            self.parent_overlay.register_hotkey()

    def _commit_bool(self, key: str, state: int) -> None:
        self.config[key] = bool(state)
        save_config(self.config)
        if self.parent_overlay:
            self.parent_overlay.apply_config()

    def _commit_taskbar(self, state: int) -> None:
        self.config["show_in_taskbar"] = bool(state)
        save_config(self.config)
        if self.parent_overlay:
            self.parent_overlay.apply_window_flags()

    def _choose_background(self) -> None:
        fname, _ = QFileDialog.getOpenFileName(
            self, "Выбрать фон", "", "Images (*.png *.jpg *.jpeg)"
        )
        if fname:
            self.config["bg_image"] = fname
            save_config(self.config)
            if self.parent_overlay:
                self.parent_overlay.apply_config()

    def _clear_background(self) -> None:
        self.config["bg_image"] = ""
        save_config(self.config)
        if self.parent_overlay:
            self.parent_overlay.apply_config()

    def _add_game(self) -> None:
        name = self.games_input.text().strip()
        if not name:
            return
        self.games_input.clear()
        self.games_list.addItem(QListWidgetItem(name))
        self._commit_games()

    def _remove_game(self) -> None:
        for item in self.games_list.selectedItems():
            self.games_list.takeItem(self.games_list.row(item))
        self._commit_games()

    def _commit_games(self) -> None:
        games = [self.games_list.item(i).text() for i in range(self.games_list.count())]
        self.config["target_games"] = games
        save_config(self.config)

    # ---------- styles ----------
    def _apply_styles(self) -> None:
        accent = self.config.get("accent_color", "#00ff99")
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: #0d0d12;
                border: 1px solid #1f1f27;
                border-radius: 12px;
            }}
            QLabel {{
                color: #a8b2d1;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: 600;
            }}
            QLineEdit, QSpinBox {{
                background-color: #1a1a24;
                color: {accent};
                border: 1px solid #1f1f27;
                border-radius: 6px;
                padding: 6px 8px;
                font-family: 'Segoe UI';
                font-weight: 700;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 1px solid {accent};
            }}
            QTabWidget::pane {{
                border: 1px solid #1f1f27;
                background: #121217;
                border-radius: 10px;
            }}
            QTabBar::tab {{
                background: #1a1a24;
                color: #a8b2d1;
                padding: 8px 18px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 700;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: #121217;
                color: {accent};
                border-bottom: 2px solid {accent};
            }}
            QSlider::groove:horizontal {{
                border-radius: 4px;
                height: 8px;
                background: #1f1f27;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: #ffffff;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
                border: 2px solid {accent};
            }}
            QPushButton {{
                background-color: #1a1a24;
                color: {accent};
                border: 1px solid {accent};
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 700;
                font-family: 'Segoe UI';
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: #0d0d12;
            }}
            QCheckBox {{
                color: #e6e9f2;
                font-family: 'Segoe UI';
                font-size: 13px;
                spacing: 10px;
            }}
            QCheckBox::indicator {{
                width: 38px;
                height: 20px;
                border-radius: 10px;
                background-color: #1f1f27;
                border: 1px solid #333;
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent};
                border: 1px solid {accent};
            }}
            QListWidget {{
                background-color: #1a1a24;
                color: #e6e9f2;
                border: 1px solid #1f1f27;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background: {accent};
                color: #0d0d12;
                font-weight: 800;
            }}
            QTextEdit {{
                background: transparent;
                border: none;
            }}
            """
        )


# ==========================================================
#                   ГЛАВНЫЙ ОВЕРЛЕЙ
# ==========================================================
class PhantomOverlay(QMainWindow):
    toggle_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.core = PhantomCore()
        self.is_locked = True
        self.manual_hidden = False
        self.dragPos = QPoint()
        self.current_hotkey = None
        self._start_time = time.time()
        self._prev_ai_text = ""

        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))

        self.apply_window_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._build_ui()

        self.move(self.config.get("pos_x", 100), self.config.get("pos_y", 100))
        self.setup_tray()
        self.apply_config()

        self.toggle_signal.connect(self.do_toggle_visibility)
        self.register_hotkey()

        # аптайм-таймер (раз в секунду)
        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._refresh_uptime)
        self._uptime_timer.start(1000)

        self.fade_in_anim()

        self.monitor_thread = HardwareMonitorThread(
            interval_ms=int(self.config.get("update_interval_ms", 1000))
        )
        self.monitor_thread.data_updated.connect(self.update_ui)
        self.monitor_thread.start()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setObjectName("glass_panel")

        root = QVBoxLayout(self.central_widget)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(6)

        # ---- header ----
        header = QHBoxLayout()
        header.setSpacing(8)

        self.status_dot = StatusDot()
        self.lbl_title = QLabel("Phantom")
        self.lbl_title.setStyleSheet(
            "color: #ffffff; font-family: 'Segoe UI'; font-size: 14px; "
            "font-weight: 800; letter-spacing: 0.5px;"
        )
        self.lbl_uptime = QLabel("00:00")
        self.lbl_uptime.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_uptime.setStyleSheet(
            "color: #8891b0; font-family: 'Segoe UI'; font-size: 11px; font-weight: 600;"
        )
        header.addWidget(self.status_dot)
        header.addWidget(self.lbl_title)
        header.addStretch(1)
        header.addWidget(self.lbl_uptime)
        root.addLayout(header)

        # разделитель
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        self.sep.setFixedHeight(1)
        self.sep.setStyleSheet("background: rgba(255,255,255,25); border: none;")
        root.addWidget(self.sep)

        # ---- метрики ----
        accent = self.config.get("accent_color", "#00ff99")
        show_spark = bool(self.config.get("show_sparklines", True))

        self.bar_gpu = MetricBar("🎮", "GPU", accent=accent, show_sparkline=show_spark)
        self.bar_cpu = MetricBar("🧠", "CPU", accent=accent, show_sparkline=show_spark)
        self.bar_ram = MetricBar("💾", "RAM", accent=accent, show_sparkline=show_spark)

        root.addWidget(self.bar_gpu)
        root.addWidget(self.bar_cpu)
        root.addWidget(self.bar_ram)

        # ping + net row
        self.lbl_ping = QLabel("🌐 PING: -- ms")
        self.lbl_ping.setStyleSheet(self._text_style())
        root.addWidget(self.lbl_ping)

        self.lbl_net = QLabel("↑ 0.0 KB/s    ↓ 0.0 KB/s")
        self.lbl_net.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 11px; color: #8891b0; font-weight: 600;"
        )
        root.addWidget(self.lbl_net)

        self.lbl_music = QLabel("🎵 Ожидание медиа…")
        self.lbl_music.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 11px; color: #a8b2d1; font-weight: 500;"
        )
        self.lbl_music.setWordWrap(False)
        root.addWidget(self.lbl_music)

        self.lbl_ai = QLabel("🤖 Silphiette: работаю…")
        self.lbl_ai.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 11px; color: #ffcc66; "
            "font-style: italic; font-weight: 500;"
        )
        root.addWidget(self.lbl_ai)

        # тень вокруг панели
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(38)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.central_widget.setGraphicsEffect(shadow)

        self._resize_for_mode()

    def _text_style(self) -> str:
        return (
            "font-family: 'Segoe UI'; font-size: 12px; font-weight: 600; "
            "color: rgba(255, 255, 255, 220);"
        )

    def _resize_for_mode(self) -> None:
        if self.config.get("compact_mode", False):
            self.resize(230, 240)
        else:
            self.resize(280, 270)

    # ---------- hotkey ----------
    def register_hotkey(self):
        try:
            if self.current_hotkey:
                try:
                    keyboard.remove_hotkey(self.current_hotkey)
                except Exception as e:
                    log_err("hotkey.remove", e)
            self.current_hotkey = self.config.get("hotkey_toggle", "ctrl+shift+p")
            if self.current_hotkey:
                keyboard.add_hotkey(self.current_hotkey, lambda: self.toggle_signal.emit())
        except Exception as e:
            log_err("hotkey.add", e)

    # ---------- window flags ----------
    def apply_window_flags(self):
        base_flags = (
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint
        )
        if not self.config.get("show_in_taskbar", False):
            base_flags |= Qt.WindowType.Tool
        else:
            base_flags |= Qt.WindowType.Window

        self.setWindowFlags(base_flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.is_locked)

        if self.isVisible():
            self.hide()
            self.show()

    # ---------- animations ----------
    def fade_in_anim(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(600)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(max(0.1, self.config["opacity"] / 255.0))
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.start()

    def do_toggle_visibility(self):
        self.manual_hidden = not self.manual_hidden
        if not self.manual_hidden:
            self.show()
            self.fade_in_anim()
        else:
            self.hide()

    # ---------- config ----------
    def apply_interval(self) -> None:
        try:
            self.monitor_thread.set_interval_ms(int(self.config.get("update_interval_ms", 1000)))
        except Exception as e:
            log_err("interval.apply", e)

    def apply_config(self):
        # прозрачность — если не идёт fade-in
        if not hasattr(self, "anim") or self.anim.state() != QPropertyAnimation.State.Running:
            self.setWindowOpacity(max(0.1, self.config["opacity"] / 255.0))

        accent = self.config.get("accent_color", "#00ff99")
        show_spark = bool(self.config.get("show_sparklines", True))

        self.bar_gpu.set_accent(accent)
        self.bar_cpu.set_accent(accent)
        self.bar_ram.set_accent(accent)
        self.bar_gpu.set_sparkline_visible(show_spark)
        self.bar_cpu.set_sparkline_visible(show_spark)
        self.bar_ram.set_sparkline_visible(show_spark)

        self.lbl_net.setVisible(bool(self.config.get("show_network_rate", True)))
        self.lbl_ai.setVisible(bool(self.config.get("show_ai", True)))

        border = "1px solid rgba(255, 255, 255, 30)"
        bg_style = (
            "background-color: qlineargradient(x1:0,y1:0,x2:0,y2:1, "
            "stop:0 rgba(22,22,30,255), stop:1 rgba(14,14,18,255));"
        )

        if self.config["bg_image"] and os.path.exists(self.config["bg_image"]):
            path = self.config["bg_image"].replace("\\", "/")
            bg_style = f"border-image: url('{path}') 0 0 0 0 stretch stretch;"
            border = "none"

        if not self.is_locked:
            border = f"2px dashed {accent}"
            bg_style = "background-color: rgba(15, 15, 20, 220);"

        self.setStyleSheet(
            f"QWidget#glass_panel {{ {bg_style} border: {border}; border-radius: 16px; }}"
        )

        self._resize_for_mode()

    # ---------- drag ----------
    def mousePressEvent(self, event):
        if not self.is_locked and event.button() == Qt.MouseButton.LeftButton:
            self.dragPos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.is_locked and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.dragPos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if not self.is_locked and event.button() == Qt.MouseButton.LeftButton:
            self.config["pos_x"], self.config["pos_y"] = self.x(), self.y()
            save_config(self.config)

    # ---------- tray ----------
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists("icon.png"):
            self.tray_icon.setIcon(QIcon("icon.png"))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        self.tray_menu = QMenu()
        accent = self.config.get("accent_color", "#00ff99")
        self.tray_menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: #0d0d12; color: #ffffff;
                border: 1px solid #1f1f27; border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 7px 24px; border-radius: 4px; margin: 2px 4px;
                font-family: 'Segoe UI'; font-weight: 600;
            }}
            QMenu::item:selected {{ background-color: {accent}; color: #0d0d12; font-weight: 800; }}
            QMenu::separator {{ height: 1px; background: #1f1f27; margin: 4px 10px; }}
            """
        )

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

        music_next = QAction("⏭ Следующий трек", self)
        music_next.triggered.connect(lambda: self._safe_media_key("next track"))
        self.tray_menu.addAction(music_next)

        music_prev = QAction("⏮ Предыдущий трек", self)
        music_prev.triggered.connect(lambda: self._safe_media_key("previous track"))
        self.tray_menu.addAction(music_prev)

        self.tray_menu.addSeparator()
        self.tray_menu.addAction(QAction("⚙ Настройки", self, triggered=self.open_settings))
        self.tray_menu.addAction(QAction("❌ Выход", self, triggered=self._quit_app))

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason) -> None:
        # двойной клик по трею → toggle
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
                self.monitor_thread.stop()
                self.monitor_thread.wait(2000)
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
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        if h:
            self.lbl_uptime.setText(f"⏱ {h:02d}:{m:02d}:{s:02d}")
        else:
            self.lbl_uptime.setText(f"⏱ {m:02d}:{s:02d}")

    # ---------- data ----------
    def update_ui(self, data):
        accent = self.config.get("accent_color", "#00ff99")

        # ----- GPU -----
        gpu_temp = data.get("gpu_temp")
        gpu_util = data.get("gpu_util")

        if isinstance(gpu_temp, int) and isinstance(gpu_util, int):
            critical = gpu_temp > 82
            self.bar_gpu.set_value(
                gpu_util, f"{gpu_temp}°C · {gpu_util}%", critical=critical
            )
            # цвет статус-точки
            if gpu_temp > 82:
                self.status_dot.set_color("#ff5c5c")
                if self.config.get("enable_voice", True):
                    self.core.say("Внимание! Видеокарта перегревается.")
            elif gpu_temp > 75:
                self.status_dot.set_color("#ffcc66")
            else:
                self.status_dot.set_color(accent)
        else:
            self.bar_gpu.set_value(0, "N/A", critical=False)
            self.status_dot.set_color(accent)

        # ----- CPU -----
        cpu = float(data.get("cpu", 0) or 0)
        self.bar_cpu.set_value(cpu, f"{cpu:.0f}%", critical=cpu >= 95)

        # ----- RAM -----
        ram = float(data.get("ram", 0) or 0)
        self.bar_ram.set_value(ram, f"{ram:.0f}%", critical=ram >= 92)

        # ----- PING -----
        ping_val = data.get("ping")
        if ping_val is None:
            self.lbl_ping.setText("🌐 PING: — ms")
            self.lbl_ping.setStyleSheet(self._text_style())
        else:
            color = accent
            if ping_val > 120:
                color = "#ff5c5c"
            elif ping_val > 60:
                color = "#ffcc66"
            self.lbl_ping.setText(f"🌐 PING: {ping_val} ms")
            self.lbl_ping.setStyleSheet(
                f"font-family: 'Segoe UI'; font-size: 12px; font-weight: 700; color: {color};"
            )

        # ----- NET -----
        up = float(data.get("net_up", 0.0) or 0.0)
        down = float(data.get("net_down", 0.0) or 0.0)
        self.lbl_net.setText(f"↑ {up:6.1f} KB/s    ↓ {down:6.1f} KB/s")

        # ----- MUSIC -----
        music = data.get("music", "") or ""
        self.lbl_music.setText(music[:42] + "…" if len(music) > 42 else music)

        # ----- AI STATUS -----
        if self.config.get("show_ai", True):
            ai_text = self._compose_ai_status(gpu_temp, cpu, ram, ping_val)
            if ai_text != self._prev_ai_text:
                self._prev_ai_text = ai_text
                self.lbl_ai.setText(ai_text)

        # ----- DISCORD -----
        try:
            temp_str = f"{gpu_temp}°C" if isinstance(gpu_temp, int) else "N/A"
            self.core.update_discord(
                state=f"GPU: {temp_str}", details=(music[:35] or "—")
            )
        except Exception as e:
            log_err("discord.update.ui", e)

        # ----- SMART FOCUS -----
        if (
            self.config.get("smart_hide", False)
            and self.is_locked
            and not self.manual_hidden
        ):
            active = (data.get("active_title") or "").lower()
            games = [g.lower() for g in self.config.get("target_games", []) if g]
            is_gaming = any(g in active for g in games)
            self.setVisible(is_gaming)

    def _compose_ai_status(self, gpu_temp, cpu, ram, ping_val) -> str:
        if isinstance(gpu_temp, int) and gpu_temp > 82:
            return "🤖 Silphiette: перегрев GPU! Снизь нагрузку."
        if cpu >= 95:
            return "🤖 Silphiette: CPU на 100% — фоновые задачи?"
        if ram >= 92:
            return "🤖 Silphiette: память почти закончилась."
        if isinstance(ping_val, int) and ping_val > 150:
            return "🤖 Silphiette: сеть не в форме — высокий пинг."
        return "🤖 Silphiette: система в норме."

    # ---------- shutdown ----------
    def closeEvent(self, event):
        try:
            if hasattr(self, "monitor_thread"):
                self.monitor_thread.stop()
                self.monitor_thread.wait(2000)
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
    overlay = PhantomOverlay()
    overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    overlay.show()
    sys.exit(app.exec())
