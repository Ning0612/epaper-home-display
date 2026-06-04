from __future__ import annotations

import asyncio
import functools
import logging
import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as _DateTime, timedelta as _timedelta

from app.display.renderer import render_dashboard
from app.display.renderer_alert import render_alert_page
from app.display.renderer_apmode import render_ap_mode_page
from app.services.snapshot_client import fetch_snapshot
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


def _is_alert_active(settings) -> bool:
    """True when alert page should be shown: enabled and page is alert.

    snapshot_url is no longer required — MQTT camera feed can supply images without HTTP.
    """
    return (
        state.display_page == "alert"
        and settings.outdoor_agent.alert_page_enabled
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

    def _dismiss() -> bool:
        state.display_page = "dashboard"
        state.last_snapshot_image = None
        state.last_alarm_decision = None
        state.last_alert = None
        state.alert_face_event = None
        state.alert_last_triggered_at = None
        state.alert_page_started_at = None
        return True

    # Normalise disabled alert state immediately
    if not settings.outdoor_agent.alert_page_enabled:
        return _dismiss()

    if state.alert_last_triggered_at is None:
        return _dismiss()

    elapsed = (_DateTime.now() - state.alert_last_triggered_at).total_seconds()
    if elapsed > settings.outdoor_agent.alert_page_timeout_sec:
        logger.info("Alert page timeout (%.0fs), returning to dashboard", elapsed)
        return _dismiss()

    return False


def _maybe_advance_carousel(settings) -> None:
    """Advance carousel every N dashboard refreshes; updates state.custom_image_path."""
    if not settings.images.carousel_enabled:
        return
    if len(state.image_playlist) < 2:
        return

    state.carousel_refresh_count += 1
    if state.carousel_refresh_count < max(1, settings.images.carousel_interval_refreshes):
        return
    state.carousel_refresh_count = 0

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


async def _display_loop(
    epaper, executor: ThreadPoolExecutor, display_queue: asyncio.Queue, settings, mqtt_service=None
) -> None:
    # Every full_refresh_every-th update is a full refresh (clears ghosting); others use
    # init_fast() for a faster partial update. max(1,...) guards against zero in YAML.
    refresh_count = 0
    last_rendered_page: str | None = None
    loop = asyncio.get_event_loop()
    # startup_wait_done: True once _wait_for_startup_data() has returned.
    #   Prevents re-calling it (with a fresh 180s timeout) on subsequent iterations.
    # startup_pending: True until the first render succeeds.
    #   While True: skip wall-clock alignment and bypass the presence gate.
    startup_wait_done = False
    startup_pending = True

    while True:
        # Wait strategy:
        #   not startup_wait_done → wait for essential data (up to 3 min), then fall through
        #   startup_pending (data ready, render not yet done) → fall through immediately
        #   alert → wall-clock aligned, capped at alert timeout; ap_mode → 30s; dashboard → wall-clock aligned.
        # event value is preserved so callers downstream can react to specific signals
        # (e.g. "wifi_connected" bypasses the presence-check gate).
        event: str | None = None
        if not startup_wait_done:
            await _wait_for_startup_data()
            startup_wait_done = True
            # Fall through immediately — no scheduling wait before first render
        elif startup_pending:
            pass  # data ready, first render not yet done — fall through immediately
        elif _is_alert_active(settings):
            now = _DateTime.now()
            delay = _seconds_until_dashboard_tick(
                now,
                settings.display.dashboard_trigger_second,
                settings.display.dashboard_interval_minutes,
            )
            # Cap wait at alert timeout so _check_alert_timeout fires on schedule
            if state.alert_last_triggered_at is not None:
                elapsed = (now - state.alert_last_triggered_at).total_seconds()
                timeout_remaining = max(0.1, settings.outdoor_agent.alert_page_timeout_sec - elapsed)
                delay = min(delay, timeout_remaining)
            else:
                delay = 0.1  # no trigger time recorded → let _check_alert_timeout transition immediately
            try:
                event = await asyncio.wait_for(display_queue.get(), timeout=delay)
            except asyncio.TimeoutError:
                pass
        elif _is_ap_mode_active():
            # AP mode: static info page, refresh periodically to update timestamp
            try:
                event = await asyncio.wait_for(display_queue.get(), timeout=_AP_MODE_REFRESH_INTERVAL)
            except asyncio.TimeoutError:
                pass
        else:
            # Align to N-minute wall-clock boundary (configurable via dashboard_interval_minutes).
            # Any display_queue event (button, MQTT alert, presence_return) fires immediately.
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

        # Check if alert page should time out and return to dashboard.
        # When a transition occurs, drain stale events from the queue and force full refresh.
        # "wifi_connected" is re-queued so the presence-bypass logic below can act on it.
        transitioned = _check_alert_timeout(settings)
        if transitioned:
            while not display_queue.empty():
                try:
                    drained = display_queue.get_nowait()
                    if drained == "wifi_connected":
                        try:
                            display_queue.put_nowait(drained)
                        except asyncio.QueueFull:
                            pass
                        break
                except asyncio.QueueEmpty:
                    break
            refresh_count = 0   # force full refresh on first dashboard frame after alert

        if state.display_page == "ap_mode":
            pass  # always render AP mode page regardless of presence
        elif state.display_page == "dashboard":
            # Bypass presence gate for the very first render so boot-up always
            # produces a display update regardless of occupancy state.
            if state.presence != "OCCUPIED" and event != "wifi_connected" and not startup_pending:
                continue  # pause dashboard updates while nobody home
            # Advance carousel AFTER the presence gate so the counter only
            # increments when a dashboard render is actually about to happen.
            _maybe_advance_carousel(settings)

        if state.display_busy:
            continue

        # Capture page before entering executor so publish reflects what was actually rendered,
        # not a potentially mutated state (MQTT can change display_page mid-executor-wait).
        rendered_page = state.display_page

        # Force full refresh on any alert→other transition (handles button cancel in addition to timeout).
        if last_rendered_page == "alert" and rendered_page != "alert":
            refresh_count = 0

        state.display_busy = True
        try:
            now = _DateTime.now()

            if _is_alert_active(settings):
                # Prefer MQTT camera feed; fall back to HTTP snapshot when no recent MQTT frame.
                # MQTT camera frames update state.last_snapshot_image directly via _dispatch_camera.
                mqtt_age: float | None = None
                if state.last_camera_frame_at is not None:
                    mqtt_age = (now - state.last_camera_frame_at).total_seconds()
                # Only skip HTTP if we actually have a cached image AND the MQTT frame is fresh.
                # last_camera_frame_at is not cleared on alert dismiss, so checking image existence
                # prevents a stale timestamp from suppressing HTTP on alert re-entry.
                mqtt_fresh = (
                    state.last_snapshot_image is not None
                    and mqtt_age is not None
                    and mqtt_age <= 5.0
                )
                if settings.outdoor_agent.snapshot_url and not mqtt_fresh:
                    snap = await fetch_snapshot(
                        settings.outdoor_agent.snapshot_url,
                        settings.outdoor_agent.snapshot_timeout_sec,
                    )
                    if snap is not None:
                        state.last_snapshot_image = snap
                image = render_alert_page(state, settings, now)
                actual_full_refresh = (refresh_count % max(1, settings.display.full_refresh_every) == 0)
                await loop.run_in_executor(
                    executor, functools.partial(epaper.display, image, actual_full_refresh)
                )
                refresh_count += 1
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

            startup_pending = False  # first render succeeded — clear boot gate
            last_rendered_page = rendered_page

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
