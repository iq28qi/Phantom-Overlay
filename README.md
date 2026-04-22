<div align="center">

<img src="icon.png" alt="Phantom Overlay" width="112" height="112" />

# 👻 Phantom Overlay

**HUD нового поколения для Windows: glassmorphism, неон и вся телеметрия системы — поверх любой игры.**

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-UI-41CD52?logo=qt&logoColor=white)](https://www.riverbankcomputing.com/software/pyqt/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-A855F7.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/iq28qi/Phantom-Overlay?logo=github&label=release&color=00ff99)](https://github.com/iq28qi/Phantom-Overlay/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/iq28qi/Phantom-Overlay/total?logo=github&color=00ff99)](https://github.com/iq28qi/Phantom-Overlay/releases)
[![Stars](https://img.shields.io/github/stars/iq28qi/Phantom-Overlay?style=social)](https://github.com/iq28qi/Phantom-Overlay/stargazers)

**[ ⬇️ Скачать .exe ](https://github.com/iq28qi/Phantom-Overlay/releases/latest)** · **[ 🇬🇧 English README ](README.en.md)** · **[ 🗺 Roadmap ](#-roadmap)** · **[ 💬 Discussions ](https://github.com/iq28qi/Phantom-Overlay/discussions)**

<!-- Hero screenshot. Положи `preview.png` в assets/ и картинка подтянется автоматически. -->
<img src="assets/preview.png" alt="Phantom Overlay — hero shot" width="720" onerror="this.style.display='none'" />

</div>

---

## 📑 Содержание

- [🚀 Что это такое](#-что-это-такое)
- [⚡ Фичи](#-фичи)
- [🎬 Галерея](#-галерея)
- [⬇️ Установка для геймеров (готовый .exe)](#️-установка-для-геймеров-готовый-exe)
- [🛠 Запуск из исходников (для разработчиков)](#-запуск-из-исходников-для-разработчиков)
- [🎛 Управление и хоткеи](#-управление-и-хоткеи)
- [🧩 Темы, пресеты и цветовые режимы](#-темы-пресеты-и-цветовые-режимы)
- [🔌 Плагины](#-плагины)
- [🏗 Архитектура](#-архитектура)
- [🗺 Roadmap](#-roadmap)
- [🤝 Contributing](#-contributing)
- [📄 Лицензия](#-лицензия)

---

## 🚀 Что это такое

**Phantom Overlay** — лёгкий (`< 40 МБ`) оверлей на Python + PyQt6 в стиле **glassmorphism**: матовое стекло, мягкая тень, неоновый акцент, вращающийся conic-бордер и шум на фоне. Живёт поверх всех окон, автоматически скрывается, когда ты не в игре, и показывает всё, что важно во время катки:

> **CPU · RAM · GPU (temp & util) · батарея · Disk I/O · сеть (↑/↓ / ping) · текущий трек · таймер сессии · голосовые алерты**

Оверлей полностью настраивается без перезапуска — в `Phantom Control Center` все изменения видно мгновенно через live preview.

---

## ⚡ Фичи

### 📊 Телеметрия системы
- **CPU / RAM** с анимированным процентом и sparkline-историей.
- **GPU (NVIDIA)** — температура и нагрузка через NVML, круговая индикация.
- **CPU temp** из `psutil.sensors_temperatures` (coretemp / k10temp / acpitz).
- **Сеть** — пинг до настраиваемого хоста, скорость up/down в реальном времени.
- **Disk I/O** — MB/s чтения и записи.
- **Батарея** — процент + AC-индикация.
- **Clock / аптайм** — часы с секундами и время работы сессии.
- **Peak tracker** — пиковые значения CPU/RAM/GPU-temp/Ping с начала сессии.

### 🎨 Визуал
- **Glassmorphism-панель** с градиентом, radial glow, шумом и опциональным вращающимся **conic-бордером**.
- **Светящиеся частицы** на фоне (можно выключить).
- **Анимация значений** через `QPropertyAnimation` — никаких скачков цифр.
- **Hover micro-animations** — мягкий «lift» у кнопок и карточек через `QGraphicsDropShadowEffect`.
- **Кастомные шрифты** — Inter (UI) и JetBrains Mono (цифры), вшиты в `fonts/` и подгружаются через `QFontDatabase`. Если шрифтов нет — фолбэк на Segoe UI / Consolas.
- **Динамические цвета** — два режима: **steps** (пороги warn/crit) и **gradient** (плавный переход `accent → yellow → red` по всей шкале нагрузки).
- **Theme presets**: Neon Mint, Ultraviolet, Cyber Cyan, Magma, Sakura, Matrix, Stealth, Gold + любой кастомный акцент через palette picker.

### 🎮 Gaming-UX
- **Smart Focus** — оверлей показывается только когда активно окно из списка игр (`CS2`, `Valorant`, `Apex`, `Dota 2`, …). Список редактируется в Control Center.
- **Redactable window**: drag-режим, угловой snap, auto-hide по неактивности, click-through, always-on-top, lock, три таскбар-режима.
- **Три пресета-профиля** (Gaming / Coding / Streaming) с своими настройками прозрачности, цвета и видимости виджетов.
- **Profile triggers** через JSON — например, `shooter_profile.json` автоматически включает crosshair и повышает opacity, когда активно окно CS2/Valorant.

### 🔊 Интеграции
- **Discord Rich Presence** — транслирует температуру GPU и текущий трек (нужен свой Client ID).
- **Windows Media Control** (`winsdk`) — Now Playing + кнопки Play/Pause/Next/Prev прямо в трее.
- **AI-ассистент Silphiette** — контекстные текстовые статусы: перегрев GPU, 100% CPU, высокий пинг, «система в норме».
- **Голосовые алерты** через `pyttsx3` — предупреждение при перегреве.
- **Плагины** через Python-файлы в `plugins/` — свои виджеты и метрики без лезания в основной код *(загрузчик — в дороге, см. [Roadmap](#-roadmap))*.

### ⚙️ Технически
- **Кэшированный тайл шума** 256×256 + `QBrush` — O(1) на отрисовку при любом размере окна.
- **Отдельный QThread** для hardware-мониторинга — UI никогда не фризится.
- **Чистое завершение потоков**, логирование ошибок в stderr (`[phantom][prefix] Type: message`).
- **2 языка UI**: русский / английский (переключение в настройках).

---

## 🎬 Галерея

> GIF и скриншоты кладутся в [`assets/`](assets/README.md). Если файл ещё не записан — GitHub покажет битую ссылку, так что секции с картинками заполняются по мере записи.

<table>
<tr>
<td align="center" width="50%">
<strong>Оверлей в CS2</strong><br/>
<img src="assets/overlay_in_game.gif" alt="Overlay over CS2" width="100%" onerror="this.alt='(GIF ещё не записан — см. assets/README.md)'" />
</td>
<td align="center" width="50%">
<strong>Live Preview в настройках</strong><br/>
<img src="assets/settings_live.gif" alt="Control Center live preview" width="100%" onerror="this.alt='(GIF ещё не записан — см. assets/README.md)'" />
</td>
</tr>
<tr>
<td align="center">
<strong>Theme presets</strong><br/>
<img src="assets/presets.png" alt="Theme presets grid" width="100%" onerror="this.alt='(скриншот ещё не записан)'" />
</td>
<td align="center">
<strong>Compact mode</strong><br/>
<img src="assets/compact_mode.png" alt="Compact mode" width="100%" onerror="this.alt='(скриншот ещё не записан)'" />
</td>
</tr>
</table>

---

## ⬇️ Установка для геймеров (готовый .exe)

<div align="center">

### 📥 [Скачать **PhantomOverlay.exe** — GitHub Releases →](https://github.com/iq28qi/Phantom-Overlay/releases/latest)

</div>

1. Скачай `PhantomOverlay.exe` из [последнего релиза](https://github.com/iq28qi/Phantom-Overlay/releases/latest).
2. Положи его в удобную папку (например, `C:\Phantom\`).
3. *(Опционально)* положи рядом свой `icon.png` — он станет иконкой в трее.
4. Запусти `PhantomOverlay.exe`. Оверлей плавно появится, в трее возникнет значок призрака 👻.
5. Правый клик по значку → **`⚙ Настройки`** → докрути под себя.

> Все твои настройки автоматически сохраняются в `phantom_config.json` рядом с `.exe`. Перенеси файл — и настройки уедут вместе с ним.

---

## 🛠 Запуск из исходников (для разработчиков)

Требования: **Python 3.12+**, Windows 10 / 11. На Linux и macOS большая часть UI отрендерится, но hardware-модули (`keyboard`, `winsdk`, `nvml`, `pyttsx3`) — Windows-only.

```bash
git clone https://github.com/iq28qi/Phantom-Overlay.git
cd Phantom-Overlay

python -m venv .venv
.venv\Scripts\activate      # PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
python phantom.py
```

### Сборка локального .exe

```bat
build.bat
```

Либо вручную:

```pwsh
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed `
    --collect-all winsdk `
    --add-data "fonts;fonts" `
    --add-data "plugins;plugins" `
    --icon "icon.ico" `
    --name "PhantomOverlay" `
    phantom.py
```

> ⚠️ Библиотека `keyboard` для глобальных хоткеев на Windows требует запуска от администратора.

### CI / автоматический релиз

В репозиторий подключён workflow [`.github/workflows/release.yml`](.github/workflows/release.yml):

- Триггерится на пуш тега `v*` (например, `v5.2.0`).
- Собирает `PhantomOverlay.exe` через PyInstaller на `windows-latest`.
- Автоматически создаёт GitHub Release и прикрепляет .exe к нему.
- Отдельно можно запустить вручную через **Actions → Build & Release → Run workflow** — получится артефакт без публикации релиза.

---

## 🎛 Управление и хоткеи

| Действие | Как |
| --- | --- |
| Показать / скрыть оверлей | Двойной клик по значку в трее **или** `Ctrl + Shift + P` |
| Открыть настройки | Правый клик по трею → `⚙ Настройки` **или** `Ctrl + Shift + O` |
| Режим перетаскивания | Трей → `🛠 Режим перетаскивания` |
| Управление музыкой | Трей → `⏯ / ⏭ / ⏮` (требует winsdk) |
| Выход | Трей → `❌ Выход` |

Все хоткеи настраиваются в `Control Center → Основные`.

---

## 🧩 Темы, пресеты и цветовые режимы

- **Theme presets** — готовые сеты акцента + прозрачность + частицы + compact mode. Кликаешь карточку — применяется мгновенно.
- **Custom accent** — palette picker или ручной HEX (`#ff3366`, `#22d3ee`, …).
- **Color mode**:
  - `steps` — классика: цвет переключается на warn (80%) и crit (95%).
  - `gradient` — цвет плавно смещается `accent → yellow → red` пропорционально нагрузке на протяжении всей шкалы 0–100%.
- **Border style**: `solid`, `dashed`, `neon`, `none` + включаемый вращающийся conic-бордер поверх.
- **Window mode**: `auto` / `compact` / `fixed` / `free` — от 380×320 до пользовательских размеров.
- **Corner snap**: top-left / top-right / bottom-* — оверлей сам прилипает к углу при запуске.

---

## 🔌 Плагины

Плагины лежат в [`plugins/`](plugins/) и следуют простому контракту:

```python
# plugins/uptime_plugin.py
PLUGIN_META = {
    "name": "Session Uptime",
    "version": "1.0",
    "author": "phantom",
    "description": "Показывает время работы оверлея",
}

class PhantomPlugin:
    def __init__(self, config: dict): ...
    def on_data(self, data: dict) -> dict: ...   # добавь свои ключи в data
    def get_label(self) -> str: ...              # строка для чипа в оверлее
    def on_config_change(self, config: dict): ...
```

> ⚙️ **Состояние**: формат плагина зафиксирован, пример `plugins/uptime_plugin.py` рабочий, но автоматический `importlib`-loader сейчас в разработке ([Roadmap](#-roadmap) → PR3). До его появления плагин не подключается сам.

---

## 🏗 Архитектура

На сегодня — один `phantom.py` (~3600 строк) + вспомогательные ассеты. Модули внутри файла логически разделены заголовками:

```
phantom.py
├── CONFIG            — DEFAULT_CONFIG, load/save, автомиграция
├── TRANSLATIONS      — словари ru / en + tr()/set_language()
├── FONTS             — load_bundled_fonts(), UI_FONT_FAMILY, MONO_FONT_FAMILY
├── COLOR_MODE        — steps/gradient + _color_for_load / _color_for_temp
├── PRIMITIVES        — helpers, Sparkline, Chip, HoverGlow, StatusDot
├── HARDWARE          — HardwareMonitorThread (QThread + NVML + psutil + ping)
├── CORE              — PhantomCore (Discord RPC, TTS, Media via winsdk)
├── WIDGETS           — MetricCard, CircularGauge, Visualizer, PresetCard, ...
├── GLASS_PANEL       — фон с кэшированным тайлом шума и conic-бордером
├── SETTINGS          — ModernSettings (Control Center, 4 вкладки + live preview)
├── OVERLAY           — PhantomOverlay (главное окно + трей + хоткеи)
└── ENTRY             — main(), _install_excepthook()
```

Распил этого монолита на `config.py` / `hardware.py` / `widgets/` / `overlay.py` — запланирован (см. [Roadmap](#-roadmap)).

---

## 🗺 Roadmap

| # | Задача | Статус |
| --- | --- | --- |
| ✅ PR1 | Polish & perf: bundled fonts, cached noise tile, hover micro-anim, gradient color mode | [#2](https://github.com/iq28qi/Phantom-Overlay/pull/2) |
| 🧩 PR2 | Repo polish: README, badges, assets/, plugins/, issue/PR templates, release workflow | в этом PR |
| 🔌 PR3 | Plugin loader через `importlib` + hot-reload из `Control Center` | planned |
| 🎮 PR4 | CS2 Game State Integration (HP / K-D / bomb timer) | planned |
| 💡 PR4 | OpenRGB integration — подсветка корпуса в такт с critical-алертами | planned |
| 🧱 PR5 | Распил `phantom.py` на модули (`config.py`, `hardware.py`, `widgets/`, `overlay.py`) | planned |
| 🚀 future | `QOpenGLWidget`-бэкенд для `GlassPanel` (только если FPS начнёт просаживаться) | exploratory |

---

## 🤝 Contributing

Баги и идеи приветствуются:

- 🐛 **Баг** — используй [шаблон Bug report](.github/ISSUE_TEMPLATE/bug_report.yml).
- ✨ **Фича/идея** — шаблон [Feature request](.github/ISSUE_TEMPLATE/feature_request.yml).
- 🛠 **Pull request** — открой issue сначала (кроме опечаток и мелких фиксов), следуй [`PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

Правила стиля:

- Никаких новых зависимостей без обсуждения — `requirements.txt` должен оставаться компактным.
- UI-строки добавляются сразу в обе локали (`ru` + `en`) в `TRANSLATIONS`.
- Изменения в `DEFAULT_CONFIG` — совместимые (старые ключи не ломаются, новые добавляются с разумным дефолтом).

---

## 📄 Лицензия

[MIT](LICENSE) © 2025 iq28qi. Inter и JetBrains Mono — [SIL Open Font License 1.1](fonts/).
