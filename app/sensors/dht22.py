from __future__ import annotations

import logging
from typing import Protocol

from app.config import DHT22Config

logger = logging.getLogger(__name__)


class DHT22Sensor(Protocol):
    def read(self) -> tuple[float, float]:
        """Return (temperature_celsius, humidity_percent)."""
        ...


class RealDHT22:
    def __init__(self, config: DHT22Config) -> None:
        import adafruit_dht  # type: ignore[import]
        import board  # type: ignore[import]
        pin = getattr(board, f"D{config.gpio_pin}")
        self._device = adafruit_dht.DHT22(pin)

    def read(self) -> tuple[float, float]:
        temp = self._device.temperature
        hum = self._device.humidity
        if temp is None or hum is None:
            raise RuntimeError("DHT22 returned None — retry")
        return float(temp), float(hum)


class MockDHT22:
    def __init__(self, temperature: float = 26.0, humidity: float = 60.0) -> None:
        self._temperature = temperature
        self._humidity = humidity

    def read(self) -> tuple[float, float]:
        return self._temperature, self._humidity


def create_dht22(config: DHT22Config) -> DHT22Sensor:
    if config.use_mock:
        logger.info("DHT22: mock mode")
        return MockDHT22()
    logger.info("DHT22: real sensor on GPIO %d", config.gpio_pin)
    return RealDHT22(config)
