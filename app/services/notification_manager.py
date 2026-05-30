from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.config import DiscordConfig
from app.logic.desk_session import format_daily_summary, format_session_end_msg
from app.services.discord import DiscordService
from app.storage.logs import (
    get_pending_notifications,
    mark_notification_sent,
    queue_notification,
    update_notification_retry,
)

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [timedelta(minutes=5), timedelta(minutes=15), timedelta(hours=1)]
_MAX_ATTEMPTS = 5


class NotificationManager:
    def __init__(self, discord: DiscordService, config: DiscordConfig) -> None:
        self._discord = discord
        self._config = config

    async def send_device_online(self, webui_url: str) -> None:
        if not self._config.notify_device_online:
            return
        msg = f"✅ ePaper Home Display 已上線\nWebUI: {webui_url}"
        await self._send_or_queue("device_online", msg)

    async def send_session_end(self, session: dict) -> None:
        if not self._config.notify_session_end:
            return
        msg = format_session_end_msg(session)
        await self._send_or_queue("session_end", msg)

    async def send_daily_summary(self, date_str: str, sessions: list[dict]) -> None:
        if not self._config.notify_daily_summary:
            return
        msg = format_daily_summary(date_str, sessions)
        await self._send_or_queue("daily_summary", msg)

    async def process_retry_queue(self) -> None:
        """Send any pending notifications whose retry time has arrived."""
        now = datetime.now()
        pending = await get_pending_notifications(now)
        for item in pending:
            success = await self._discord.send(item["message"])
            if success:
                await mark_notification_sent(item["id"])
                logger.info(
                    "Queued notification %s sent (type=%s)", item["id"], item["type"]
                )
            else:
                attempts = item["attempts"] + 1
                if attempts >= _MAX_ATTEMPTS:
                    await mark_notification_sent(item["id"])  # give up
                    logger.warning(
                        "Notification %s permanently failed after %d attempts",
                        item["id"],
                        attempts,
                    )
                else:
                    delay_idx = min(attempts - 1, len(_RETRY_DELAYS) - 1)
                    next_retry = now + _RETRY_DELAYS[delay_idx]
                    await update_notification_retry(item["id"], next_retry, attempts)

    async def _send_or_queue(self, msg_type: str, message: str) -> None:
        if not self._config.webhook_url:
            logger.debug("Discord webhook not configured, skipping notification (type=%s)", msg_type)
            return
        success = await self._discord.send(message)
        if not success:
            next_retry = datetime.now() + _RETRY_DELAYS[0]
            await queue_notification(msg_type, message, next_retry)
            logger.info("Notification queued for retry (type=%s)", msg_type)
