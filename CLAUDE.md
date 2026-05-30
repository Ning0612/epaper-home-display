# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**ePaper Home Display** running on Raspberry Pi Zero 2W with a Waveshare 7.5" e-Paper display, DHT22 sensor, light sensor, button, and buzzer/USB speaker.

Operates independently from Agent 1 and communicates via MQTT.

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
pytest tests/test_presence.py::test_occupied_when_light_bright

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
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_mqtt'
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_weather'
```

---

## Architecture

### Layer Separation (Critical)

Hardware access is strictly separated from business logic:

| Layer | Location | Rule |
|-------|----------|-------|
| Hardware drivers | `app/sensors/`, `app/display/`, `app/services/voice.py` | GPIO, SPI, I2C access only here |
| Business logic | `app/logic/` | No hardware imports; receives data via function args |
| State | `app/state.py` | Single source of truth for shared mutable state |
| WebUI | `app/webui/server.py` | Monitoring/config only, no decision logic |

### Key Data Flows

**Sensor → State → Display:**
```
DHT22/light → app/sensors/ → app/state.py → app/display/renderer.py → epaper.py → hardware
```

**MQTT In → Logic → MQTT Out:**
```
Agent1 publishes home/security/* → app/services/mqtt_client.py → app/logic/ → publish home/home_state/*
```

**Presence Score (app/logic/presence.py):**
```
presence_score = ambient_light_score + recent_door_activity_score + recent_known_user_entry_score
score >= 2 → OCCUPIED | score < 2 → UNOCCUPIED
```

### e-Paper Update Timing

The display is slow — never block MQTT callbacks or WebUI handlers for it:

- Normal dashboard: wall-clock aligned — triggered at `:dashboard_trigger_second` each minute (default :57) so the panel shows the correct minute at :00
- Weather/environment: every 10 minutes
- Security alert: immediately via display_queue
- Refresh cadence: every 10th successful write is a full refresh (init, clears ghosting); the other 9 use init_fast (partial)

### MQTT Topics

Subscribes to: `home/security/door`, `home/security/face`, `home/security/alert`, `home/security/status`

Publishes to: `home/home_state/presence`, `home/home_state/alarm_decision`, `home/display/status`

All payloads are JSON and must include `agent` and `timestamp` fields.

### Mock Pattern for Local Testing

All hardware classes must have a mock counterpart usable without GPIO:

```python
class MockDHT22:
    def read(self) -> tuple[float, float]:
        return 26.3, 61.0
```

Unit tests import mocks; hardware scripts import real drivers. Never let `import RPi.GPIO` execute during `pytest`.

---

## Tech Stack

- **Runtime**: Python 3, systemd service, SQLite, `.venv` virtual environment
- **Web**: FastAPI (WebUI only)
- **MQTT**: paho-mqtt
- **Display**: Pillow (image rendering) + Waveshare Python driver (SPI transport)
- **Tests**: pytest with mocked hardware

Do not use: desktop GUI frameworks, browser automation, anything requiring a monitor on the Pi.

---

## Configuration

Read all runtime values from config file or environment variables. Never hard-code:

```
mqtt_broker_host / mqtt_broker_port
openweathermap_api_key
discord_webhook_url
timezone
dht22_gpio / button_gpio / light_sensor_config
epaper_model
webui_host / webui_port
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
7. MQTT pub/sub works with Agent 1
8. Presence score logic correct
9. e-Paper dashboard renders all data
10. WebUI shows current state
11. SQLite logs all event types
12. systemd starts epaper-home-display on boot
