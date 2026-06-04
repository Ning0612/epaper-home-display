from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

from app.display.renderer_constants import DISPLAY_W, DISPLAY_H, BG
from app.display.renderer_cards import (
    _draw_card_weather,
    _draw_card_image,
    _draw_card_indoor,
    _draw_card_agent1,
    _draw_card_usage,
)

# Re-export symbols referenced directly by tests
from app.display.renderer_utils import _load_weather_icon, _draw_progress_bar, _pick_daily_forecast  # noqa: F401

if TYPE_CHECKING:
    from app.config import Settings
    from app.state import AgentState


def render_dashboard(
    state: "AgentState", settings: "Settings", now: datetime | None = None
) -> Image.Image:
    img = Image.new("RGB", (DISPLAY_W, DISPLAY_H), BG)
    draw = ImageDraw.Draw(img)
    if now is None:
        now = datetime.now()

    color = settings.display.is_color
    _draw_card_weather(img, draw, state, now, color=color)
    _draw_card_image(img, draw, state)
    _draw_card_indoor(draw, state, color=color)
    _draw_card_agent1(draw, state)
    _draw_card_usage(draw, state, color=color)

    return img
