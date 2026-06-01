from __future__ import annotations

import asyncio
import functools
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as _DateTime, timedelta as _timedelta

from app.display.renderer import render_dashboard
from app.display.renderer_alert import render_alert_page
from app.display.renderer_apmode import render_ap_mode_page
from app.services.snapshot_client import fetch_snapshot
from app.state import state

logger = logging.getLogger(__name__)


def _is_alert_active(settings) -> bool:
    """True when alert page should be shown: enabled, URL configured, and page is alert."""
    return (
        state.display_page == "alert"
        and settings.outdoor_agent.alert_page_enabled
        and bool(settings.outdoor_agent.snapshot_url)
    )


def _is_ap_mode_active() -> bool:
    """True when device is in AP mode and the AP setup page should be displayed."""
    return state.wifi_mode == "ap"


def _check_alert_timeout(settings) -> bool:
    """Return to dashboard if timed out or alert page is disabled/unconfigured.

    Returns True if a transition from alert→dashboard just occurred (caller can force full refresh).
    """
    if state.display_page != "alert":
        return False

    # Normalise disabled / unconfigured alert state immediately
    if not settings.outdoor_agent.alert_page_enabled or not settings.outdoor_agent.snapshot_url:
        state.display_page = "dashboard"
        state.last_snapshot_image = None
        return True

    if state.alert_last_triggered_at is None:
        state.display_page = "dashboard"
        state.last_snapshot_image = None
        return True

    elapsed = (_DateTime.now() - state.alert_last_triggered_at).total_seconds()
    if elapsed > settings.outdoor_agent.alert_page_timeout_sec:
        logger.info("Alert page timeout (%.0fs), returning to dashboard", elapsed)
        state.display_page = "dashboard"
        state.last_snapshot_image = None
        return True

    return False


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
        # Wait strategy: alert → fixed short interval; ap_mode → 30s; dashboard → wall-clock aligned.
        if _is_alert_active(settings):
            interval = settings.outdoor_agent.alert_refresh_interval_sec
            try:
                await asyncio.wait_for(display_queue.get(), timeout=interval)
            except asyncio.TimeoutError:
                pass
        elif _is_ap_mode_active():
            # AP mode: static info page, refresh every 30s to update timestamp
            try:
                await asyncio.wait_for(display_queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                pass
        else:
            # Align to wall-clock: trigger at :dashboard_trigger_second each minute.
            # Any display_queue event (button, MQTT alert, presence_return) fires immediately.
            now = _DateTime.now()
            target = settings.display.dashboard_trigger_second
            delay = (target - now.second) % 60 or 60  # `or 60` avoids re-triggering immediately
            try:
                await asyncio.wait_for(display_queue.get(), timeout=delay)
            except asyncio.TimeoutError:
                pass  # wall-clock trigger

        # Check if alert page should time out and return to dashboard.
        # When a transition occurs, drain stale events from the queue and force full refresh.
        transitioned = _check_alert_timeout(settings)
        if transitioned:
            # Drain stale "alert" events that accumulated during the alert session so the
            # first dashboard frame isn't burst-triggered multiple times.
            while not display_queue.empty():
                try:
                    display_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            refresh_count = 0   # force full refresh on first dashboard frame after alert

        if state.display_page == "ap_mode":
            pass  # always render AP mode page regardless of presence
        elif state.display_page == "dashboard":
            _maybe_advance_carousel(settings)
            if state.presence != "OCCUPIED":
                continue  # pause dashboard updates while nobody home

        if state.display_busy:
            continue

        # Capture page before entering executor so publish reflects what was actually rendered,
        # not a potentially mutated state (MQTT can change display_page mid-executor-wait).
        rendered_page = state.display_page

        state.display_busy = True
        try:
            now = _DateTime.now()

            if _is_alert_active(settings):
                # Fetch latest snapshot from outdoor agent (non-blocking)
                snap = await fetch_snapshot(
                    settings.outdoor_agent.snapshot_url,
                    settings.outdoor_agent.snapshot_timeout_sec,
                )
                if snap is not None:
                    state.last_snapshot_image = snap
                image = render_alert_page(state, settings, now)
                # Alert page always uses fast refresh to meet 3s cadence
                actual_full_refresh = False
                await loop.run_in_executor(
                    executor, functools.partial(epaper.display, image, actual_full_refresh)
                )
                # Do not increment refresh_count — alert uses fast refresh exclusively;
                # dashboard resumes from its previous cadence position when we return.
            elif state.display_page == "ap_mode":
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
                refresh_count += 1  # only advance cadence on successful panel write

            if mqtt_service is not None:
                try:
                    mqtt_service.publish("home/display/status", {
                        "status": "updated",
                        "page": rendered_page,
                        "refresh_type": "full" if actual_full_refresh else "fast",
                    })
                except Exception as exc:
                    logger.debug("Failed to publish display status: %s", exc)
        except Exception as exc:
            logger.error("Display update failed: %s", exc)
        finally:
            state.display_busy = False
