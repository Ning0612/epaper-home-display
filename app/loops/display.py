from __future__ import annotations

import asyncio
import functools
import logging
import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as _DateTime, timedelta as _timedelta

from app.display.renderer import render_dashboard
from app.display.renderer_apmode import render_ap_mode_page
from app.state import state

logger = logging.getLogger(__name__)

_AP_MODE_REFRESH_INTERVAL = 30.0
_STARTUP_DATA_TIMEOUT = 180.0


def _seconds_until_dashboard_tick(now: _DateTime, trigger_second: int, interval_minutes: int) -> float:
    """Seconds until the next N-minute wall-clock boundary trigger.

    Fires (60 - trigger_second) seconds before each N-minute mark so the panel
    finishes updating right as the clock rolls over.  interval_minutes must be a
    divisor of 60 (validated at config load time).
    """
    interval_sec = interval_minutes * 60
    lag = 60 - trigger_second           # seconds the panel takes to update
    target_pos = interval_sec - lag     # position within cycle to fire
    pos = (now.minute * 60 + now.second) % interval_sec
    return float((target_pos - pos) % interval_sec or interval_sec)


async def _wait_for_startup_data(timeout_sec: float = _STARTUP_DATA_TIMEOUT) -> None:
    """Wait until weather + sensor data are ready, or timeout elapses (or AP mode detected)."""
    deadline = asyncio.get_event_loop().time() + timeout_sec
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            logger.warning(
                "Startup data wait timed out after %.0fs — rendering with available data", timeout_sec
            )
            return
        if _is_ap_mode_active():
            logger.info("AP mode active during startup — skipping data wait")
            return
        if state.weather_current is not None and state.temperature is not None:
            logger.info("Startup data ready (weather + temperature loaded)")
            return
        await asyncio.sleep(min(2.0, remaining))


def _is_ap_mode_active() -> bool:
    """True when device is in AP mode and the AP setup page should be displayed."""
    return state.wifi_mode == "ap"


def _advance_image_selection(settings) -> None:
    """Pick the next carousel image and update state.custom_image_path/carousel_index.

    Shared by the interval-driven auto-advance below and the manual "advance now"
    WebUI endpoint. Does not touch carousel_refresh_count.
    """
    # Iterate until a valid image is found, removing missing files along the way.
    while len(state.image_playlist) >= 2:
        playlist = state.image_playlist
        # Re-sync index on every iteration so "next" is always relative to the currently
        # displayed image — guards against both external WebUI changes and files removed
        # earlier in this same loop
        if state.custom_image_path and state.custom_image_path in playlist:
            state.carousel_index = playlist.index(state.custom_image_path)
        else:
            state.carousel_index = state.carousel_index % len(playlist)
        if settings.images.carousel_mode == "random":
            candidates = [i for i in range(len(playlist)) if i != state.carousel_index]
            idx = random.choice(candidates) if candidates else state.carousel_index
        else:
            idx = (state.carousel_index + 1) % len(playlist)

        if os.path.exists(playlist[idx]):
            state.carousel_index = idx
            state.custom_image_path = playlist[idx]
            logger.debug("Carousel advanced to index %d: %s", idx, playlist[idx])
            return

        logger.warning("Carousel image missing, removing from playlist: %s", playlist[idx])
        state.image_playlist = [p for p in state.image_playlist if p != playlist[idx]]

    # Playlist collapsed below 2 during cleanup; ensure custom_image_path and index are consistent
    if not state.image_playlist:
        state.custom_image_path = None
        state.carousel_index = 0
    elif state.custom_image_path not in state.image_playlist:
        state.custom_image_path = state.image_playlist[0]
        state.carousel_index = 0
    else:
        state.carousel_index = state.image_playlist.index(state.custom_image_path)


def _maybe_advance_carousel(settings) -> None:
    """Advance carousel every N dashboard refreshes; updates state.custom_image_path."""
    if not settings.images.carousel_enabled:
        return
    if len(state.image_playlist) < 2:
        return

    if state.carousel_skip_next_advance:
        # A manual advance (WebUI) just picked the current image outside of this
        # loop — let it render for one full cycle before the interval countdown
        # resumes, so it's never skipped past when carousel_interval_refreshes == 1.
        state.carousel_skip_next_advance = False
        return

    state.carousel_refresh_count += 1
    if state.carousel_refresh_count < max(1, settings.images.carousel_interval_refreshes):
        return
    state.carousel_refresh_count = 0
    _advance_image_selection(settings)


async def _display_loop(
    epaper, executor: ThreadPoolExecutor, display_queue: asyncio.Queue, settings
) -> None:
    # The first update is a full refresh; then every full_refresh_every-th call
    # after that is a full refresh again (clears ghosting). Others use init_fast()
    # for a faster partial update. max(1,...) guards against zero in YAML.
    refresh_count = 0
    loop = asyncio.get_event_loop()
    # startup_wait_done: True once _wait_for_startup_data() has returned.
    #   Prevents re-calling it (with a fresh 180s timeout) on subsequent iterations.
    # startup_pending: True until the first render or clear succeeds.
    #   While True: skip wall-clock alignment and allow the initial dashboard render
    #   even when presence is not yet OCCUPIED, so the settings entry remains visible.
    startup_wait_done = False
    startup_pending = True
    screen_cleared = False

    while True:
        # Wait strategy:
        #   not startup_wait_done → wait for essential data (up to 3 min), then fall through
        #   startup_pending (data ready, render not yet done) → fall through immediately
        #   ap_mode → 30s; dashboard → wall-clock aligned.
        # event value is preserved so callers downstream can react to specific signals
        # (e.g. "wifi_connected" allows one dashboard render even while unoccupied).
        event: str | None = None
        if not startup_wait_done:
            await _wait_for_startup_data()
            startup_wait_done = True
            # Fall through immediately — no scheduling wait before first render
        elif startup_pending:
            pass  # data ready, first render not yet done — fall through immediately
        elif _is_ap_mode_active():
            # AP mode: static info page, refresh periodically to update timestamp
            try:
                event = await asyncio.wait_for(display_queue.get(), timeout=_AP_MODE_REFRESH_INTERVAL)
            except asyncio.TimeoutError:
                pass
        else:
            # Align to N-minute wall-clock boundary (configurable via dashboard_interval_minutes).
            # Any display_queue event (button, presence_return, presence_away, wifi_connected)
            # fires immediately.
            now = _DateTime.now()
            delay = _seconds_until_dashboard_tick(
                now,
                settings.display.dashboard_trigger_second,
                settings.display.dashboard_interval_minutes,
            )
            try:
                event = await asyncio.wait_for(display_queue.get(), timeout=delay)
            except asyncio.TimeoutError:
                pass  # wall-clock trigger

        if state.display_page == "ap_mode":
            pass  # always render AP mode page regardless of presence
        elif state.display_page == "dashboard":
            allow_unoccupied_render = startup_pending or event == "wifi_connected"
            if state.presence != "OCCUPIED" and not allow_unoccupied_render:
                if not screen_cleared:
                    if state.display_busy:
                        continue

                    state.display_busy = True
                    try:
                        await loop.run_in_executor(executor, epaper.clear)
                        screen_cleared = True
                        refresh_count = 0
                        startup_pending = False
                        logger.info("Display cleared while unoccupied")
                    except Exception:
                        logger.exception("Failed to clear display while unoccupied")
                    finally:
                        state.display_busy = False
                # Keep the panel clear and pause dashboard updates while nobody is home.
                continue
            # Advance carousel AFTER the presence gate so the counter only
            # increments when a dashboard render is actually about to happen.
            _maybe_advance_carousel(settings)

        if state.display_busy:
            continue

        state.display_busy = True
        try:
            now = _DateTime.now()

            if state.display_page == "ap_mode":
                actual_full_refresh = (refresh_count % max(1, settings.display.full_refresh_every) == 0)
                image = render_ap_mode_page(state, settings, now)
                await loop.run_in_executor(
                    executor, functools.partial(epaper.display, image, actual_full_refresh)
                )
                refresh_count += 1
            else:
                actual_full_refresh = (refresh_count % max(1, settings.display.full_refresh_every) == 0)
                # Advance clock by display lag so the rendered HH:MM matches the
                # minute that will be visible when the panel finishes updating.
                render_time = now + _timedelta(seconds=60 - settings.display.dashboard_trigger_second)
                image = render_dashboard(state, settings, render_time)
                await loop.run_in_executor(
                    executor, functools.partial(epaper.display, image, actual_full_refresh)
                )
                refresh_count += 1  # advances once epaper.display() returns without raising, even if it
                # skipped the panel write internally (e.g. a dirty-region no-op on an unchanged frame)

            screen_cleared = False
            startup_pending = False  # first render succeeded — clear boot gate
        except Exception as exc:
            logger.error("Display update failed: %s", exc)
        finally:
            state.display_busy = False
