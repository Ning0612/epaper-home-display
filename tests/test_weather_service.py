from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import WeatherConfig
from app.display.renderer import _pick_daily_forecast
from app.services.weather import WeatherService


@pytest.fixture
def config():
    return WeatherConfig(api_key="test_key", lat=25.05, lon=121.53)


def _make_mock_response(json_data: dict):
    resp = AsyncMock()
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value=json_data)
    return resp


@pytest.mark.asyncio
async def test_fetch_returns_current_and_forecast(config):
    mock_current = {
        "weather": [{"id": 800, "description": "clear sky"}],
        "main": {"temp": 25.0, "feels_like": 24.0, "humidity": 60},
    }
    mock_forecast = {
        "list": [
            {"weather": [{"id": 800}], "main": {"temp": 24.0}},
            {"weather": [{"id": 500}], "main": {"temp": 20.0}},
        ]
    }

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.get = MagicMock(side_effect=[
        _make_mock_response(mock_current),
        _make_mock_response(mock_forecast),
    ])

    with patch("app.services.weather.aiohttp.ClientSession", return_value=mock_session):
        service = WeatherService(config)
        current, forecast = await service.fetch()

    assert current["main"]["temp"] == 25.0
    assert len(forecast) == 2
    assert service.cached_current is current


@pytest.mark.asyncio
async def test_forecast_returns_all_slots(config):
    many_entries = [{"weather": [{"id": 800}], "main": {"temp": float(i)}, "dt_txt": f"2026-06-0{(i//8)+1} {(i%8)*3:02d}:00:00"} for i in range(40)]
    mock_current = {"weather": [{"id": 800}], "main": {"temp": 22.0}}
    mock_forecast = {"list": many_entries}

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.get = MagicMock(side_effect=[
        _make_mock_response(mock_current),
        _make_mock_response(mock_forecast),
    ])

    with patch("app.services.weather.aiohttp.ClientSession", return_value=mock_session):
        service = WeatherService(config)
        _, forecast = await service.fetch()

    assert len(forecast) == 40

    calls = mock_session.get.call_args_list
    assert len(calls) == 2
    params_current = calls[0][1]["params"]
    params_forecast = calls[1][1]["params"]
    assert params_current["lat"] == 25.05
    assert params_current["lon"] == 121.53
    assert params_forecast["lat"] == 25.05
    assert params_forecast["lon"] == 121.53
    assert params_forecast["cnt"] == 40


def _make_slots(day_offset: int, conditions: list[str], temps: list[float], pops: list[float]) -> list[dict]:
    d = (date.today() + timedelta(days=day_offset)).strftime("%Y-%m-%d")
    return [
        {"dt_txt": f"{d} {i*3:02d}:00:00", "weather": [{"main": c}], "main": {"temp": t}, "pop": p}
        for i, (c, t, p) in enumerate(zip(conditions, temps, pops))
    ]


def test_pick_daily_forecast_aggregation():
    # Rain×4, Clear×3, Thunderstorm×1 → mode is Rain; avg temp = 21°; max pop = 0.8
    slots = (
        _make_slots(1, ["Rain", "Rain", "Clear", "Rain", "Thunderstorm", "Rain", "Clear", "Clear"], [20, 22, 21, 19, 18, 20, 23, 25], [0.3, 0.5, 0.0, 0.5, 0.8, 0.6, 0.1, 0.0]) +
        _make_slots(2, ["Clouds"] * 8, [15.0] * 8, [0.1] * 8)
    )
    result = _pick_daily_forecast(slots, count=4)

    assert len(result) == 2

    day1 = result[0]
    assert day1["weather"][0]["main"] == "Rain"
    assert abs(day1["main"]["temp"] - sum([20, 22, 21, 19, 18, 20, 23, 25]) / 8) < 0.01
    assert day1["pop"] == 0.8

    day2 = result[1]
    assert day2["weather"][0]["main"] == "Clouds"
    assert day2["main"]["temp"] == pytest.approx(15.0)


def test_pick_daily_forecast_skips_today():
    today_slots = _make_slots(0, ["Clear"] * 8, [30.0] * 8, [0.0] * 8)
    tomorrow_slots = _make_slots(1, ["Rain"] * 8, [25.0] * 8, [0.5] * 8)
    result = _pick_daily_forecast(today_slots + tomorrow_slots, count=4)
    assert len(result) == 1
    assert result[0]["weather"][0]["main"] == "Rain"


def test_pick_daily_forecast_handles_none_dt_txt():
    bad_slots = [{"dt_txt": None, "weather": [{"main": "Clear"}], "main": {"temp": 20.0}, "pop": 0.0}]
    good_slots = _make_slots(1, ["Clouds"] * 2, [18.0, 19.0], [0.2, 0.3])
    result = _pick_daily_forecast(bad_slots + good_slots, count=4)
    assert len(result) == 1
    assert result[0]["weather"][0]["main"] == "Clouds"


def test_pick_daily_forecast_severe_weather_wins_tie():
    # Thunderstorm×3 = Clear×3, Rain×2 → tie → Thunderstorm wins by severity
    slots = _make_slots(1, ["Clear", "Clear", "Rain", "Rain", "Thunderstorm", "Thunderstorm", "Thunderstorm", "Clear"], [20.0] * 8, [0.5] * 8)
    result = _pick_daily_forecast(slots, count=1)
    assert result[0]["weather"][0]["main"] == "Thunderstorm"
