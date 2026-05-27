from __future__ import annotations

import logging
import os
import sys
from typing import Protocol

from PIL import Image

from app.config import DisplayConfig

logger = logging.getLogger(__name__)

# The Waveshare driver lives under lib/ in the repo root.
_LIB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)

try:
    from waveshare_epd import epd7in5_V2 as _epd_module  # type: ignore[import]
    _HAS_DRIVER = True
except ImportError:
    _HAS_DRIVER = False


class EpaperDisplay(Protocol):
    def init(self) -> None: ...
    def display(self, image: Image.Image, full_refresh: bool = False) -> None: ...
    def sleep(self) -> None: ...
    def clear(self) -> None: ...


class RealEpaper:
    def __init__(self) -> None:
        self._epd = _epd_module.EPD()

    def init(self) -> None:
        self._epd.init()

    def display(self, image: Image.Image, full_refresh: bool = False) -> None:
        if full_refresh:
            self._epd.init()
        buf = self._epd.getbuffer(image)
        self._epd.display(buf)
        self._epd.sleep()

    def sleep(self) -> None:
        self._epd.sleep()

    def clear(self) -> None:
        self._epd.init()
        self._epd.Clear()
        self._epd.sleep()


class MockEpaper:
    def __init__(self, save_path: str | None = None) -> None:
        self._save_path = save_path
        self._display_count = 0

    def init(self) -> None:
        logger.debug("MockEpaper: init")

    def display(self, image: Image.Image, full_refresh: bool = False) -> None:
        self._display_count += 1
        logger.info("MockEpaper: display #%d full_refresh=%s", self._display_count, full_refresh)
        if self._save_path:
            image.save(self._save_path)

    def sleep(self) -> None:
        logger.debug("MockEpaper: sleep")

    def clear(self) -> None:
        logger.debug("MockEpaper: clear")


def create_epaper(config: DisplayConfig) -> EpaperDisplay:
    if config.use_mock or not _HAS_DRIVER:
        if not config.use_mock and not _HAS_DRIVER:
            logger.warning("Waveshare driver not found in lib/ — using MockEpaper")
        return MockEpaper()
    return RealEpaper()
