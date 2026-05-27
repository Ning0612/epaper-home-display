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
        import RPi.GPIO as GPIO  # type: ignore[import]
        self._pin = config.gpio_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._gpio = GPIO

    def is_pressed(self) -> bool:
        return not self._gpio.input(self._pin)

    def register_callback(self, fn: Callable[[], None]) -> None:
        self._gpio.add_event_detect(
            self._pin,
            self._gpio.FALLING,
            callback=lambda _: fn(),
            bouncetime=200,
        )


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
