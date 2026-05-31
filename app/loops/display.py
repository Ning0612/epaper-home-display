from __future__ import annotations

import asyncio
import functools
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as _DateTime, timedelta as _timedelta

from app.display.renderer import render_dashboard
from app.state import state

logger = logging.getLogger(__name__)


def _maybe_advance_carousel(settings) -> None:
    """Advance carousel to next image if interval elapsed; updates state.custom_image_path."""
    if not settings.images.carousel_enabled:
        return
    if len(state.image_playlist) < 2:
        return

    now = _DateTime.now()
    interval = _timedelta(minutes=max(1, settings.images.carousel_interval_minutes))

    if state.carousel_last_advance is not None and (now - state.carousel_last_advance) < interval:
        return

    playlist = state.image_playlist
    if settings.images.carousel_mode == "random":
        candidates = [i for i in range(len(playlist)) if i != state.carousel_index]
        idx = random.choice(candidates) if candidates else state.carousel_index
    else:
        idx = (state.carousel_index + 1) % len(playlist)

    import os
    if not os.path.exists(playlist[idx]):
        logger.warning("Carousel image missing, removing from playlist: %s", playlist[idx])
        state.image_playlist = [p for p in state.image_playlist if p != playlist[idx]]
        # Recurse once to try the next candidate (avoids infinite loop: list is now shorter)
        if len(state.image_playlist) >= 2:
            _maybe_advance_carousel(settings)
        return

    state.carousel_index = idx
    state.custom_image_path = playlist[idx]
    state.carousel_last_advance = now
    logger.debug("Carousel advanced to index %d: %s", idx, playlist[idx])


async def _display_loop(
    epaper, executor: ThreadPoolExecutor, display_queue: asyncio.Queue, settings, mqtt_service=None
) -> None:
    # Every full_refresh_every-th update is a full refresh (clears ghosting); others use
    # init_fast() for a faster partial update. max(1,...) guards against zero in YAML.
    refresh_count = 0
    loop = asyncio.get_event_loop()

    while True:
        # Align to wall-clock: trigger at :dashboard_trigger_second each minute.
        # Any display_queue event (button, MQTT alert, presence_return) fires immediately.
        now = _DateTime.now()
        target = settings.display.dashboard_trigger_second
        delay = (target - now.second) % 60 or 60  # `or 60` avoids re-triggering immediately
        try:
            await asyncio.wait_for(display_queue.get(), timeout=delay)
        except asyncio.TimeoutError:
            pass  # wall-clock trigger

        _maybe_advance_carousel(settings)

        if state.presence != "OCCUPIED":
            continue  # pause updates while nobody home

        if state.display_busy:
            continue

        full_refresh = (refresh_count % max(1, settings.display.full_refresh_every) == 0)
        state.display_busy = True
        try:
            # Advance clock by display lag so the rendered HH:MM matches the
            # minute that will be visible when the panel finishes updating.
            render_time = _DateTime.now() + _timedelta(seconds=60 - settings.display.dashboard_trigger_second)
            image = render_dashboard(state, settings, render_time)
            await loop.run_in_executor(
                executor, functools.partial(epaper.display, image, full_refresh)
            )
            refresh_count += 1  # only advance cadence on successful panel write
            if mqtt_service is not None:
                try:
                    mqtt_service.publish("home/display/status", {
                        "status": "updated",
                        "refresh_type": "full" if full_refresh else "fast",
                    })
                except Exception as exc:
                    logger.debug("Failed to publish display status: %s", exc)
        except Exception as exc:
            logger.error("Display update failed: %s", exc)
        finally:
            state.display_busy = False
