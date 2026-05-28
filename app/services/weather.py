from __future__ import annotations

import logging
from datetime import datetime

import aiohttp

from app.config import WeatherConfig

logger = logging.getLogger(__name__)

_BASE = "https://api.openweathermap.org/data/2.5"


class WeatherService:
    def __init__(self, config: WeatherConfig) -> None:
        self._config = config
        self._cached_current: dict | None = None
        self._cached_forecast: list[dict] = []
        self._last_fetch: datetime | None = None

    async def fetch(self) -> tuple[dict, list[dict]]:
        q = f"{self._config.city_name},TW"
        current_params = {
            "q": q,
            "appid": self._config.api_key,
            "units": self._config.units,
        }
        forecast_params = {
            "q": q,
            "appid": self._config.api_key,
            "units": self._config.units,
            "cnt": 40,
        }
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{_BASE}/weather", params=current_params, timeout=timeout) as resp:
                resp.raise_for_status()
                current: dict = await resp.json()
            async with session.get(f"{_BASE}/forecast", params=forecast_params, timeout=timeout) as resp:
                resp.raise_for_status()
                forecast_body: dict = await resp.json()

        self._cached_current = current
        self._cached_forecast = forecast_body.get("list", [])
        self._last_fetch = datetime.now()
        logger.info(
            "Weather: %s %.1f°C",
            current.get("weather", [{}])[0].get("description", ""),
            current.get("main", {}).get("temp", 0),
        )
        return self._cached_current, self._cached_forecast

    @property
    def cached_current(self) -> dict | None:
        return self._cached_current

    @property
    def cached_forecast(self) -> list[dict]:
        return self._cached_forecast
