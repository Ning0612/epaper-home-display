from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import WeatherConfig
from app.services.weather import WeatherService


@pytest.fixture
def config():
    return WeatherConfig(api_key="test_key", city_id=1668341)


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
async def test_forecast_capped_at_eight(config):
    many_entries = [{"weather": [{"id": 800}], "main": {"temp": float(i)}} for i in range(20)]
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

    assert len(forecast) == 8
