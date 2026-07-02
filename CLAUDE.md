# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**ePaper Home Display** running on Raspberry Pi Zero 2W with a Waveshare 7.3" e-Paper display (epd7in3e, 7-color ACeP), DHT22 sensor, light sensor, button, and buzzer/USB speaker.

Originally a course final project that integrated with a separate agent ("Agent 1") over MQTT for doorbell/face-recognition security alerts. That integration has been removed from `main` — the historical final-project state is preserved on the `archive/final-project` branch. `main` now covers standalone functionality (local sensors, e-Paper, weather, WebUI, image carousel, Claude/Codex usage display) plus a new, unrelated MQTT integration with [esp32-hydracup](https://github.com/Ning0612/esp32-hydracup) (a smart water cup) for displaying daily water-drinking progress — see [docs/hydracup-mqtt-protocol.md](docs/hydracup-mqtt-protocol.md).

---

## Development Model

Claude Code runs on the **laptop**. The Raspberry Pi is only the deployment and hardware test target.

```
Laptop  →  edit code, run unit tests (mocked), commit
Pi Zero →  git pull, run hardware tests, run epaper-home-display service
```

Do not assume Claude Code is installed on the Pi. Use SSH for Pi-side execution.

Pi hostname: `pi@epaper-display.local`

### Pi Execution Policy

- **Non-sudo commands** (git pull, pip install, journalctl, python scripts): Claude executes directly via SSH.
- **sudo commands** (systemctl restart/enable/daemon-reload, cp to /etc/systemd/): Claude cannot run these — provide the exact command and ask the user to run it manually (e.g. `! ssh pi@epaper-display.local 'sudo systemctl restart epaper-home-display'`).

---

## Common Commands

### Local (Laptop)

```bash
# Run all unit tests
pytest

# Run a single test file
pytest tests/test_presence.py

# Run a single test function
pytest tests/test_presence.py::test_light_dark_is_occupied

# Syntax-check a modified file
./.venv/Scripts/python.exe -m py_compile app/logic/presence.py

# Compile-check a whole directory
./.venv/Scripts/python.exe -m compileall app/
```

### Deploy & Operate (Pi via SSH)

```bash
# Deploy latest code (manual / emergency only — Pi auto-updates within 5 min after push)
ssh pi@epaper-display.local 'cd ~/epaper-home-display && git pull'

# Install/update dependencies
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/pip install -r requirements.txt'

# Restart service
ssh pi@epaper-display.local 'sudo systemctl restart epaper-home-display'

# Check service status
ssh pi@epaper-display.local 'systemctl status epaper-home-display --no-pager'

# Tail logs
ssh pi@epaper-display.local 'journalctl -u epaper-home-display -n 100 --no-pager'
ssh pi@epaper-display.local 'journalctl -u epaper-home-display -f'

# Auto-update logs
ssh pi@epaper-display.local 'journalctl -t epaper-auto-update -n 50 --no-pager'

# Auto-update timer status
ssh pi@epaper-display.local 'systemctl list-timers epaper-auto-update.timer --no-pager'
```

### Hardware Tests (Pi)

```bash
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_epaper'
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_dht22'
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_light'
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_button'
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_speaker'
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_weather'
```

---

## Architecture

### Layer Separation (Critical)

Hardware access is strictly separated from business logic:

| Layer | Location | Rule |
|-------|----------|-------|
| Hardware drivers | `app/sensors/`, `app/display/`, `app/services/voice.py` | GPIO, SPI, I2C access only here |
| Network services | `app/services/` (weather, MQTT, Discord, usage polling) | External I/O only; writes to `state.py`, never decides display behavior |
| Business logic | `app/logic/` | No hardware/network imports; receives data via function args |
| State | `app/state.py` | Single source of truth for shared mutable state |
| WebUI | `app/webui/server.py` | Monitoring/config only, no decision logic |

### Key Data Flows

**Sensor → State → Display:**
```
DHT22/light → app/sensors/ → app/state.py → app/display/renderer.py → epaper.py → hardware
```

**Presence Score (app/logic/presence.py):**
```
light_raw < bright_threshold → OCCUPIED  (score = 1.0)
light_raw ≥ bright_threshold → UNOCCUPIED (score = 0.0)
```

**HydraCup MQTT → State → Display:**
```
esp32-hydracup → Mosquitto broker (Pi, :1883) → app/services/mqtt_client.py (paho-mqtt, background thread)
  → app/logic/hydration.py (parse_status, pure) → app/state.py (hydra_*) → renderer_cards.py::_draw_card_hydra()
```
`MQTTService.start()`/`.stop()` are wired in `app/main.py` around the `asyncio.gather()` call — paho-mqtt runs its own background thread (`loop_start()`), so it is not itself a gathered coroutine. Full protocol spec: [docs/hydracup-mqtt-protocol.md](docs/hydracup-mqtt-protocol.md).

### e-Paper Update Timing

The display is slow — never block WebUI handlers for it:

- Normal dashboard: wall-clock aligned to `dashboard_interval_minutes` boundaries (default every 5 min). Trigger second is auto-derived per model: `epd7in3e`→40 (full refresh ~20s), `epd7in5_V2`→57 (fast refresh ~0.3s). Not user-configurable.
- Weather/environment: every 10 minutes
- Refresh cadence: every `full_refresh_every` (default 10) successful writes is a full refresh (init, clears ghosting); others use init_fast (partial). Note: `epd7in3e` has no init_fast — every write is a full refresh.

### Buttons

GPIO wiring still has 4 physical buttons (`sensors.button.gpio_pins`, at least 4 entries required), but only Button 1 (GPIO 5) is bound to a handler (`_handle_btn_dashboard`: force OCCUPIED + switch to dashboard). Buttons 2–4 are reserved pins left over from the retired Agent 1 integration — no callback is registered for them.

### Mock Pattern for Local Testing

All hardware classes must have a mock counterpart usable without GPIO:

```python
class MockDHT22:
    def read(self) -> tuple[float, float]:
        return 26.3, 61.0
```

Unit tests import mocks; hardware scripts import real drivers. Never let `import RPi.GPIO` execute during `pytest`.

### Display Preview Rule

**Any change to `app/display/` must be verified by rendering a preview PNG before reporting the task as done.**

Run after every display-related edit:

```bash
./.venv/Scripts/python.exe -m scripts.preview_render
```

Saves `preview_dashboard.png`, `preview_apmode.png` in `docs/images/`.
Mock data includes: indoor sensors, Claude/Codex usage with reset times, current weather + 4-day forecast.
To adjust mock data, edit `scripts/preview_render.py`.

Open and visually inspect the saved PNGs. Check: layout intact, text readable, no clipped elements, correct image mode (RGB). Do not skip this step even for small tweaks.

---

## Tech Stack

- **Runtime**: Python 3, systemd service, SQLite, `.venv` virtual environment
- **Web**: FastAPI (WebUI only)
- **Display**: Pillow (image rendering) + Waveshare Python driver (SPI transport)
- **Tests**: pytest with mocked hardware

Do not use: desktop GUI frameworks, browser automation, anything requiring a monitor on the Pi.

---

## Configuration

Read all runtime values from config file or environment variables. Never hard-code (shorthand names below — actual nested YAML keys are in `config.example.yaml`):

```
openweathermap_api_key
discord_webhook_url
timezone
dht22_gpio / button_gpio / light_sensor_config
epaper_model
webui_host / webui_port
mqtt.broker_host / mqtt.username / mqtt.password
```

Reference file: `config.example.yaml`

---

## Deployment Checklist

Pi has an auto-update timer (`epaper-auto-update.timer`) that polls every 5 minutes. After `git push`, the Pi will pull and restart automatically — no manual SSH needed.

```bash
pytest && git status && git diff          # verify locally first
git push                                  # Pi auto-updates within 5 minutes

# Optional: confirm update applied
ssh pi@epaper-display.local 'journalctl -t epaper-auto-update -n 10 --no-pager'
ssh pi@epaper-display.local 'journalctl -u epaper-home-display -n 50 --no-pager'
```

Manual deploy (if auto-update not set up or for emergency):
```bash
ssh pi@epaper-display.local 'cd ~/epaper-home-display && git pull'
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/pip install -r requirements.txt'
ssh pi@epaper-display.local 'sudo systemctl restart epaper-home-display'
```

Do not add features until the service starts cleanly after each deploy.

---

## Minimum Viable Build Order

1. Pi boots, SSH works, venv works
2. e-Paper displays test screen
3. DHT22 reads temperature/humidity
4. Light sensor produces usable state
5. Button input works
6. Weather API returns data
7. Presence score logic correct
8. e-Paper dashboard renders all data
9. WebUI shows current state
10. SQLite logs all event types
11. systemd starts epaper-home-display on boot
