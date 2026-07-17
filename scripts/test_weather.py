"""Hardware test: OpenWeatherMap API. Run on Pi: python -m scripts.test_weather"""
from __future__ import annotations

import asyncio
import sys

from app.config import load_settings
from app.services.weather import WeatherService


async def _run() -> None:
    settings = load_settings()
    if not settings.weather.api_key:
        print("ERROR: weather.api_key not set in config.yaml")
        sys.exit(1)

    print(f"Fetching weather for lat={settings.weather.lat}, lon={settings.weather.lon} ...")
    service = WeatherService(settings.weather)
    current, forecast = await service.fetch()

    desc = current.get("weather", [{}])[0].get("description", "")
    temp = current.get("main", {}).get("temp")
    hum = current.get("main", {}).get("humidity")
    print(f"  Current: {desc}  {temp}°C  humidity={hum}%")
    print(f"  Forecast entries: {len(forecast)}")
    print("PASS")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
