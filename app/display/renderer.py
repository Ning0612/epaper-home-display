from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from app.config import Settings
    from app.state import AgentState

logger = logging.getLogger(__name__)

DISPLAY_W, DISPLAY_H = 800, 480
BG = 255  # white
FG = 0    # black

_FONT_CACHE: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
_FONT_PATH = "assets/fonts/DejaVuSans.ttf"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = ImageFont.truetype(_FONT_PATH, size)
        except (IOError, OSError):
            _FONT_CACHE[size] = ImageFont.load_default()
    return _FONT_CACHE[size]


def render_dashboard(state: "AgentState", settings: "Settings") -> Image.Image:
    img = Image.new("L", (DISPLAY_W, DISPLAY_H), BG)
    draw = ImageDraw.Draw(img)

    now = datetime.now()
    _draw_header(draw, state, now)
    _draw_env(draw, state)
    _draw_weather(draw, state)
    _draw_reminder(draw, state)
    _draw_footer(draw, state)

    return img


def _draw_header(draw: ImageDraw.ImageDraw, state: "AgentState", now: datetime) -> None:
    draw.text((10, 10), now.strftime("%a %Y-%m-%d  %H:%M"), font=_font(28), fill=FG)
    draw.text((560, 10), f"● {state.presence}", font=_font(24), fill=FG)
    if state.last_alert:
        draw.text((710, 10), "⚠ ALERT", font=_font(22), fill=FG)
    draw.line([(0, 52), (DISPLAY_W, 52)], fill=FG, width=1)


def _draw_env(draw: ImageDraw.ImageDraw, state: "AgentState") -> None:
    temp = f"{state.temperature:.1f}°C" if state.temperature is not None else "--°C"
    hum = f"{state.humidity:.0f}%" if state.humidity is not None else "--%"
    light = "bright" if state.light_is_bright else "dim"
    draw.text((10, 62), f"Temp: {temp}   Hum: {hum}   Light: {light}", font=_font(26), fill=FG)
    draw.line([(0, 100), (DISPLAY_W, 100)], fill=FG, width=1)


def _draw_weather(draw: ImageDraw.ImageDraw, state: "AgentState") -> None:
    y = 110
    if not state.weather_current:
        draw.text((10, y), "Weather: unavailable", font=_font(24), fill=FG)
        draw.line([(0, 175), (DISPLAY_W, 175)], fill=FG, width=1)
        return
    w = state.weather_current
    desc = w.get("weather", [{}])[0].get("description", "")
    temp = w.get("main", {}).get("temp", "--")
    feels = w.get("main", {}).get("feels_like", "--")
    draw.text((10, y), f"Weather: {desc}  {temp}°C  Feels {feels}°C", font=_font(24), fill=FG)
    if state.weather_forecast:
        temps = [str(e.get("main", {}).get("temp", "--")) for e in state.weather_forecast[:4]]
        draw.text((10, y + 34), "Next: " + "  ".join(f"{t}°C" for t in temps), font=_font(20), fill=FG)
    draw.line([(0, 175), (DISPLAY_W, 175)], fill=FG, width=1)


def _draw_reminder(draw: ImageDraw.ImageDraw, state: "AgentState") -> None:
    reminder = state.active_reminder or "No reminders"
    draw.text((10, 185), f"Reminder: {reminder}", font=_font(24), fill=FG)
    draw.line([(0, 228), (DISPLAY_W, 228)], fill=FG, width=1)


def _draw_footer(draw: ImageDraw.ImageDraw, state: "AgentState") -> None:
    y = 238
    door_str = "Door: --"
    if state.last_door_event:
        ts = state.last_door_event.get("timestamp", "")
        st = state.last_door_event.get("state", "")
        door_str = f"Door: {st} {ts[-8:-3] if len(ts) >= 8 else ts}"

    face_str = "Face: --"
    if state.last_face_event:
        identity = state.last_face_event.get("identity", "unknown")
        ts = state.last_face_event.get("timestamp", "")
        face_str = f"Face: {identity} {ts[-8:-3] if len(ts) >= 8 else ts}"

    draw.text((10, y), door_str, font=_font(22), fill=FG)
    draw.text((420, y), face_str, font=_font(22), fill=FG)
