from __future__ import annotations

import logging
from typing import Callable, Protocol

from app.config import ButtonConfig

logger = logging.getLogger(__name__)


class ButtonSensor(Protocol):
    def is_pressed(self) -> bool: ...
    def register_callback(self, fn: Callable[[], None]) -> None: ...


class RealButton:
    def __init__(self, config: ButtonConfig) -> None:
        # gpiozero uses lgpio backend on Bookworm/Trixie and avoids the
        # RPi.GPIO add_event_detect incompatibility on newer Pi OS versions.
        from gpiozero import Button as _GZButton  # type: ignore[import]
        self._btn = _GZButton(config.gpio_pin, pull_up=True, bounce_time=0.2)

    def is_pressed(self) -> bool:
        return bool(self._btn.is_pressed)

    def register_callback(self, fn: Callable[[], None]) -> None:
        self._btn.when_pressed = fn


class MockButton:
    def __init__(self) -> None:
        self._pressed = False
        self._callback: Callable[[], None] | None = None

    def is_pressed(self) -> bool:
        return self._pressed

    def register_callback(self, fn: Callable[[], None]) -> None:
        self._callback = fn

    def simulate_press(self) -> None:
        self._pressed = True
        if self._callback:
            self._callback()
        self._pressed = False


def create_button(config: ButtonConfig) -> ButtonSensor:
    if config.use_mock:
        logger.info("Button: mock mode")
        return MockButton()
    logger.info("Button: GPIO pin %d", config.gpio_pin)
    return RealButton(config)
