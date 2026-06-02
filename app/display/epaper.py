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

class EpaperDisplay(Protocol):
    def init(self) -> None: ...
    def display(self, image: Image.Image, full_refresh: bool = False) -> None: ...
    def sleep(self) -> None: ...
    def clear(self) -> None: ...


class RealEpaper:
    def __init__(self, epd_module) -> None:
        self._epd = epd_module.EPD()

    def init(self) -> None:
        self._epd.init()

    def display(self, image: Image.Image, full_refresh: bool = False) -> None:
        # sleep() calls module_exit() which closes the SPI fd, so both paths
        # must call an init variant to reopen it before writing.
        if full_refresh:
            self._epd.init()
        else:
            try:
                self._epd.init_fast()
            except AttributeError:
                # Older driver versions may not have init_fast(); fall back to
                # full init so the panel still updates correctly.
                logger.warning("init_fast() not available, falling back to init()")
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
    if config.use_mock:
        return MockEpaper()
    import importlib
    try:
        epd_module = importlib.import_module(f"waveshare_epd.{config.model}")
    except ImportError:
        logger.warning("Waveshare driver '%s' not found in lib/ — using MockEpaper", config.model)
        return MockEpaper()
    return RealEpaper(epd_module)
