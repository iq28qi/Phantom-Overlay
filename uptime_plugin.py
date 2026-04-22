"""
Пример плагина: счётчик аптайма сессии.
Показывает сколько времени оверлей работает.
Закинь этот файл в папку plugins/ — подхватится автоматически.
"""
import time

PLUGIN_META = {
    "name": "Session Uptime",
    "version": "1.0",
    "author": "phantom",
    "description": "Показывает время работы оверлея"
}

class PhantomPlugin:
    def __init__(self, config: dict):
        self.start_time = time.time()
        self.config = config

    def on_data(self, data: dict) -> dict:
        elapsed = int(time.time() - self.start_time)
        h, m = divmod(elapsed // 60, 60)
        data["uptime"] = f"{h:02d}:{m:02d}"
        return data

    def get_label(self) -> str:
        elapsed = int(time.time() - self.start_time)
        h, m = divmod(elapsed // 60, 60)
        return f"⏱ {h:02d}:{m:02d}"

    def on_config_change(self, config: dict):
        self.config = config
