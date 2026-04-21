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
    QFrame, QTextEdit, QStackedWidget, QToolButton
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QPoint, QPointF, QPropertyAnimation, QEasingCurve,
    QRectF, QTimer, pyqtProperty
)
from PyQt6.QtGui import (
    QAction, QIcon, QColor, QPainter, QLinearGradient, QRadialGradient,
    QPen, QBrush, QPainterPath, QFont, QPixmap, QImage
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

APP_VERSION = "4.2.0 — Premium Edition"

DEFAULT_CONFIG = {
    "opacity": 235,
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
#               ПАЛИТРА / УТИЛЬНЫЕ ФУНКЦИИ
# ==========================================================
def _mix(c1: QColor, c2: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red()   * (1 - t) + c2.red()   * t),
        int(c1.green() * (1 - t) + c2.green() * t),
        int(c1.blue()  * (1 - t) + c2.blue()  * t),
        int(c1.alpha() * (1 - t) + c2.alpha() * t),
    )


def _color_for_load(percent: float, accent: QColor) -> QColor:
    """Градиентный цвет по загрузке: accent → yellow → red."""
    yellow = QColor("#ffcc66")
    red = QColor("#ff5c5c")
    if percent < 70:
        return _mix(accent, yellow, (percent / 70.0) * 0.35)
    if percent < 90:
        return _mix(yellow, red, (percent - 70) / 20.0)
    return red


def _color_for_temp(temp: int, accent: QColor) -> QColor:
    if temp <= 55:
        return accent
    if temp <= 75:
        return _mix(accent, QColor("#ffcc66"), (temp - 55) / 20.0)
    if temp <= 85:
        return _mix(QColor("#ffcc66"), QColor("#ff5c5c"), (temp - 75) / 10.0)
    return QColor("#ff5c5c")


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

            try:
                data["cpu"] = psutil.cpu_percent()
                data["ram"] = psutil.virtual_memory().percent
            except Exception as e:
                log_err("psutil", e)
                data["cpu"] = random.randint(18, 25)
                data["ram"] = random.randint(45, 50)

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

            try:
                p = ping("8.8.8.8", timeout=1)
                data["ping"] = int(p * 1000) if p else None
            except Exception as e:
                log_err("ping", e)
                data["ping"] = None

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

            try:
                data["music"] = self.loop.run_until_complete(self.get_music_info())
            except Exception as e:
                log_err("media", e)
                data["music"] = "No Media"

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
            return "Media API unavailable"
        try:
            sessions = await SessionManager.request_async()
            curr = sessions.get_current_session()
            if curr:
                info = await curr.try_get_media_properties_async()
                return f"{info.artist or 'Unknown'} — {info.title or 'Track'}"
            return "⏸ Тишина"
        except Exception as e:
            log_err("winsdk.media", e)
            return "No Media"


# ==========================================================
#                   ПРЕМИУМ ВИДЖЕТЫ
# ==========================================================
class Sparkline(QWidget):
    """Мини-график с мягкой заливкой и сглаживанием."""

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

        w = self.width()
        h = self.height()
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

        # gradient-filled area under curve
        fill_path = QPainterPath()
        fill_path.moveTo(pts[0].x(), h)
        fill_path.lineTo(pts[0])
        for p in pts[1:]:
            fill_path.lineTo(p)
        fill_path.lineTo(pts[-1].x(), h)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        c1 = QColor(self._color); c1.setAlpha(130)
        c2 = QColor(self._color); c2.setAlpha(0)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        painter.fillPath(fill_path, QBrush(grad))

        # line
        line_path = QPainterPath()
        line_path.moveTo(pts[0])
        for p in pts[1:]:
            line_path.lineTo(p)
        pen = QPen(self._color)
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(line_path)


class MetricCard(QWidget):
    """Премиум-карточка с иконкой, именем метрики, большим числом, gradient-прогрессом и sparkline."""

    def __init__(self, icon: str, name: str, unit: str = "%",
                 accent: str = "#00ff99", show_sparkline: bool = True, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._name = name
        self._unit = unit
        self._accent = QColor(accent)
        self._value_anim = 0.0      # animated percent for bar fill
        self._value_target = 0.0
        self._value_text = "--"
        self._secondary_text = ""
        self._critical = False

        self._anim = QPropertyAnimation(self, b"animatedValue")
        self._anim.setDuration(450)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._build_ui(show_sparkline)

    # ---------- animated property ----------
    def get_animated_value(self) -> float:
        return self._value_anim

    def set_animated_value(self, v: float) -> None:
        self._value_anim = max(0.0, min(100.0, float(v)))
        self.update()

    animatedValue = pyqtProperty(float, fget=get_animated_value, fset=set_animated_value)

    # ---------- ui ----------
    def _build_ui(self, show_sparkline: bool) -> None:
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(4)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)

        self.lbl_icon = QLabel(self._icon)
        self.lbl_icon.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 14px;"
        )
        self.lbl_name = QLabel(self._name)
        self.lbl_name.setStyleSheet(
            "color: rgba(255,255,255,170); font-family: 'Segoe UI'; "
            "font-size: 10px; font-weight: 800; letter-spacing: 1.8px;"
        )
        self.lbl_value = QLabel("--")
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        font = QFont("Segoe UI", 15)
        font.setWeight(QFont.Weight.Black)
        self.lbl_value.setFont(font)
        self.lbl_value.setStyleSheet(f"color: {self._accent.name()};")

        self.lbl_secondary = QLabel("")
        self.lbl_secondary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_secondary.setStyleSheet(
            "color: rgba(255,255,255,120); font-family: 'Segoe UI'; "
            "font-size: 10px; font-weight: 600;"
        )

        left_box = QVBoxLayout()
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(0)
        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(6)
        name_row.addWidget(self.lbl_icon)
        name_row.addWidget(self.lbl_name)
        name_row.addStretch(1)
        left_box.addLayout(name_row)
        left_box.addWidget(self.lbl_secondary)

        right_box = QVBoxLayout()
        right_box.setContentsMargins(0, 0, 0, 0)
        right_box.setSpacing(0)
        right_box.addStretch(1)
        right_box.addWidget(self.lbl_value)

        top.addLayout(left_box, 1)
        top.addLayout(right_box, 0)
        root.addLayout(top)

        self.sparkline = Sparkline(color=self._accent.name())
        self.sparkline.setVisible(show_sparkline)
        root.addWidget(self.sparkline)

    # ---------- api ----------
    def set_accent(self, color: str) -> None:
        self._accent = QColor(color)
        self.sparkline.set_color(color)
        self._refresh_value_style()
        self.update()

    def set_sparkline_visible(self, visible: bool) -> None:
        self.sparkline.setVisible(visible)

    def set_value(self, percent: float, text: str, secondary: str = "",
                  critical: bool = False) -> None:
        try:
            self._value_target = max(0.0, min(100.0, float(percent)))
        except (TypeError, ValueError):
            self._value_target = 0.0
        self._value_text = text
        self._secondary_text = secondary
        self._critical = bool(critical)

        self.lbl_value.setText(text)
        self.lbl_secondary.setText(secondary)
        self._refresh_value_style()
        self.sparkline.push(self._value_target)

        self._anim.stop()
        self._anim.setStartValue(self._value_anim)
        self._anim.setEndValue(self._value_target)
        self._anim.start()

    def _refresh_value_style(self) -> None:
        color = _color_for_load(self._value_target, self._accent)
        if self._critical:
            color = QColor("#ff5c5c")
        self.lbl_value.setStyleSheet(f"color: {color.name()};")

    # ---------- paint ----------
    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = 12.0

        # ---- card bg ----
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor(30, 30, 40, 235))
        bg.setColorAt(1.0, QColor(18, 18, 26, 235))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # ---- 1px inner highlight (top) ----
        hi = QPen(QColor(255, 255, 255, 22))
        hi.setWidthF(1.0)
        painter.setPen(hi)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)

        # ---- progress track ----
        track_h = 4.0
        track_y = h - track_h - 8  # above sparkline space; we'll draw track inside bottom area under values
        track_rect = QRectF(14, h - 4 - 0, w - 28, 0)  # placeholder unused
        # better: put slim track near bottom-card edge, just above sparkline area
        spark_h = 22.0 if self.sparkline.isVisible() else 0.0
        track_y = h - spark_h - 10
        track_rect = QRectF(14, track_y, w - 28, track_h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.drawRoundedRect(track_rect, track_h / 2, track_h / 2)

        # filled portion
        filled_w = (self._value_anim / 100.0) * (w - 28)
        if filled_w > 1.0:
            fill_rect = QRectF(14, track_y, filled_w, track_h)
            fg_color = _color_for_load(self._value_anim, self._accent)
            if self._critical:
                fg_color = QColor("#ff5c5c")
            glow_grad = QLinearGradient(14, 0, 14 + filled_w, 0)
            c_start = QColor(fg_color); c_start.setAlpha(230)
            c_end = QColor(fg_color); c_end.setAlpha(255)
            glow_grad.setColorAt(0.0, c_start)
            glow_grad.setColorAt(1.0, c_end)
            painter.setBrush(QBrush(glow_grad))
            painter.drawRoundedRect(fill_rect, track_h / 2, track_h / 2)

            # subtle accent glow dot at end
            dot_r = 5.0
            dot = QRadialGradient(14 + filled_w, track_y + track_h / 2, dot_r * 2)
            g_in = QColor(fg_color); g_in.setAlpha(200)
            g_out = QColor(fg_color); g_out.setAlpha(0)
            dot.setColorAt(0.0, g_in)
            dot.setColorAt(1.0, g_out)
            painter.setBrush(QBrush(dot))
            painter.drawEllipse(QPointF(14 + filled_w, track_y + track_h / 2),
                                dot_r * 2, dot_r * 2)


class CircularGauge(QWidget):
    """Круговой индикатор: внешнее кольцо + температура в центре + подпись."""

    def __init__(self, accent: str = "#00ff99", parent=None):
        super().__init__(parent)
        self._accent = QColor(accent)
        self._temp = 0
        self._util = 0
        self._anim_util = 0.0
        self._available = False
        self.setFixedSize(96, 96)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._anim = QPropertyAnimation(self, b"animatedUtil")
        self._anim.setDuration(450)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_animated_util(self) -> float:
        return self._anim_util

    def set_animated_util(self, v: float) -> None:
        self._anim_util = max(0.0, min(100.0, float(v)))
        self.update()

    animatedUtil = pyqtProperty(float, fget=get_animated_util, fset=set_animated_util)

    def set_accent(self, color: str) -> None:
        self._accent = QColor(color)
        self.update()

    def set_values(self, temp, util) -> None:
        if temp is None or util is None:
            self._available = False
            self.update()
            return
        self._available = True
        self._temp = int(temp)
        new_util = int(util)
        self._anim.stop()
        self._anim.setStartValue(self._anim_util)
        self._anim.setEndValue(float(new_util))
        self._anim.start()
        self._util = new_util

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(w, h) / 2.0 - 6.0

        # background ring
        track_pen = QPen(QColor(255, 255, 255, 32))
        track_pen.setWidth(6)
        track_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        color = _color_for_temp(self._temp if self._available else 40, self._accent)

        # glow behind arc
        glow = QRadialGradient(cx, cy, radius + 8)
        g1 = QColor(color); g1.setAlpha(0)
        g2 = QColor(color); g2.setAlpha(60)
        g3 = QColor(color); g3.setAlpha(0)
        glow.setColorAt(0.55, g1)
        glow.setColorAt(0.75, g2)
        glow.setColorAt(1.0, g3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPointF(cx, cy), radius + 8, radius + 8)

        # progress arc (top, clockwise)
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        arc_pen = QPen(color)
        arc_pen.setWidth(6)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Qt angles are 1/16 degrees; start at 90° (top), sweep clockwise negative
        start_angle = 90 * 16
        span = -int((self._anim_util / 100.0) * 360 * 16) if self._available else 0
        painter.drawArc(rect, start_angle, span)

        # center text — temperature
        painter.setPen(QColor(255, 255, 255, 240))
        font_big = QFont("Segoe UI", 18)
        font_big.setWeight(QFont.Weight.Black)
        painter.setFont(font_big)
        if self._available:
            txt = f"{self._temp}°"
        else:
            txt = "N/A"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)

        # label "GPU"
        painter.setPen(QColor(255, 255, 255, 130))
        font_lbl = QFont("Segoe UI", 8)
        font_lbl.setWeight(QFont.Weight.ExtraBold)
        font_lbl.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        painter.setFont(font_lbl)
        lbl_rect = QRectF(rect.left(), rect.bottom() - 26, rect.width(), 14)
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, "GPU")


class StatusDot(QWidget):
    """Пульсирующая точка-индикатор."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#00ff99")
        self._pulse = 0.0
        self.setFixedSize(14, 14)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def _tick(self) -> None:
        self._pulse = (self._pulse + 0.06) % (2 * math.pi)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        cx, cy = w / 2, h / 2

        # halo
        alpha = int(60 + 80 * (0.5 + 0.5 * math.sin(self._pulse)))
        halo_grad = QRadialGradient(cx, cy, w / 2)
        halo_in = QColor(self._color); halo_in.setAlpha(alpha)
        halo_out = QColor(self._color); halo_out.setAlpha(0)
        halo_grad.setColorAt(0.0, halo_in)
        halo_grad.setColorAt(1.0, halo_out)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo_grad))
        painter.drawEllipse(0, 0, w, h)

        # core
        core = QColor(self._color)
        painter.setBrush(core)
        painter.drawEllipse(int(w / 2 - 3), int(h / 2 - 3), 6, 6)


class IconButton(QToolButton):
    """Мини-кнопка в хедере."""

    def __init__(self, glyph: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setText(glyph)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoRaise(True)
        self.setFixedSize(22, 22)
        self.setStyleSheet(
            """
            QToolButton {
                color: rgba(255,255,255,160);
                background: rgba(255,255,255,10);
                border: 1px solid rgba(255,255,255,18);
                border-radius: 6px;
                font-family: 'Segoe UI'; font-weight: 800; font-size: 11px;
            }
            QToolButton:hover {
                color: #ffffff;
                background: rgba(255,255,255,28);
                border: 1px solid rgba(255,255,255,40);
            }
            QToolButton:pressed { background: rgba(255,255,255,48); }
            """
        )


class Marquee(QLabel):
    """Плавная бегущая строка для длинных треков."""

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
        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.setFont(self.font())
        text = self._full + "     " + self._full
        fm = self.fontMetrics()
        y = (self.height() + fm.ascent() - fm.descent()) // 2
        painter.drawText(-self._offset, y, text)


# ==========================================================
#          PREMIUM ДИАЛОГ НАСТРОЕК (SIDEBAR NAV)
# ==========================================================
class ModernSettings(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Phantom Control Center")
        self.setMinimumSize(720, 520)
        self.config = current_config
        self.parent_overlay = parent

        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))

        self._build_ui()
        self._apply_styles()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # sidebar
        side = QWidget()
        side.setObjectName("side")
        side.setFixedWidth(200)
        side_l = QVBoxLayout(side)
        side_l.setContentsMargins(18, 22, 14, 22)
        side_l.setSpacing(12)

        brand = QLabel("⚙  PHANTOM")
        brand.setStyleSheet(
            f"color: {self.config['accent_color']}; font-family: 'Segoe UI'; "
            "font-size: 14px; font-weight: 900; letter-spacing: 2.5px;"
        )
        subtitle = QLabel(f"v{APP_VERSION}")
        subtitle.setStyleSheet("color: #8891b0; font-size: 10px; letter-spacing: 0.8px;")

        side_l.addWidget(brand)
        side_l.addWidget(subtitle)
        side_l.addSpacing(10)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        for title in ["⚙   Общие", "🎨   Дизайн", "🎮   Игры", "ℹ   О программе"]:
            QListWidgetItem(title, self.nav)
        self.nav.setCurrentRow(0)
        side_l.addWidget(self.nav, 1)

        btn_close = QPushButton("✔  Готово")
        btn_close.setMinimumHeight(38)
        btn_close.setObjectName("done_btn")
        btn_close.clicked.connect(self.accept)
        side_l.addWidget(btn_close)

        # content
        self.stack = QStackedWidget()
        self.stack.setObjectName("stack")
        self._build_page_general()
        self._build_page_design()
        self._build_page_games()
        self._build_page_about()

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)

        root.addWidget(side)
        root.addWidget(self.stack, 1)

    def _page_scaffold(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(14)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            "color: #ffffff; font-family: 'Segoe UI'; font-size: 20px; "
            "font-weight: 900; letter-spacing: 0.6px;"
        )
        lay.addWidget(lbl)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,20); border: none;")
        lay.addWidget(sep)
        lay.addSpacing(4)
        return page, lay

    def _build_page_general(self) -> None:
        page, lay = self._page_scaffold("Общие настройки")

        form = QFormLayout()
        form.setSpacing(16)
        form.setContentsMargins(0, 0, 0, 0)

        self.input_hotkey = QLineEdit(self.config.get("hotkey_toggle", "ctrl+shift+p"))
        self.input_hotkey.editingFinished.connect(self._commit_hotkey)
        form.addRow("Хоткей (скрыть/показать):", self.input_hotkey)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(250, 5000)
        self.spin_interval.setSingleStep(100)
        self.spin_interval.setSuffix("  мс")
        self.spin_interval.setValue(int(self.config.get("update_interval_ms", 1000)))
        self.spin_interval.valueChanged.connect(self._commit_interval)
        form.addRow("Интервал обновления:", self.spin_interval)

        self.cb_smart = QCheckBox("Показывать только в играх (Smart Focus)")
        self.cb_smart.setChecked(bool(self.config.get("smart_hide", False)))
        self.cb_smart.stateChanged.connect(lambda s: self._commit_bool("smart_hide", s))
        form.addRow("Поведение:", self.cb_smart)

        self.cb_ai = QCheckBox("Текстовый AI ассистент")
        self.cb_ai.setChecked(bool(self.config.get("show_ai", True)))
        self.cb_ai.stateChanged.connect(lambda s: self._commit_bool("show_ai", s))
        form.addRow("Интерфейс:", self.cb_ai)

        self.cb_voice = QCheckBox("Голосовое предупреждение о перегреве")
        self.cb_voice.setChecked(bool(self.config.get("enable_voice", True)))
        self.cb_voice.stateChanged.connect(lambda s: self._commit_bool("enable_voice", s))
        form.addRow("Звук:", self.cb_voice)

        self.cb_taskbar = QCheckBox("Показывать значок на панели задач")
        self.cb_taskbar.setChecked(bool(self.config.get("show_in_taskbar", False)))
        self.cb_taskbar.stateChanged.connect(self._commit_taskbar)
        form.addRow("Система:", self.cb_taskbar)

        lay.addLayout(form)
        lay.addStretch(1)
        self.stack.addWidget(page)

    def _build_page_design(self) -> None:
        page, lay = self._page_scaffold("Дизайн и внешний вид")

        form = QFormLayout()
        form.setSpacing(16)
        form.setContentsMargins(0, 0, 0, 0)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(60, 255)
        self.slider_opacity.setValue(int(self.config.get("opacity", 200)))
        self.slider_opacity.valueChanged.connect(self._commit_opacity_live)
        self.slider_opacity.sliderReleased.connect(lambda: save_config(self.config))
        form.addRow("Прозрачность панели:", self.slider_opacity)

        self.accent_swatch = QPushButton()
        self.accent_swatch.setFixedHeight(32)
        self._refresh_accent_swatch()
        self.accent_swatch.clicked.connect(self._pick_accent)
        form.addRow("Акцентный цвет:", self.accent_swatch)

        # preset accent row
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        for name, hex_ in [
            ("Neon Mint", "#00ff99"),
            ("Ultraviolet", "#a78bfa"),
            ("Cyber Cyan", "#22d3ee"),
            ("Magma", "#ff7a59"),
            ("Sakura", "#ff6ba8"),
            ("Gold", "#f5c24c"),
        ]:
            btn = QPushButton()
            btn.setFixedSize(36, 22)
            btn.setToolTip(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: {hex_}; border: 1px solid rgba(255,255,255,50); border-radius: 4px; }}"
                f"QPushButton:hover {{ border: 1px solid rgba(255,255,255,120); }}"
            )
            btn.clicked.connect(lambda _chk=False, c=hex_: self._set_accent(c))
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        form.addRow("Пресеты:", preset_row)

        self.cb_spark = QCheckBox("Показывать мини-графики (sparklines)")
        self.cb_spark.setChecked(bool(self.config.get("show_sparklines", True)))
        self.cb_spark.stateChanged.connect(lambda s: self._commit_bool("show_sparklines", s))
        form.addRow("Графики:", self.cb_spark)

        self.cb_net = QCheckBox("Показывать скорость сети (↑ / ↓)")
        self.cb_net.setChecked(bool(self.config.get("show_network_rate", True)))
        self.cb_net.stateChanged.connect(lambda s: self._commit_bool("show_network_rate", s))
        form.addRow("Сеть:", self.cb_net)

        self.cb_compact = QCheckBox("Компактный режим (узкая панель)")
        self.cb_compact.setChecked(bool(self.config.get("compact_mode", False)))
        self.cb_compact.stateChanged.connect(lambda s: self._commit_bool("compact_mode", s))
        form.addRow("Раскладка:", self.cb_compact)

        btns = QHBoxLayout()
        btn_bg = QPushButton("🖼  Выбрать фон")
        btn_bg.setMinimumHeight(34)
        btn_bg.clicked.connect(self._choose_background)
        btn_clear = QPushButton("✖  Сбросить")
        btn_clear.setMinimumHeight(34)
        btn_clear.clicked.connect(self._clear_background)
        btns.addWidget(btn_bg)
        btns.addWidget(btn_clear)
        form.addRow("Обои окна:", btns)

        lay.addLayout(form)
        lay.addStretch(1)
        self.stack.addWidget(page)

    def _build_page_games(self) -> None:
        page, lay = self._page_scaffold("Игры для Smart Focus")

        hint = QLabel(
            "Оверлей появится, когда заголовок активного окна содержит одну из "
            "этих строк. Регистр не важен."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8891b0; font-size: 11px;")
        lay.addWidget(hint)

        self.games_list = QListWidget()
        for g in self.config.get("target_games", []):
            QListWidgetItem(g, self.games_list)
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

        self.stack.addWidget(page)

    def _build_page_about(self) -> None:
        page, lay = self._page_scaffold("О программе")

        accent = self.config["accent_color"]
        info = QTextEdit()
        info.setReadOnly(True)
        info.setFrameStyle(QFrame.Shape.NoFrame)
        info.setHtml(
            f"""
            <div style="color:#ffffff;font-family:'Segoe UI';">
              <div style="font-size:22px;font-weight:900;color:{accent};">👻 Phantom Overlay</div>
              <div style="color:#a8b2d1;font-size:11px;margin-top:2px;">
                Premium Edition · v{APP_VERSION}
              </div>

              <p style="color:#b6beda;font-size:12px;line-height:1.6;margin-top:18px;">
                Phantom — минималистичный внутриигровой HUD нового поколения:
                круговой индикатор температуры GPU, карточки CPU/RAM с плавной
                анимацией значений и мини-графиками истории, живое статус-ядро
                и frosted-glass панель с мягким свечением акцента.
              </p>

              <p style="color:#8891b0;font-size:11px;">
                <b>Хоткей по умолчанию:</b> Ctrl + Shift + P.
                <br>Настройки автоматически сохраняются в
                <code>phantom_config.json</code>.
              </p>

              <p style="color:#8891b0;font-size:11px;margin-top:18px;">
                Лицензия: MIT &nbsp;·&nbsp; Стек: PyQt6, psutil, ping3, winsdk,
                pypresence &nbsp;·&nbsp; Автор: iq28qi
              </p>
            </div>
            """
        )
        lay.addWidget(info, 1)

        self.stack.addWidget(page)

    # ---------- handlers ----------
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

    def _pick_accent(self) -> None:
        initial = QColor(self.config.get("accent_color", "#00ff99"))
        color = QColorDialog.getColor(initial, self, "Выберите акцентный цвет")
        if color.isValid():
            self._set_accent(color.name())

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

    # ---------- styles ----------
    def _apply_styles(self) -> None:
        accent = self.config.get("accent_color", "#00ff99")
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: #0b0b10;
            }}
            QWidget#side {{
                background-color: #0e0e14;
                border-right: 1px solid #1a1a24;
            }}
            QStackedWidget#stack {{
                background-color: #0b0b10;
            }}
            QLabel {{
                color: #b6beda;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: 600;
            }}
            QListWidget#nav {{
                background: transparent;
                color: #a8b2d1;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: 700;
                border: none;
                outline: 0;
            }}
            QListWidget#nav::item {{
                padding: 10px 12px;
                border-radius: 8px;
                margin: 3px 0;
            }}
            QListWidget#nav::item:hover {{
                background: rgba(255,255,255,10);
                color: #ffffff;
            }}
            QListWidget#nav::item:selected {{
                background: rgba(255,255,255,14);
                color: {accent};
                border-left: 2px solid {accent};
            }}
            QLineEdit, QSpinBox {{
                background-color: #14141c;
                color: {accent};
                border: 1px solid #1f1f27;
                border-radius: 8px;
                padding: 8px 10px;
                font-family: 'Segoe UI';
                font-weight: 800;
                font-size: 12px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 1px solid {accent};
            }}
            QSlider::groove:horizontal {{
                border-radius: 4px;
                height: 8px;
                background: #1f1f27;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {accent}, stop:1 rgba(255,255,255,220));
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
                background-color: #14141c;
                color: {accent};
                border: 1px solid rgba(255,255,255,24);
                border-radius: 10px;
                padding: 6px 14px;
                font-weight: 800;
                font-family: 'Segoe UI';
            }}
            QPushButton:hover {{
                background-color: rgba(0,255,153,18);
                border: 1px solid {accent};
            }}
            QPushButton#done_btn {{
                background-color: {accent};
                color: #0b0b10;
                border: none;
                letter-spacing: 0.8px;
            }}
            QPushButton#done_btn:hover {{
                background-color: rgba(255,255,255,230);
                color: #0b0b10;
            }}
            QCheckBox {{
                color: #e6e9f2;
                font-family: 'Segoe UI';
                font-size: 12px;
                spacing: 10px;
            }}
            QCheckBox::indicator {{
                width: 38px;
                height: 20px;
                border-radius: 10px;
                background-color: #1f1f27;
                border: 1px solid #2a2a36;
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent};
                border: 1px solid {accent};
            }}
            QListWidget {{
                background-color: #14141c;
                color: #e6e9f2;
                border: 1px solid #1f1f27;
                border-radius: 10px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 7px 10px;
                border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background: {accent};
                color: #0b0b10;
                font-weight: 900;
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
class GlassPanel(QWidget):
    """Кастомный рендеринг премиум-фона с frosted-glass эффектом."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._accent = QColor("#00ff99")
        self._bg_pixmap: QPixmap | None = None
        self._noise: QPixmap | None = None
        self._unlocked = False

    def set_accent(self, color: str) -> None:
        self._accent = QColor(color)
        self.update()

    def set_background_image(self, path: str) -> None:
        if path and os.path.exists(path):
            self._bg_pixmap = QPixmap(path)
        else:
            self._bg_pixmap = None
        self.update()

    def set_unlocked(self, unlocked: bool) -> None:
        self._unlocked = bool(unlocked)
        self.update()

    def _make_noise(self, w: int, h: int) -> QPixmap:
        if self._noise is not None and self._noise.width() == w and self._noise.height() == h:
            return self._noise
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        rnd = random.Random(42)
        for _ in range(w * h // 28):
            x = rnd.randint(0, w - 1)
            y = rnd.randint(0, h - 1)
            a = rnd.randint(6, 18)
            img.setPixelColor(x, y, QColor(255, 255, 255, a))
        self._noise = QPixmap.fromImage(img)
        return self._noise

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        radius = 20.0
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        painter.setClipPath(path)

        # ---- base gradient ----
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(22, 22, 32, 245))
        grad.setColorAt(1.0, QColor(9, 9, 14, 245))
        painter.fillRect(self.rect(), QBrush(grad))

        # ---- optional user background ----
        if self._bg_pixmap is not None and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.setOpacity(0.35)
            painter.drawPixmap(0, 0, scaled)
            painter.setOpacity(1.0)

        # ---- accent corner glow (top-left) ----
        accent_glow = QRadialGradient(0, 0, max(w, h))
        c1 = QColor(self._accent); c1.setAlpha(80)
        c2 = QColor(self._accent); c2.setAlpha(0)
        accent_glow.setColorAt(0.0, c1)
        accent_glow.setColorAt(0.9, c2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(accent_glow))
        painter.drawRect(self.rect())

        # ---- soft secondary glow (bottom-right, cool blue) ----
        cool = QColor("#5a7dff")
        cool_glow = QRadialGradient(float(w), float(h), max(w, h) * 0.9)
        cc1 = QColor(cool); cc1.setAlpha(60)
        cc2 = QColor(cool); cc2.setAlpha(0)
        cool_glow.setColorAt(0.0, cc1)
        cool_glow.setColorAt(1.0, cc2)
        painter.setBrush(QBrush(cool_glow))
        painter.drawRect(self.rect())

        # ---- noise texture ----
        painter.drawPixmap(0, 0, self._make_noise(w, h))

        # ---- top highlight line ----
        painter.setPen(QPen(QColor(255, 255, 255, 24), 1))
        painter.drawLine(int(radius / 2), 1, int(w - radius / 2), 1)

        # ---- outer border ----
        border = QColor(self._accent) if self._unlocked else QColor(255, 255, 255, 36)
        if self._unlocked:
            pen = QPen(border)
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
        else:
            pen = QPen(border)
            pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)


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
        self.panel = GlassPanel()
        self.panel.setObjectName("glass_panel")
        self.setCentralWidget(self.panel)

        root = QVBoxLayout(self.panel)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        # ==================== HEADER ====================
        header = QHBoxLayout()
        header.setSpacing(8)

        self.status_dot = StatusDot()
        self.lbl_title = QLabel("PHANTOM")
        tfont = QFont("Segoe UI", 12)
        tfont.setWeight(QFont.Weight.Black)
        tfont.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0)
        self.lbl_title.setFont(tfont)
        self.lbl_title.setStyleSheet("color: #ffffff;")

        self.lbl_uptime = QLabel("00:00")
        ufont = QFont("Consolas", 9)
        ufont.setWeight(QFont.Weight.DemiBold)
        self.lbl_uptime.setFont(ufont)
        self.lbl_uptime.setStyleSheet(
            "color: rgba(255,255,255,140); "
            "background: rgba(255,255,255,14); "
            "border: 1px solid rgba(255,255,255,24); "
            "border-radius: 8px; padding: 2px 8px;"
        )

        self.btn_settings = IconButton("⚙", "Настройки")
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_hide = IconButton("—", "Скрыть (hotkey)")
        self.btn_hide.clicked.connect(lambda: self.toggle_signal.emit())
        self.btn_quit = IconButton("✕", "Выйти")
        self.btn_quit.clicked.connect(self._quit_app)

        header.addWidget(self.status_dot)
        header.addWidget(self.lbl_title)
        header.addSpacing(6)
        header.addWidget(self.lbl_uptime)
        header.addStretch(1)
        header.addWidget(self.btn_settings)
        header.addWidget(self.btn_hide)
        header.addWidget(self.btn_quit)
        root.addLayout(header)

        # separator
        self.sep = QFrame()
        self.sep.setFixedHeight(1)
        self.sep.setStyleSheet("background: rgba(255,255,255,22); border: none;")
        root.addWidget(self.sep)

        # ==================== BODY ====================
        body = QHBoxLayout()
        body.setSpacing(12)

        accent = self.config.get("accent_color", "#00ff99")
        self.gauge = CircularGauge(accent=accent)
        body.addWidget(self.gauge, 0, Qt.AlignmentFlag.AlignTop)

        cards_col = QVBoxLayout()
        cards_col.setSpacing(8)

        show_spark = bool(self.config.get("show_sparklines", True))
        self.card_cpu = MetricCard("🧠", "CPU", accent=accent, show_sparkline=show_spark)
        self.card_ram = MetricCard("💾", "RAM", accent=accent, show_sparkline=show_spark)
        cards_col.addWidget(self.card_cpu)
        cards_col.addWidget(self.card_ram)
        body.addLayout(cards_col, 1)

        root.addLayout(body)

        # ==================== FOOTER ====================
        self.lbl_net = QLabel()
        nfont = QFont("Consolas", 9)
        nfont.setWeight(QFont.Weight.DemiBold)
        self.lbl_net.setFont(nfont)
        self.lbl_net.setStyleSheet(
            "color: rgba(255,255,255,170); "
            "background: rgba(255,255,255,10); "
            "border: 1px solid rgba(255,255,255,20); "
            "border-radius: 8px; padding: 4px 10px;"
        )
        self.lbl_net.setText("🌐  —  ·  ↑ 0 KB/s  ·  ↓ 0 KB/s")
        root.addWidget(self.lbl_net)

        self.lbl_music = Marquee()
        mfont = QFont("Segoe UI", 10)
        mfont.setItalic(True)
        mfont.setWeight(QFont.Weight.Medium)
        self.lbl_music.setFont(mfont)
        self.lbl_music.setStyleSheet("color: rgba(255,255,255,180);")
        self.lbl_music.setFixedHeight(18)
        self.lbl_music.setText("🎵  Ожидание медиа…")
        root.addWidget(self.lbl_music)

        self.lbl_ai = QLabel("🤖  Silphiette: работаю…")
        afont = QFont("Segoe UI", 10)
        afont.setWeight(QFont.Weight.DemiBold)
        afont.setItalic(True)
        self.lbl_ai.setFont(afont)
        self.lbl_ai.setStyleSheet("color: #ffcc66;")
        self.lbl_ai.setWordWrap(True)
        root.addWidget(self.lbl_ai)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(48)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 210))
        self.panel.setGraphicsEffect(shadow)

        self._resize_for_mode()

    def _resize_for_mode(self) -> None:
        if self.config.get("compact_mode", False):
            self.resize(300, 260)
        else:
            self.resize(360, 310)

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
        self.anim.setDuration(700)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(max(0.1, self.config["opacity"] / 255.0))
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
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
        if not hasattr(self, "anim") or self.anim.state() != QPropertyAnimation.State.Running:
            self.setWindowOpacity(max(0.1, self.config["opacity"] / 255.0))

        accent = self.config.get("accent_color", "#00ff99")
        show_spark = bool(self.config.get("show_sparklines", True))

        self.card_cpu.set_accent(accent)
        self.card_ram.set_accent(accent)
        self.gauge.set_accent(accent)
        self.card_cpu.set_sparkline_visible(show_spark)
        self.card_ram.set_sparkline_visible(show_spark)

        self.lbl_net.setVisible(bool(self.config.get("show_network_rate", True)))
        self.lbl_ai.setVisible(bool(self.config.get("show_ai", True)))

        self.panel.set_accent(accent)
        self.panel.set_background_image(self.config.get("bg_image", ""))
        self.panel.set_unlocked(not self.is_locked)

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
                font-family: 'Segoe UI'; font-weight: 700;
            }}
            QMenu::item:selected {{ background-color: {accent}; color: #0b0b10; font-weight: 900; }}
            QMenu::separator {{ height: 1px; background: #1f1f27; margin: 4px 10px; }}
            """
        )

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

        gpu_temp = data.get("gpu_temp")
        gpu_util = data.get("gpu_util")

        # ----- GPU gauge -----
        self.gauge.set_values(gpu_temp, gpu_util)

        if isinstance(gpu_temp, int):
            if gpu_temp > 82:
                self.status_dot.set_color("#ff5c5c")
                if self.config.get("enable_voice", True):
                    self.core.say("Внимание! Видеокарта перегревается.")
            elif gpu_temp > 75:
                self.status_dot.set_color("#ffcc66")
            else:
                self.status_dot.set_color(accent)
        else:
            self.status_dot.set_color(accent)

        # ----- CPU card -----
        cpu = float(data.get("cpu", 0) or 0)
        try:
            cpu_freq = psutil.cpu_freq()
            freq_text = f"{cpu_freq.current/1000:.2f} GHz" if cpu_freq else ""
        except Exception:
            freq_text = ""
        self.card_cpu.set_value(
            cpu, f"{cpu:.0f}%",
            secondary=freq_text or "загрузка",
            critical=cpu >= 95,
        )

        # ----- RAM card -----
        ram = float(data.get("ram", 0) or 0)
        try:
            vm = psutil.virtual_memory()
            gb_used = vm.used / (1024 ** 3)
            gb_total = vm.total / (1024 ** 3)
            ram_sec = f"{gb_used:.1f} / {gb_total:.1f} GB"
        except Exception:
            ram_sec = "память"
        self.card_ram.set_value(
            ram, f"{ram:.0f}%",
            secondary=ram_sec,
            critical=ram >= 92,
        )

        # ----- NET / PING -----
        ping_val = data.get("ping")
        up = float(data.get("net_up", 0.0) or 0.0)
        down = float(data.get("net_down", 0.0) or 0.0)
        ping_text = f"{ping_val} ms" if isinstance(ping_val, int) else "—"
        ping_color = accent
        if isinstance(ping_val, int):
            if ping_val > 120:
                ping_color = "#ff5c5c"
            elif ping_val > 60:
                ping_color = "#ffcc66"
        self.lbl_net.setText(
            f"🌐  {ping_text}   ·   ↑ {up:5.0f} KB/s   ·   ↓ {down:5.0f} KB/s"
        )
        self.lbl_net.setStyleSheet(
            f"color: {ping_color}; "
            "background: rgba(255,255,255,10); "
            "border: 1px solid rgba(255,255,255,20); "
            "border-radius: 8px; padding: 4px 10px;"
        )

        # ----- MUSIC -----
        music = (data.get("music", "") or "").strip()
        self.lbl_music.setText(f"🎵  {music}" if music else "🎵  —")

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
            return "🤖  Silphiette: перегрев GPU! Снизь нагрузку."
        if cpu >= 95:
            return "🤖  Silphiette: CPU на 100% — фоновые задачи?"
        if ram >= 92:
            return "🤖  Silphiette: память почти закончилась."
        if isinstance(ping_val, int) and ping_val > 150:
            return "🤖  Silphiette: сеть не в форме — высокий пинг."
        return "🤖  Silphiette: система в норме."

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
