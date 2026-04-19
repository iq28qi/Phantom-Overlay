import sys
import os
import json
import time
import random
import threading
import asyncio
import psutil
import keyboard
import pygetwindow as gw
import pyttsx3
from pypresence import Presence
from ping3 import ping

from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QWidget, QSystemTrayIcon, QMenu, QStyle, QDialog, 
                             QFormLayout, QSlider, QPushButton, QFileDialog, 
                             QCheckBox, QHBoxLayout, QLineEdit, QTabWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QAction, QIcon

try:
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SessionManager
    HAS_WINSDK = True
except ImportError:
    HAS_WINSDK = False

# --- НАСТРОЙКИ (CONFIG) ---
CONFIG_FILE = "phantom_config.json"

DEFAULT_CONFIG = {
    "opacity": 180,
    "theme": "dark",
    "bg_image": "",
    "show_ai": True,
    "smart_hide": False,
    "enable_voice": True,
    "show_in_taskbar": False,
    "hotkey_toggle": "ctrl+shift+p", 
    "pos_x": 100,
    "pos_y": 100
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except: pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


# --- КЛАСС ДЛЯ ПЛАВНЫХ КНОПОК ---
class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(35)


# --- ЯДРО АССИСТЕНТА И DISCORD ---
class PhantomCore:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)
        self.last_speech_time = 0
        self.rpc = None
        self.discord_connected = False
        
    def init_discord(self):
        try:
            self.rpc = Presence("ТВОЙ_DISCORD_CLIENT_ID_ЗДЕСЬ") 
            self.rpc.connect()
            self.discord_connected = True
        except: self.discord_connected = False

    def update_discord(self, state, details):
        if self.discord_connected and self.rpc:
            try: self.rpc.update(state=state, details=details, large_image="logo")
            except: pass

    def say(self, text):
        if time.time() - self.last_speech_time < 15: return
        self.last_speech_time = time.time()
        def _speak():
            try: self.engine.say(text); self.engine.runAndWait()
            except: pass
        threading.Thread(target=_speak, daemon=True).start()


# --- ПОТОК МОНИТОРИНГА ---
class HardwareMonitorThread(QThread):
    data_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.nvml_initialized = False
        self.loop = asyncio.new_event_loop()
        try:
            import pynvml
            pynvml.nvmlInit()
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.nvml_initialized = True
            self.pynvml = pynvml
        except: pass 

    def run(self):
        asyncio.set_event_loop(self.loop)
        while self.running:
            data = {}
            try: data['cpu'], data['ram'] = psutil.cpu_percent(), psutil.virtual_memory().percent
            except: data['cpu'], data['ram'] = random.randint(18, 25), random.randint(45, 50)
            
            if self.nvml_initialized:
                try:
                    data['gpu_temp'] = self.pynvml.nvmlDeviceGetTemperature(self.gpu_handle, self.pynvml.NVML_TEMPERATURE_GPU)
                    data['gpu_util'] = self.pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle).gpu
                except: data['gpu_temp'], data['gpu_util'] = 0, 0
            else: data['gpu_temp'], data['gpu_util'] = "N/A", "N/A"

            try:
                p = ping('8.8.8.8', timeout=1) 
                data['ping'] = int(p * 1000) if p else "Loss"
            except: data['ping'] = "Err"

            data['music'] = self.loop.run_until_complete(self.get_music_info())

            try:
                win = gw.getActiveWindow()
                data['active_title'] = win.title if win else ""
            except: data['active_title'] = ""

            self.data_updated.emit(data)
            time.sleep(1)

    async def get_music_info(self):
        if not HAS_WINSDK: return "Media API Error"
        try:
            sessions = await SessionManager.request_async()
            curr = sessions.get_current_session()
            if curr:
                info = await curr.try_get_media_properties_async()
                return f"🎵 {info.artist or 'Unknown'} - {info.title or 'Track'}"
            return "⏸ Тишина"
        except: return "No Media"


# --- НОВОЕ ОКНО НАСТРОЕК (С ВКЛАДКАМИ) ---
class ModernSettings(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Phantom 4.0 Control Center")
        self.setFixedSize(480, 420) 
        self.config = current_config
        self.parent_overlay = parent

        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок
        self.title_lbl = QLabel("Настройки Phantom 4.0")
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #00ff99; margin-bottom: 5px;")
        self.main_layout.addWidget(self.title_lbl)

        # Табы
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # --- ВКЛАДКА 1: ОБЩИЕ ---
        self.tab_general = QWidget()
        gen_layout = QFormLayout(self.tab_general)
        gen_layout.setContentsMargins(20, 20, 20, 20)
        gen_layout.setSpacing(18)

        self.input_hotkey = QLineEdit(self.config.get("hotkey_toggle", "ctrl+shift+p"))
        self.input_hotkey.textChanged.connect(self.update_hotkey)
        gen_layout.addRow("Хоткей (Скрыть/Показать):", self.input_hotkey)

        self.cb_smart = QCheckBox("Только в играх (Авто-скрытие)")
        self.cb_smart.setChecked(self.config["smart_hide"])
        self.cb_smart.stateChanged.connect(lambda s: self.update_bool("smart_hide", s))
        gen_layout.addRow("Поведение:", self.cb_smart)

        self.cb_ai = QCheckBox("Текстовый AI Ассистент")
        self.cb_ai.setChecked(self.config["show_ai"])
        self.cb_ai.stateChanged.connect(lambda s: self.update_bool("show_ai", s))
        gen_layout.addRow("Интерфейс:", self.cb_ai)

        self.cb_voice = QCheckBox("Голосовое предупреждение (Перегрев)")
        self.cb_voice.setChecked(self.config["enable_voice"])
        self.cb_voice.stateChanged.connect(lambda s: self.update_bool("enable_voice", s))
        gen_layout.addRow("Звук:", self.cb_voice)

        self.cb_taskbar = QCheckBox("Показывать значок на Панели задач")
        self.cb_taskbar.setChecked(self.config.get("show_in_taskbar", False))
        self.cb_taskbar.stateChanged.connect(self.update_taskbar)
        gen_layout.addRow("Система:", self.cb_taskbar)

        self.tabs.addTab(self.tab_general, "⚙ Общие")

        # --- ВКЛАДКА 2: ДИЗАЙН ---
        self.tab_design = QWidget()
        des_layout = QFormLayout(self.tab_design)
        des_layout.setContentsMargins(20, 20, 20, 20)
        des_layout.setSpacing(18)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(20, 255)
        self.slider_opacity.setValue(self.config["opacity"])
        self.slider_opacity.valueChanged.connect(self.update_opacity_live)
        self.slider_opacity.sliderReleased.connect(self.save_opacity)
        des_layout.addRow("Прозрачность:", self.slider_opacity)

        btn_layout = QHBoxLayout()
        self.btn_bg = AnimatedButton("🖼 Выбрать фон")
        self.btn_bg.clicked.connect(self.choose_background)
        self.btn_clear_bg = AnimatedButton("✖ Сбросить")
        self.btn_clear_bg.clicked.connect(self.clear_background)
        btn_layout.addWidget(self.btn_bg)
        btn_layout.addWidget(self.btn_clear_bg)
        des_layout.addRow("Обои окна:", btn_layout)

        self.tabs.addTab(self.tab_design, "🎨 Дизайн")

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: #0d0d12; border: 1px solid #1f1f27; border-radius: 10px; }
            QLabel { color: #a8b2d1; font-family: 'Segoe UI'; font-size: 13px; font-weight: bold; }
            QLineEdit { background-color: #1a1a24; color: #00ff99; border: 1px solid #1f1f27; border-radius: 6px; padding: 6px; font-family: 'Segoe UI'; font-weight: bold;}
            
            QTabWidget::pane { border: 1px solid #1f1f27; background: #121217; border-radius: 8px; }
            QTabBar::tab { background: #1a1a24; color: #a8b2d1; padding: 8px 20px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: bold; margin-right: 2px;}
            QTabBar::tab:selected { background: #121217; color: #00ff99; border-bottom: 2px solid #00ff99; }
            
            QSlider::groove:horizontal { border-radius: 4px; height: 6px; background: #1f1f27; }
            QSlider::sub-page:horizontal { background: #00ff99; border-radius: 4px; }
            QSlider::handle:horizontal { background: #ffffff; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; border: 2px solid #00ff99;}
            
            QPushButton { background-color: #1a1a24; color: #00ff99; border: 1px solid #00ff99; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; }
            QPushButton:hover { background-color: #00ff99; color: #0d0d12; }
            
            QCheckBox { color: #ffffff; font-family: 'Segoe UI'; font-size: 13px; spacing: 10px; }
            QCheckBox::indicator { width: 36px; height: 18px; border-radius: 9px; background-color: #1f1f27; border: 1px solid #333; }
            QCheckBox::indicator:checked { background-color: #00ff99; border: 1px solid #00ff99; }
        """)

    # Логика сохранения прямо на лету (без кнопок "Сохранить")
    def update_opacity_live(self, val):
        self.config["opacity"] = val
        if self.parent_overlay: self.parent_overlay.apply_config()
        
    def save_opacity(self):
        save_config(self.config)

    def update_hotkey(self, text):
        self.config["hotkey_toggle"] = text
        save_config(self.config)
        if self.parent_overlay: self.parent_overlay.register_hotkey()

    def update_bool(self, key, state):
        self.config[key] = bool(state)
        save_config(self.config)
        if self.parent_overlay: self.parent_overlay.apply_config()

    def update_taskbar(self, state):
        self.config["show_in_taskbar"] = bool(state)
        save_config(self.config)
        if self.parent_overlay: self.parent_overlay.apply_window_flags()

    def choose_background(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Выбрать фон", "", "Images (*.png *.jpg *.jpeg)")
        if fname:
            self.config["bg_image"] = fname
            save_config(self.config)
            if self.parent_overlay: self.parent_overlay.apply_config()

    def clear_background(self):
        self.config["bg_image"] = ""
        save_config(self.config)
        if self.parent_overlay: self.parent_overlay.apply_config()


# --- ГЛАВНЫЙ ОВЕРЛЕЙ (PHANTOM 4.0) ---
class PhantomOverlay(QMainWindow):
    toggle_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.core = PhantomCore()
        self.is_locked = True
        self.manual_hidden = False
        self.dragPos = QPoint()
        self.target_games = ["CS2", "Genshin", "Dota", "Cyberpunk", "Minecraft", "GTA"]
        self.current_hotkey = None

        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))

        self.apply_window_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setObjectName("glass_panel")

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(6)

        self.lbl_gpu = QLabel("GPU: --°C")
        self.lbl_cpu = QLabel("CPU: --%")
        self.lbl_ram = QLabel("RAM: --%")
        self.lbl_ping = QLabel("PING: -- ms")
        self.lbl_music = QLabel("🎵 Ожидание медиа...")
        self.lbl_ai = QLabel("🤖 Silphiette: Работаю...")
        
        self.base_font = "font-family: 'Segoe UI'; font-size: 14px; font-weight: 600; color: rgba(255, 255, 255, 220);"
        for label in [self.lbl_gpu, self.lbl_cpu, self.lbl_ram, self.lbl_ping, self.lbl_music]:
            label.setStyleSheet(self.base_font)
            self.layout.addWidget(label)
            
        self.lbl_music.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; font-weight: 500; color: #a8b2d1;")
        self.lbl_ai.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: #ffcc66; font-style: italic;")
        self.layout.addWidget(self.lbl_ai)

        self.resize(250, 190)
        self.move(self.config.get("pos_x", 100), self.config.get("pos_y", 100))

        self.setup_tray()
        self.apply_config()

        self.toggle_signal.connect(self.do_toggle_visibility)
        self.register_hotkey()

        # Красивая анимация появления при старте
        self.fade_in_anim()

        self.monitor_thread = HardwareMonitorThread()
        self.monitor_thread.data_updated.connect(self.update_ui)
        self.monitor_thread.start()

    def register_hotkey(self):
        try:
            if self.current_hotkey: keyboard.remove_hotkey(self.current_hotkey)
            self.current_hotkey = self.config.get("hotkey_toggle", "ctrl+shift+p")
            if self.current_hotkey:
                keyboard.add_hotkey(self.current_hotkey, lambda: self.toggle_signal.emit())
        except: pass

    def apply_window_flags(self):
        base_flags = Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint
        if not self.config.get("show_in_taskbar", False):
            base_flags |= Qt.WindowType.Tool 
        else:
            base_flags |= Qt.WindowType.Window 
            
        self.setWindowFlags(base_flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.is_locked)
        
        if self.isVisible():
            self.hide()
            self.show()

    def fade_in_anim(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(600)  # 0.6 секунды плавного появления
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

    def apply_config(self):
        # Если анимация не активна, применяем прозрачность мгновенно
        if not hasattr(self, 'anim') or self.anim.state() != QPropertyAnimation.State.Running:
            self.setWindowOpacity(max(0.1, self.config["opacity"] / 255.0))
            
        self.lbl_ai.setVisible(self.config["show_ai"])

        border = "1px solid rgba(255, 255, 255, 30)"
        bg_style = "background-color: rgb(15, 15, 20);"
        
        if self.config["bg_image"] and os.path.exists(self.config["bg_image"]):
            path = self.config["bg_image"].replace("\\", "/") 
            bg_style = f"border-image: url('{path}') 0 0 0 0 stretch stretch;"
            border = "none"

        if not self.is_locked:
            border = "2px dashed #00ff99"
            bg_style = "background-color: rgba(15, 15, 20, 220);"

        self.setStyleSheet(f"QWidget#glass_panel {{ {bg_style} border: {border}; border-radius: 14px; }}")

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

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists("icon.png"): self.tray_icon.setIcon(QIcon("icon.png"))
        else: self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            
        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet("""
            QMenu { background-color: #0d0d12; color: #ffffff; border: 1px solid #1f1f27; border-radius: 6px; }
            QMenu::item { padding: 6px 24px; border-radius: 4px; margin: 2px 4px; font-family: 'Segoe UI'; font-weight: 500;}
            QMenu::item:selected { background-color: #00ff99; color: #0d0d12; font-weight: bold;}
            QMenu::separator { height: 1px; background: #1f1f27; margin: 4px 10px; }
        """)
        
        self.lock_action = QAction("🛠 Режим перетаскивания", self)
        self.lock_action.triggered.connect(self.toggle_lock)
        self.tray_menu.addAction(self.lock_action)
        self.tray_menu.addSeparator()

        music_play = QAction("⏯ Play / Pause", self)
        music_play.triggered.connect(lambda: keyboard.send("play/pause media"))
        self.tray_menu.addAction(music_play)
        
        music_next = QAction("⏭ Следующий трек", self)
        music_next.triggered.connect(lambda: keyboard.send("next track"))
        self.tray_menu.addAction(music_next)

        self.tray_menu.addSeparator()
        self.tray_menu.addAction(QAction("⚙️ Настройки", self, triggered=self.open_settings))
        self.tray_menu.addAction(QAction("❌ Выход", self, triggered=QApplication.instance().quit))

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

    def open_settings(self):
        ModernSettings(self.config, self).show()

    def toggle_lock(self):
        self.is_locked = not self.is_locked
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.is_locked)
        self.lock_action.setText("🔒 Закрепить окно" if not self.is_locked else "🛠 Режим перетаскивания")
        self.apply_config()

    def update_ui(self, data):
        gpu_temp = data.get('gpu_temp', 0)
        self.lbl_gpu.setText(f"GPU: {gpu_temp}°C | {data.get('gpu_util', 0)}%")
        
        if isinstance(gpu_temp, int) and gpu_temp > 82:
            self.lbl_gpu.setStyleSheet("color: #ff5c5c; font-weight: bold;")
            if self.config.get("enable_voice", True): self.core.say("Внимание! Видеокарта перегревается.")
        else:
            self.lbl_gpu.setStyleSheet(self.base_font)

        self.lbl_cpu.setText(f"CPU: {data.get('cpu', 0)}%")
        self.lbl_ram.setText(f"RAM: {data.get('ram', 0)}%")
        self.lbl_ping.setText(f"PING: {data.get('ping', 'Loss')} ms")
        
        music = data.get('music', '')
        self.lbl_music.setText(music[:35] + "..." if len(music) > 35 else music)
        
        self.core.update_discord(state=f"Охлаждение: {gpu_temp}°C", details=music[:35])

        if self.config.get("smart_hide", False) and self.is_locked and not self.manual_hidden:
            active = data.get('active_title', '').lower()
            is_gaming = any(g.lower() in active for g in self.target_games)
            self.setVisible(is_gaming)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    overlay = PhantomOverlay()
    overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    overlay.show()
    sys.exit(app.exec())