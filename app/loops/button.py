from __future__ import annotations

import asyncio
import logging
from datetime import datetime as _DateTime

from app.state import state
from app.storage.logs import start_desk_session

logger = logging.getLogger(__name__)


async def _handle_button(display_queue: asyncio.Queue) -> None:
    if state.presence != "OCCUPIED" and state.desk_session_id is None:
        now = _DateTime.now()
        try:
            session_id = await start_desk_session(now)
            state.desk_session_id = session_id
            state.desk_session_start = now
        except Exception as exc:
            logger.error("Button: failed to start desk session: %s", exc)
    state.presence = "OCCUPIED"
    try:
        display_queue.put_nowait("dashboard")
    except asyncio.QueueFull:
        logger.debug("Display queue full on button press, will render on next cycle")
    logger.info("Button: forced OCCUPIED")
