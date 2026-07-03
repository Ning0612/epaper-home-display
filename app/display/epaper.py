from __future__ import annotations

import logging
import os
import sys
from typing import Protocol

from PIL import Image

from app.config import DisplayConfig
from app.display.dirty_region import compute_dirty_regions, pack_mono_buffer

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
        self._last_image: Image.Image | None = None

    def init(self) -> None:
        self._epd.init()

    def display(self, image: Image.Image, full_refresh: bool = False) -> None:
        if (
            not full_refresh
            and self._last_image is not None
            and hasattr(self._epd, "display_Partial")
            and hasattr(self._epd, "init_part")
            # getbuffer() auto-rotates 480x800 input to the panel's native
            # 800x480 orientation; the dirty-region path crops/diffs in the
            # image's own coordinate space and cannot replicate that, so it
            # only applies when the image is already in panel-native size.
            and image.size == (self._epd.width, self._epd.height)
        ):
            regions = compute_dirty_regions(self._last_image, image)
            if regions is not None:
                if not regions:
                    logger.debug("Dirty-region diff empty, skipping panel write")
                    return
                self._epd.init_part()
                for xs, ys, xe, ye in regions:
                    buf = pack_mono_buffer(image.crop((xs, ys, xe, ye)))
                    self._epd.display_Partial(buf, xs, ys, xe, ye)
                self._epd.sleep()
                self._last_image = image.copy()
                logger.info("Partial refresh: %d region(s) %s", len(regions), regions)
                return
            # regions is None: no usable baseline (size mismatch) — fall through.

        # sleep() calls module_exit() which closes the SPI fd, so both paths
        # must call an init variant to reopen it before writing.
        use_fast = not full_refresh
        if full_refresh:
            self._epd.init()
        else:
            try:
                self._epd.init_fast()
            except AttributeError:
                # Driver has no init_fast() — fall back to full init.
                # display_fast() is also unavailable in this case.
                logger.warning("init_fast() not available, falling back to init()")
                self._epd.init()
                use_fast = False
        buf = self._epd.getbuffer(image)
        if use_fast:
            try:
                self._epd.display_fast(buf)
            except AttributeError:
                # Driver has init_fast() but no display_fast() — use display().
                self._epd.display(buf)
        else:
            self._epd.display(buf)
        self._epd.sleep()
        # Only recorded once the whole write succeeds, so an exception mid-way
        # leaves the next diff covering the incomplete update (self-healing).
        self._last_image = image.copy()

    def sleep(self) -> None:
        self._epd.sleep()

    def clear(self) -> None:
        self._epd.init()
        self._epd.Clear()
        self._epd.sleep()
        # Panel content no longer matches any previously recorded frame.
        self._last_image = None


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
