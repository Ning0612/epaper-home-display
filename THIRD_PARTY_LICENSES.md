# Third-Party Licenses

This document covers all third-party components used in this project, organized by how they are distributed:

- **Bundled in git** — source files or binaries checked into this repository
- **Install separately** — fonts or pip packages installed outside the repo
- **CDN-loaded** — JavaScript/CSS/fonts fetched by the browser at runtime (WebUI only)
- **Subprocess / system tools** — external OS binaries called at runtime, never bundled

---

## 1. Bundled in Repository

### 1.1 Weather Icons (modified)

**Location**: `assets/weather_icons/` (`.svg`, `.png`)
**Original**: [erikflowers/weather-icons](https://github.com/erikflowers/weather-icons)
**Copyright**: Copyright (C) 2014 Erik Flowers
**License**: [SIL Open Font License 1.1 (OFL-1.1)](assets/weather_icons/LICENSE)

Modifications: selected subset, SVG paths redrawn for 64×64 grid, exported to PNG via Inkscape.
Full attribution and OFL-1.1 license text are in `assets/weather_icons/LICENSE`.

### 1.2 Waveshare e-Paper Python Library

**Location**: `lib/waveshare_epd/` (`epdconfig.py`, `epd7in3e.py`, `epd7in5_V2.py`)
**Original**: [waveshare/e-Paper](https://github.com/waveshare/e-Paper)
**Copyright**: Waveshare team
**License**: MIT License (full text in each source file header)

Included as-is to avoid a runtime dependency on a package not published on PyPI.

---

## 2. Fonts (not bundled — install separately)

### DejaVu Sans / DejaVu Sans Bold

**Location**: `assets/fonts/` (excluded from version control via `.gitignore`)
**Original**: [dejavu-fonts/dejavu-fonts](https://github.com/dejavu-fonts/dejavu-fonts)
**Derived from**: Bitstream Vera Fonts — Copyright (C) 2003 Bitstream, Inc.
**License**: [Bitstream Vera Fonts License](https://dejavu-fonts.github.io/License.html) (permissive)

Install on Raspberry Pi OS:
```bash
sudo apt install fonts-dejavu-core
cp /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf assets/fonts/
cp /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf assets/fonts/
```

---

## 3. Python Runtime Dependencies

Installed via `pip install -r requirements.txt`; not bundled in this repository.

### 3.1 Core Runtime

| Package | Version req. | License | Notes |
|---------|-------------|---------|-------|
| fastapi | ≥0.115 | MIT | Web framework |
| uvicorn[standard] | ≥0.30 | BSD-3-Clause | ASGI server |
| pyyaml | ≥6.0 | MIT | Config parsing |
| pillow | ≥10.4 | MIT-CMU（本專案套件中繼資料標示；歷史上常標為 HPND，現行版本已改為 MIT-CMU） | Image rendering |
| aiohttp | ≥3.9 | Apache-2.0 AND MIT（本專案套件中繼資料標示，dual-component） | Async HTTP client |
| aiosqlite | ≥0.20 | MIT | Async SQLite |
| passlib[bcrypt] | ≥1.7.4 | BSD-2-Clause (passlib) + Apache-2.0 (bcrypt) | Password hashing |
| python-multipart | ≥0.0.9 | Apache-2.0 | File upload parsing |
| paho-mqtt | ≥2.1 | EPL-2.0 OR BSD-3-Clause（dual-licensed，本專案套件中繼資料標示） | MQTT client (HydraCup + Bambu Lab printer integrations) |
| tzdata | ≥2024.1（僅 Windows，`platform_system == "Windows"` 條件相依） | Apache-2.0 | Windows 無系統 IANA 時區資料庫，補上供 `zoneinfo` 使用；Pi 用系統內建 tzdata |

### 3.2 Pi-only Hardware Packages

Install on Raspberry Pi only (not in `requirements.txt` for laptop dev):

| Package | License | Usage |
|---------|---------|-------|
| adafruit-circuitpython-dht | MIT | DHT22 temperature/humidity |
| spidev | MIT | SPI bus access |
| RPi.GPIO | MIT | GPIO control |
| gpiozero | BSD-3-Clause | Button input handling |

### 3.3 Dev / Test Only

| Package | License | Usage |
|---------|---------|-------|
| pytest | MIT | Test runner |
| pytest-asyncio | Apache-2.0 | Async test support |

---

## 4. External Runtime System Tools (not bundled)

All tools below are invoked as **separate OS processes** via `subprocess` or
`asyncio.create_subprocess_exec()`. No source code is bundled or modified.

Per the [GNU GPL FAQ on fork/exec](https://www.gnu.org/licenses/gpl-faq.html#GPLAndInterpreted):
a simple fork/exec with no shared complex data structures does not make this
MIT-licensed project a derivative work of GPL software. The project's MIT license
is unaffected by calling these tools.

> **SD card / Docker image note**: if you distribute a pre-built system image that
> *includes* GPL binaries (e.g., espeak-ng, alsa-utils), you must fulfil each
> tool's binary distribution obligations — retain copyright notices and, for GPL
> programs, provide or reference the upstream distro source packages.
> The recommended deployment is to have users install tools via `apt` themselves.

### 4.1 TTS & Audio

| Tool | Package | License | Usage in project |
|------|---------|---------|-----------------|
| `espeak-ng` | espeak-ng | GPL-3.0+ | Text-to-speech synthesis (`voice.py`) |
| `aplay` | alsa-utils | GPL-2.0+ | WAV file playback (`voice.py`) |
| `amixer` | alsa-utils | GPL-2.0+ | ALSA volume control (`voice.py`) |

Optional alternative audio players (allow-listed in `voice.py`, not required):
`mpg123` (LGPL-2.1+), `mpg321` (GPL-2.0+), `omxplayer` (GPL-2.0+), `paplay` (LGPL-2.1+), `cvlc` (LGPL-2.1+).

Install on Pi:
```bash
sudo apt install espeak-ng alsa-utils
```

### 4.2 WiFi Management

| Tool | Package | License | Usage in project |
|------|---------|---------|-----------------|
| `nmcli` | NetworkManager | LGPL-2.1+ | WiFi scan & connect (`wifi.py`, `wifi_monitor.py`) |
| `iwgetid` | wireless-tools | GPL-2.0+ | Query current SSID (`routes/settings.py`) |
| `iwconfig` | wireless-tools | GPL-2.0+ | Query signal strength (`routes/settings.py`) |

---

## 5. External APIs and Data Services

These are remote network services used at runtime. No source code or data is
bundled; their respective terms of service apply independently.

| Service | Purpose | Reference |
|---------|---------|-----------|
| OpenWeatherMap API | Current weather + forecast | [Terms of Service](https://openweathermap.org/terms) (attribution required on free tier) |
| Discord Webhook API | Push notifications | [Discord Developer ToS](https://discord.com/developers/docs/policies-and-agreements/developer-terms-of-service) |
| Anthropic API | Claude usage polling (OAuth) | [Anthropic Usage Policy](https://www.anthropic.com/legal/usage-policy) |
| OpenAI API | Codex usage polling (OAuth) | [OpenAI Usage Policy](https://openai.com/policies/usage-policies) |

---

## Summary

| Component | In git | License | Distribution type |
|-----------|--------|---------|-------------------|
| Weather Icons (modified) | ✅ `.svg` `.png` | OFL-1.1 | Bundled |
| Waveshare e-Paper driver | ✅ `.py` | MIT | Bundled |
| DejaVu fonts | ❌ gitignored | Bitstream Vera | Install separately (`apt`) |
| fastapi, uvicorn, PyYAML … | ❌ pip | MIT / Apache-2.0 / BSD | Install via pip |
| Pillow | ❌ pip | MIT-CMU | Install via pip |
| aiohttp | ❌ pip | Apache-2.0 AND MIT | Install via pip |
| passlib + bcrypt | ❌ pip | BSD-2-Clause + Apache-2.0 | Install via pip |
| paho-mqtt | ❌ pip | EPL-2.0 OR BSD-3-Clause | Install via pip |
| tzdata | ❌ pip（僅 Windows，`platform_system == "Windows"`） | Apache-2.0 | Install via pip |
| espeak-ng | ❌ system | GPL-3.0+ | subprocess — separate process |
| alsa-utils (aplay / amixer) | ❌ system | GPL-2.0+ | subprocess — separate process |
| NetworkManager (nmcli) | ❌ system | LGPL-2.1+ | subprocess — separate process |
| wireless-tools (iwgetid / iwconfig) | ❌ system | GPL-2.0+ | subprocess — separate process |
