from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.services.weather import WeatherService
from app.state import state

logger = logging.getLogger(__name__)


async def _weather_loop(weather_service: WeatherService, settings) -> None:
    while True:
        try:
            current, forecast = await weather_service.fetch()
            state.weather_current = current
            state.weather_forecast = forecast
            state.weather_fetched_at = datetime.now()
        except Exception as exc:
            logger.warning("Weather fetch failed (using cached data): %s", exc)
        await asyncio.sleep(settings.weather.fetch_interval_seconds)
