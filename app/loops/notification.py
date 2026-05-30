from __future__ import annotations

import asyncio
import logging
from datetime import datetime as _DateTime, timedelta as _timedelta

from app.services.notification_manager import NotificationManager
from app.storage.logs import get_sessions_for_date

logger = logging.getLogger(__name__)


async def _notification_loop(settings, notification_manager: NotificationManager) -> None:
    last_summary_date = None
    while True:
        await asyncio.sleep(60)
        try:
            await notification_manager.process_retry_queue()

            if settings.discord.notify_daily_summary and settings.discord.daily_summary_time:
                now = _DateTime.now()
                try:
                    h, m = (int(x) for x in settings.discord.daily_summary_time.split(":"))
                    if now.hour == h and now.minute == m and last_summary_date != now.date():
                        yesterday = (now - _timedelta(days=1)).date()
                        sessions = await get_sessions_for_date(yesterday)
                        await notification_manager.send_daily_summary(
                            str(yesterday), sessions
                        )
                        last_summary_date = now.date()
                except ValueError:
                    logger.warning(
                        "Invalid daily_summary_time: %s", settings.discord.daily_summary_time
                    )
        except Exception as exc:
            logger.error("Notification loop error: %s", exc)
