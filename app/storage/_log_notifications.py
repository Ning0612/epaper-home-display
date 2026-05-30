from __future__ import annotations

from datetime import datetime

from app.storage.db import connect
from app.storage._log_helpers import _now, _to_iso


async def queue_notification(msg_type: str, message: str, next_retry: datetime) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO notification_queue "
            "(created_ts, type, message, attempts, next_retry_ts, sent) VALUES (?,?,?,0,?,0)",
            (_now(), msg_type, message, _to_iso(next_retry)),
        )
        await db.commit()


async def get_pending_notifications(now: datetime) -> list[dict]:
    async with connect() as db:
        async with db.execute(
            "SELECT id, type, message, attempts FROM notification_queue "
            "WHERE sent=0 AND next_retry_ts <= ? ORDER BY created_ts ASC",
            (_to_iso(now),),
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"id": r[0], "type": r[1], "message": r[2], "attempts": r[3]} for r in rows]


async def mark_notification_sent(notification_id: int) -> None:
    async with connect() as db:
        await db.execute(
            "UPDATE notification_queue SET sent=1 WHERE id=?",
            (notification_id,),
        )
        await db.commit()


async def update_notification_retry(
    notification_id: int, next_retry: datetime, attempts: int
) -> None:
    async with connect() as db:
        await db.execute(
            "UPDATE notification_queue SET next_retry_ts=?, attempts=? WHERE id=?",
            (_to_iso(next_retry), attempts, notification_id),
        )
        await db.commit()
