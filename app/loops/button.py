from __future__ import annotations

import asyncio
import logging
from datetime import datetime as _DateTime

from app.state import state
from app.storage.logs import start_desk_session

logger = logging.getLogger(__name__)

# Minimum seconds before the same button re-fires while already on the target page.
_SAME_PAGE_COOLDOWN_SECS = 180

# Per-button last-accepted timestamps (keyed by 1-based button number).
_btn_last_accepted: dict[int, _DateTime] = {}


def _in_ap_mode(btn_num: int) -> bool:
    if state.wifi_mode == "ap":
        logger.debug("Button %d ignored: device in AP mode", btn_num)
        return True
    return False


def _within_cooldown(btn_num: int, now: _DateTime) -> bool:
    """Return True if button was last accepted within _SAME_PAGE_COOLDOWN_SECS."""
    last = _btn_last_accepted.get(btn_num)
    if last is None:
        return False
    return (now - last).total_seconds() < _SAME_PAGE_COOLDOWN_SECS


async def _handle_btn_dashboard(display_queue: asyncio.Queue) -> None:
    """Button 1 (GPIO 5) — force OCCUPIED and switch to Dashboard.

    When already on dashboard, repeated presses within _SAME_PAGE_COOLDOWN_SECS
    are ignored.  Switching from another page always proceeds.
    """
    if _in_ap_mode(1):
        return
    now = _DateTime.now()
    if state.display_page == "dashboard" and _within_cooldown(1, now):
        logger.debug(
            "Button 1 ignored: already on dashboard within %ds cooldown",
            _SAME_PAGE_COOLDOWN_SECS,
        )
        return
    if state.presence != "OCCUPIED" and state.desk_session_id is None:
        try:
            session_id = await start_desk_session(now)
            state.desk_session_id = session_id
            state.desk_session_start = now
        except Exception as exc:
            logger.error("Button 1: failed to start desk session: %s", exc)
    state.presence = "OCCUPIED"
    state.display_page = "dashboard"
    _btn_last_accepted[1] = now
    try:
        display_queue.put_nowait("dashboard")
    except asyncio.QueueFull:
        logger.debug("Display queue full on button 1 press")
    logger.info("Button 1: OCCUPIED + dashboard")
