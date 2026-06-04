from __future__ import annotations

import logging
from typing import Callable, Protocol

from app.config import ButtonConfig

logger = logging.getLogger(__name__)


class ButtonSensor(Protocol):
    def register_callback(self, index: int, fn: Callable[[], None]) -> None: ...


class MultiButton:
    """Wraps multiple gpiozero.Button instances, one per GPIO pin."""

    def __init__(self, config: ButtonConfig) -> None:
        from gpiozero import Button as _GZButton  # type: ignore[import]
        self._buttons = [
            _GZButton(pin, pull_up=True, bounce_time=0.2)
            for pin in config.gpio_pins
        ]
        logger.info("Buttons: %d physical buttons on GPIO %s", len(self._buttons), config.gpio_pins)

    def register_callback(self, index: int, fn: Callable[[], None]) -> None:
        self._buttons[index].when_pressed = fn


class MockButton:
    def __init__(self, count: int = 4) -> None:
        self._callbacks: list[Callable[[], None] | None] = [None] * count

    def register_callback(self, index: int, fn: Callable[[], None]) -> None:
        self._callbacks[index] = fn

    def simulate_press(self, index: int = 0) -> None:
        if not (0 <= index < len(self._callbacks)):
            return
        cb = self._callbacks[index]
        if cb is not None:
            cb()


def create_button(config: ButtonConfig) -> ButtonSensor:
    if config.use_mock:
        logger.info("Button: mock mode (%d buttons)", len(config.gpio_pins))
        return MockButton(count=len(config.gpio_pins))
    return MultiButton(config)
