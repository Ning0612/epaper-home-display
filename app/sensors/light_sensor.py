from __future__ import annotations

import logging
from typing import Protocol

from app.config import LightConfig

logger = logging.getLogger(__name__)

_LUX_SCALE = 0.098  # rough lux approximation: raw_value * scale


class LightSensor(Protocol):
    def read_raw(self) -> int:
        """Return 10-bit ADC value (0–1023) from MCP3008."""
        ...

    def read_lux(self) -> float:
        """Return approximate lux value."""
        ...

    def is_bright(self, threshold: int) -> bool:
        """Return True when raw reading is at or above threshold."""
        ...


class RealLightSensor:
    """MCP3008 10-bit ADC connected via SPI (spidev)."""

    def __init__(self, config: LightConfig) -> None:
        import spidev  # type: ignore[import]
        self._spi = spidev.SpiDev()
        self._spi.open(config.spi_bus, config.spi_device)
        self._spi.max_speed_hz = 1_350_000
        self._channel = config.adc_channel

    def read_raw(self) -> int:
        r = self._spi.xfer2([1, (8 + self._channel) << 4, 0])
        return ((r[1] & 3) << 8) + r[2]

    def read_lux(self) -> float:
        return round(self.read_raw() * _LUX_SCALE, 1)

    def is_bright(self, threshold: int) -> bool:
        return self.read_raw() >= threshold


class MockLightSensor:
    def __init__(self, raw: int = 600) -> None:
        self._raw = raw

    def read_raw(self) -> int:
        return self._raw

    def read_lux(self) -> float:
        return round(self._raw * _LUX_SCALE, 1)

    def is_bright(self, threshold: int) -> bool:
        return self._raw >= threshold


def create_light_sensor(config: LightConfig) -> LightSensor:
    if config.use_mock:
        logger.info("LightSensor: mock mode")
        return MockLightSensor()
    logger.info(
        "LightSensor: MCP3008 SPI bus=%d dev=%d ch=%d",
        config.spi_bus, config.spi_device, config.adc_channel,
    )
    return RealLightSensor(config)
