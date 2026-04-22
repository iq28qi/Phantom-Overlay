<div align="center">

<img src="icon.png" alt="Phantom Overlay" width="112" height="112" />

# 👻 Phantom Overlay

**A next-gen HUD for Windows: glassmorphism, neon and your whole system telemetry — on top of any game.**

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-UI-41CD52?logo=qt&logoColor=white)](https://www.riverbankcomputing.com/software/pyqt/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-A855F7.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/iq28qi/Phantom-Overlay?logo=github&label=release&color=00ff99)](https://github.com/iq28qi/Phantom-Overlay/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/iq28qi/Phantom-Overlay/total?logo=github&color=00ff99)](https://github.com/iq28qi/Phantom-Overlay/releases)
[![Stars](https://img.shields.io/github/stars/iq28qi/Phantom-Overlay?style=social)](https://github.com/iq28qi/Phantom-Overlay/stargazers)

**[ ⬇️ Download .exe ](https://github.com/iq28qi/Phantom-Overlay/releases/latest)** · **[ 🇷🇺 Русский README ](README.md)** · **[ 🗺 Roadmap ](#-roadmap)** · **[ 💬 Discussions ](https://github.com/iq28qi/Phantom-Overlay/discussions)**

<img src="assets/preview.png" alt="Phantom Overlay — hero shot" width="720" onerror="this.style.display='none'" />

</div>

---

## 📑 Table of contents

- [🚀 What is it](#-what-is-it)
- [⚡ Features](#-features)
- [🎬 Gallery](#-gallery)
- [⬇️ Install for gamers (pre-built .exe)](#️-install-for-gamers-pre-built-exe)
- [🛠 Run from source (for developers)](#-run-from-source-for-developers)
- [🎛 Controls & hotkeys](#-controls--hotkeys)
- [🧩 Themes, presets & color modes](#-themes-presets--color-modes)
- [🔌 Plugins](#-plugins)
- [🏗 Architecture](#-architecture)
- [🗺 Roadmap](#-roadmap)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## 🚀 What is it

**Phantom Overlay** is a lightweight (`< 40 MB`) Python + PyQt6 HUD styled after **glassmorphism**: frosted glass, soft shadow, neon accent, a rotating conic border and subtle noise. It floats on top of any window, auto-hides when you are not in a game, and shows everything that matters mid-match:

> **CPU · RAM · GPU (temp & util) · battery · Disk I/O · network (↑/↓ / ping) · now playing · session timer · voice alerts**

Everything is configured without restarting — the `Phantom Control Center` reflects all your changes instantly via a live preview.

---

## ⚡ Features

### 📊 System telemetry
- **CPU / RAM** with animated percentage and sparkline history.
- **GPU (NVIDIA)** — temperature and utilisation via NVML, circular gauge.
- **CPU temp** via `psutil.sensors_temperatures` (coretemp / k10temp / acpitz).
- **Network** — ping to a configurable host + up/down throughput.
- **Disk I/O** — MB/s read & write.
- **Battery** — percent + AC indicator.
- **Clock / uptime** — clock with seconds and session uptime.
- **Peak tracker** — session peaks for CPU / RAM / GPU-temp / Ping.

### 🎨 Visuals
- **Glassmorphism panel** with gradient, radial glow, noise and an optional rotating **conic border**.
- **Glowing particles** on the background (toggleable).
- **Animated values** via `QPropertyAnimation` — no jarring number jumps.
- **Hover micro-animations** — a subtle "lift" on buttons and cards via `QGraphicsDropShadowEffect`.
- **Bundled fonts** — Inter (UI) and JetBrains Mono (digits) shipped in `fonts/` and registered via `QFontDatabase`. If they are missing — falls back to Segoe UI / Consolas.
- **Dynamic colors** — two modes: **steps** (warn/crit thresholds) and **gradient** (smooth `accent → yellow → red` across the whole load range).
- **Theme presets**: Neon Mint, Ultraviolet, Cyber Cyan, Magma, Sakura, Matrix, Stealth, Gold + any custom accent via the palette picker.

### 🎮 Gaming UX
- **Smart Focus** — the overlay only shows when the active window matches a name from your game list (`CS2`, `Valorant`, `Apex`, `Dota 2`, …). The list is editable from the Control Center.
- **Redactable window**: drag mode, corner snap, auto-hide on idle, click-through, always-on-top, lock, three taskbar modes.
- **Three profile slots** (Gaming / Coding / Streaming), each with its own opacity, colors and widget visibility.
- **Profile triggers** via JSON — e.g. `shooter_profile.json` automatically enables the crosshair and bumps opacity whenever CS2 / Valorant becomes the active window.

### 🔊 Integrations
- **Discord Rich Presence** — broadcasts GPU temperature and current track (requires your own Client ID).
- **Windows Media Control** (`winsdk`) — Now Playing + Play/Pause/Next/Prev in the tray.
- **AI assistant Silphiette** — context-aware text statuses: GPU overheat, 100% CPU, high ping, "all systems nominal".
- **Voice alerts** via `pyttsx3` — spoken warning on overheating.
- **Plugins** via Python files in `plugins/` — drop in your own widgets/metrics without touching the core *(loader is on the way, see the [Roadmap](#-roadmap))*.

### ⚙️ Under the hood
- **Cached noise tile** 256×256 + `QBrush` — O(1) per paint regardless of window size.
- **Separate QThread** for hardware monitoring — the UI never freezes.
- **Graceful thread shutdown**, errors logged to stderr with `[phantom][prefix] Type: message`.
- **Localised UI**: Russian / English (switchable in settings).

---

## 🎬 Gallery

> GIFs and screenshots live in [`assets/`](assets/README.md). If a file has not been recorded yet, GitHub will show a broken image — the sections fill in as the assets are added.

<table>
<tr>
<td align="center" width="50%">
<strong>Overlay in CS2</strong><br/>
<img src="assets/overlay_in_game.gif" alt="Overlay over CS2" width="100%" onerror="this.alt='(GIF not recorded yet — see assets/README.md)'" />
</td>
<td align="center" width="50%">
<strong>Settings live preview</strong><br/>
<img src="assets/settings_live.gif" alt="Control Center live preview" width="100%" onerror="this.alt='(GIF not recorded yet — see assets/README.md)'" />
</td>
</tr>
<tr>
<td align="center">
<strong>Theme presets</strong><br/>
<img src="assets/presets.png" alt="Theme presets grid" width="100%" onerror="this.alt='(screenshot not recorded yet)'" />
</td>
<td align="center">
<strong>Compact mode</strong><br/>
<img src="assets/compact_mode.png" alt="Compact mode" width="100%" onerror="this.alt='(screenshot not recorded yet)'" />
</td>
</tr>
</table>

---

## ⬇️ Install for gamers (pre-built .exe)

<div align="center">

### 📥 [Download **PhantomOverlay.exe** — GitHub Releases →](https://github.com/iq28qi/Phantom-Overlay/releases/latest)

</div>

1. Grab `PhantomOverlay.exe` from the [latest release](https://github.com/iq28qi/Phantom-Overlay/releases/latest).
2. Drop it into any folder (e.g. `C:\Phantom\`).
3. *(Optional)* place your own `icon.png` next to it — it becomes the tray icon.
4. Run `PhantomOverlay.exe`. The overlay fades in, a ghost 👻 appears in the tray.
5. Right-click the tray icon → **`⚙ Settings`** → tweak everything.

> All settings are auto-saved into `phantom_config.json` next to the `.exe`. Move that file — your config travels with it.

---

## 🛠 Run from source (for developers)

Requirements: **Python 3.12+**, Windows 10 / 11. Most of the UI renders on Linux / macOS too, but hardware modules (`keyboard`, `winsdk`, `nvml`, `pyttsx3`) are Windows-only.

```bash
git clone https://github.com/iq28qi/Phantom-Overlay.git
cd Phantom-Overlay

python -m venv .venv
.venv\Scripts\activate      # PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
python phantom.py
```

### Build the .exe locally

```bat
build.bat
```

Or by hand:

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

> ⚠️ The `keyboard` library needs elevated privileges for global hotkeys on Windows.

### CI / automated release

The repo ships [`.github/workflows/release.yml`](.github/workflows/release.yml):

- Triggered on pushing a `v*` tag (e.g. `v5.2.0`).
- Builds `PhantomOverlay.exe` with PyInstaller on `windows-latest`.
- Publishes a GitHub Release and attaches the `.exe`.
- Can also be run manually from **Actions → Build & Release → Run workflow** to produce an artifact without a release.

---

## 🎛 Controls & hotkeys

| Action | How |
| --- | --- |
| Toggle overlay | Double-click tray icon **or** `Ctrl + Shift + P` |
| Open settings | Right-click tray → `⚙ Settings` **or** `Ctrl + Shift + O` |
| Drag mode | Tray → `🛠 Drag mode` |
| Media controls | Tray → `⏯ / ⏭ / ⏮` (requires winsdk) |
| Quit | Tray → `❌ Quit` |

All hotkeys are configurable in `Control Center → General`.

---

## 🧩 Themes, presets & color modes

- **Theme presets** — ready-made combos of accent + opacity + particles + compact mode. One click applies instantly.
- **Custom accent** — palette picker or a manual HEX (`#ff3366`, `#22d3ee`, …).
- **Color mode**:
  - `steps` — classic: color snaps at warn (80%) and crit (95%).
  - `gradient` — color glides smoothly `accent → yellow → red` proportionally to load across the whole 0–100% range.
- **Border style**: `solid`, `dashed`, `neon`, `none` + toggleable rotating conic border on top.
- **Window mode**: `auto` / `compact` / `fixed` / `free` — from 380×320 to your own dimensions.
- **Corner snap**: top-left / top-right / bottom-* — the overlay snaps to a corner on launch.

---

## 🔌 Plugins

Plugins live in [`plugins/`](plugins/) and follow a tiny contract:

```python
# plugins/uptime_plugin.py
PLUGIN_META = {
    "name": "Session Uptime",
    "version": "1.0",
    "author": "phantom",
    "description": "Shows overlay uptime",
}

class PhantomPlugin:
    def __init__(self, config: dict): ...
    def on_data(self, data: dict) -> dict: ...   # enrich the shared data dict
    def get_label(self) -> str: ...              # string for the overlay chip
    def on_config_change(self, config: dict): ...
```

> ⚙️ **Status**: the plugin format is frozen and the example `plugins/uptime_plugin.py` works, but the automatic `importlib`-based loader is still in progress ([Roadmap](#-roadmap) → PR3). Until it lands the plugin does not auto-attach.

---

## 🏗 Architecture

For now — a single `phantom.py` (~3600 lines) plus assets. Its sections are marked by heading comments:

```
phantom.py
├── CONFIG            — DEFAULT_CONFIG, load/save, auto-migration
├── TRANSLATIONS      — ru / en dictionaries + tr() / set_language()
├── FONTS             — load_bundled_fonts(), UI_FONT_FAMILY, MONO_FONT_FAMILY
├── COLOR_MODE        — steps/gradient + _color_for_load / _color_for_temp
├── PRIMITIVES        — helpers, Sparkline, Chip, HoverGlow, StatusDot
├── HARDWARE          — HardwareMonitorThread (QThread + NVML + psutil + ping)
├── CORE              — PhantomCore (Discord RPC, TTS, Media via winsdk)
├── WIDGETS           — MetricCard, CircularGauge, Visualizer, PresetCard, ...
├── GLASS_PANEL       — background with cached noise tile and conic border
├── SETTINGS          — ModernSettings (Control Center, 4 tabs + live preview)
├── OVERLAY           — PhantomOverlay (main window + tray + hotkeys)
└── ENTRY             — main(), _install_excepthook()
```

Splitting this monolith into `config.py` / `hardware.py` / `widgets/` / `overlay.py` is planned (see the [Roadmap](#-roadmap)).

---

## 🗺 Roadmap

| # | Task | Status |
| --- | --- | --- |
| ✅ PR1 | Polish & perf: bundled fonts, cached noise tile, hover micro-anim, gradient color mode | [#2](https://github.com/iq28qi/Phantom-Overlay/pull/2) |
| 🧩 PR2 | Repo polish: README, badges, `assets/`, `plugins/`, issue/PR templates, release workflow | this PR |
| 🔌 PR3 | Plugin loader via `importlib` + hot-reload from the Control Center | planned |
| 🎮 PR4 | CS2 Game State Integration (HP / K-D / bomb timer) | planned |
| 💡 PR4 | OpenRGB integration — case lighting reacts to critical alerts | planned |
| 🧱 PR5 | Splitting `phantom.py` into modules (`config.py`, `hardware.py`, `widgets/`, `overlay.py`) | planned |
| 🚀 future | `QOpenGLWidget` backend for `GlassPanel` (only if the FPS ever drops) | exploratory |

---

## 🤝 Contributing

Bug reports and ideas are welcome:

- 🐛 **Bug** — use the [Bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).
- ✨ **Feature / idea** — the [Feature request template](.github/ISSUE_TEMPLATE/feature_request.yml).
- 🛠 **Pull request** — please open an issue first (except for typos / tiny fixes), follow [`PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

Style rules:

- No new dependencies without discussion — `requirements.txt` should stay compact.
- UI strings go into both locales (`ru` + `en`) inside `TRANSLATIONS`.
- Changes to `DEFAULT_CONFIG` must stay backward compatible (old keys keep working, new keys come with a sane default).

---

## 📄 License

[MIT](LICENSE) © 2025 iq28qi. Inter and JetBrains Mono are [SIL Open Font License 1.1](fonts/).
