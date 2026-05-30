from __future__ import annotations

import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as _DateTime, timedelta as _timedelta

from app.display.renderer import render_dashboard
from app.state import state

logger = logging.getLogger(__name__)


async def _display_loop(
    epaper, executor: ThreadPoolExecutor, display_queue: asyncio.Queue, settings
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
        except Exception as exc:
            logger.error("Display update failed: %s", exc)
        finally:
            state.display_busy = False
