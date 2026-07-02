"""Render preview PNGs for all display pages with representative mock data."""
from __future__ import annotations

import os
os.environ.setdefault("RPI_MOCK", "1")

from datetime import datetime, timedelta, timezone

from app.config import load_settings
from app.state import AgentState
from app.display.renderer import render_dashboard
from app.display.renderer_apmode import render_ap_mode_page
from app.display.image_processor import quantize_to_epaper_palette


def _make_state() -> AgentState:
    st = AgentState()

    st.temperature = 31.5   # ≥30 → Red; change to 26.3 (normal) or 13.0 (blue) to test other zones
    st.humidity = 61.0
    st.presence = "OCCUPIED"

    # Claude usage — 5h: 85% red (≥80), 7d: 41% green (<60)
    st.claude_usage_5h = 0.85
    st.claude_usage_week = 0.41
    st.claude_5h_reset = "14:30"
    st.claude_7d_reset = "3d 2h"

    # Codex usage — 5h: 35% green (<60), 7d: 73% yellow (60–80)
    st.codex_usage_5h = 0.35
    st.codex_usage_week = 0.73
    st.codex_5h_reset = "16:45"
    st.codex_7d_reset = "5d 0h"

    # Current weather — 22°C (black, normal range)
    st.weather_current = {
        "weather": [{"main": "Rain", "description": "light rain"}],
        "main": {"temp": 22.3, "feels_like": 20.1},
    }

    # 4-day forecast — spans all three color zones:
    #   31° red (≥30), 28° black (normal), 13° blue (≤15), 24° black (normal)
    # dt_txt is interpreted as UTC by _pick_daily_forecast,
    # which converts to host local timezone (not settings.timezone).
    base = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    conditions = ["Clear", "Clouds", "Snow",  "Clouds"]
    temps     = [31.0,   28.0,    13.0,   24.0]
    pops      = [0.05,   0.30,    0.70,   0.20]
    st.weather_forecast = [
        {
            "dt_txt": (base + timedelta(days=i + 1)).strftime("%Y-%m-%d %H:%M:%S"),
            "weather": [{"main": conditions[i]}],
            "main": {"temp": temps[i]},
            "pop": pops[i],
        }
        for i in range(4)
    ]

    return st


if __name__ == "__main__":
    import os
    s = load_settings()
    st = _make_state()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "images")
    os.makedirs(out_dir, exist_ok=True)

    quantize_to_epaper_palette(render_dashboard(st, s)).save(os.path.join(out_dir, "preview_dashboard.png"))
    quantize_to_epaper_palette(render_ap_mode_page(st, s)).save(os.path.join(out_dir, "preview_apmode.png"))

    print("Saved: docs/images/preview_dashboard.png  preview_apmode.png")
