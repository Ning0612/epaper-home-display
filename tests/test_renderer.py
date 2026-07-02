from __future__ import annotations

import os
from datetime import datetime

os.environ.setdefault("RPI_MOCK", "1")

import pytest
from PIL import Image, ImageDraw

from app.state import AgentState
from app.config import load_settings
from app.display.renderer import (
    render_dashboard,
    _load_weather_icon,
    _draw_progress_bar,
)
from app.display.renderer_apmode import render_ap_mode_page


@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
def empty_state():
    return AgentState()


def test_render_dashboard_smoke(empty_state, settings):
    img = render_dashboard(empty_state, settings)
    assert img.size == (800, 480)
    assert img.mode == "RGB"


def test_render_full_state(settings):
    s = AgentState()
    s.temperature = 26.3
    s.humidity = 61.0
    s.light_is_bright = True
    s.presence = "OCCUPIED"
    s.weather_current = {
        "weather": [{"main": "Rain", "description": "light rain"}],
        "main": {"temp": 22.3, "feels_like": 20.1},
    }
    s.weather_forecast = [
        {
            "dt_txt": "2099-01-02 12:00:00",
            "weather": [{"main": "Clouds"}],
            "main": {"temp": 24.1},
            "pop": 0.8,
        },
        {
            "dt_txt": "2099-01-03 12:00:00",
            "weather": [{"main": "Clear"}],
            "main": {"temp": 26.0},
            "pop": 0.1,
        },
    ]
    s.claude_usage_5h = 0.62
    s.claude_usage_week = 0.41
    s.codex_usage_5h = None
    s.codex_usage_week = 0.73
    s.active_reminder = "Rain expected — bring umbrella"
    img = render_dashboard(s, settings)
    assert img.size == (800, 480)


def test_load_weather_icon_missing_returns_none():
    result = _load_weather_icon("NonExistentCondition", 56)
    assert result is None


def test_draw_progress_bar_out_of_range_no_exception():
    img = Image.new("RGB", (200, 30), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    _draw_progress_bar(draw, 10, 10, 140, 12, 1.5)
    _draw_progress_bar(draw, 10, 10, 140, 12, -0.5)


def test_render_with_all_usage_none(settings):
    s = AgentState()
    img = render_dashboard(s, settings)
    assert img.size == (800, 480)


def test_render_without_hydra_data(settings):
    img = render_dashboard(AgentState(), settings)
    assert img.size == (800, 480)


def test_render_with_hydra_data(settings):
    s = AgentState()
    s.hydra_current_ml = 1450
    s.hydra_goal_ml = 2000
    s.hydra_pct = 0.725
    s.hydra_updated_at = datetime.now()
    s.hydra_broker_connected = True
    s.hydra_device_online = True
    img = render_dashboard(s, settings)
    assert img.size == (800, 480)


def test_render_hydra_device_online_but_no_status_yet(settings):
    # availability arrived (device_online=True) but status topic never did (current_ml=None)
    s = AgentState()
    s.hydra_broker_connected = True
    s.hydra_device_online = True
    img = render_dashboard(s, settings)
    assert img.size == (800, 480)


def test_render_long_reminder(settings):
    s = AgentState()
    s.active_reminder = "A" * 100
    img = render_dashboard(s, settings)
    assert img.size == (800, 480)


def test_render_ap_mode_page_is_rgb(empty_state, settings):
    img = render_ap_mode_page(empty_state, settings)
    assert img.size == (800, 480)
    assert img.mode == "RGB"
