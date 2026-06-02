"""Render preview PNGs for all display pages with representative mock data."""
from __future__ import annotations

import os
os.environ.setdefault("RPI_MOCK", "1")

from datetime import datetime, timedelta, timezone

from app.config import load_settings
from app.state import AgentState
from app.display.renderer import render_dashboard
from app.display.renderer_alert import render_alert_page
from app.display.renderer_apmode import render_ap_mode_page
from app.display.image_processor import quantize_to_epaper_palette


def _make_state() -> AgentState:
    st = AgentState()

    st.temperature = 26.3
    st.humidity = 61.0
    st.presence = "OCCUPIED"

    # Claude usage with reset times
    st.claude_usage_5h = 0.62
    st.claude_usage_week = 0.41
    st.claude_5h_reset = "14:30"
    st.claude_7d_reset = "3d 2h"

    # Codex usage with reset times
    st.codex_usage_5h = 0.35
    st.codex_usage_week = 0.73
    st.codex_5h_reset = "16:45"
    st.codex_7d_reset = "5d 0h"

    # Current weather
    st.weather_current = {
        "weather": [{"main": "Rain", "description": "light rain"}],
        "main": {"temp": 22.3, "feels_like": 20.1},
    }

    # 4-day forecast — dt_txt is interpreted as UTC by _pick_daily_forecast,
    # which converts to host local timezone (not settings.timezone).
    base = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    conditions = ["Clouds", "Clear", "Rain", "Clouds"]
    temps     = [24.5, 28.0, 21.0, 23.5]
    pops      = [0.30, 0.05, 0.80, 0.40]
    st.weather_forecast = [
        {
            "dt_txt": (base + timedelta(days=i + 1)).strftime("%Y-%m-%d %H:%M:%S"),
            "weather": [{"main": conditions[i]}],
            "main": {"temp": temps[i]},
            "pop": pops[i],
        }
        for i in range(4)
    ]

    # Agent1 events
    st.last_door_event = {"state": "CLOSED"}
    st.last_face_event = {"identity": "lance"}
    st.last_alert = {"level": "NONE"}

    return st


if __name__ == "__main__":
    s = load_settings()
    st = _make_state()

    quantize_to_epaper_palette(render_dashboard(st, s)).save("preview_dashboard.png")
    quantize_to_epaper_palette(render_alert_page(st, s)).save("preview_alert.png")
    quantize_to_epaper_palette(render_ap_mode_page(st, s)).save("preview_apmode.png")

    print("Saved: preview_dashboard.png  preview_alert.png  preview_apmode.png")
