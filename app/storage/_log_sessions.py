from __future__ import annotations

from datetime import datetime, timedelta

from app.storage.db import connect
from app.storage._log_helpers import _to_iso


async def start_desk_session(start_ts: datetime) -> int:
    async with connect() as db:
        cursor = await db.execute(
            "INSERT INTO desk_sessions (start_ts) VALUES (?)",
            (_to_iso(start_ts),),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]


async def end_desk_session(session_id: int, end_ts: datetime, duration_seconds: int) -> None:
    async with connect() as db:
        await db.execute(
            "UPDATE desk_sessions SET end_ts=?, duration_seconds=? WHERE id=?",
            (_to_iso(end_ts), duration_seconds, session_id),
        )
        await db.commit()


async def get_ongoing_desk_session() -> dict | None:
    async with connect() as db:
        async with db.execute(
            "SELECT id, start_ts FROM desk_sessions WHERE end_ts IS NULL "
            "ORDER BY start_ts DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    return {"id": row[0], "start_ts": row[1], "end_ts": None, "duration_seconds": None}


async def get_sessions_for_date(target_date) -> list[dict]:
    """Return all desk sessions whose start_ts falls on *target_date* (datetime.date)."""
    date_prefix = target_date.isoformat()
    async with connect() as db:
        async with db.execute(
            "SELECT id, start_ts, end_ts, duration_seconds FROM desk_sessions "
            "WHERE start_ts LIKE ? ORDER BY start_ts ASC",
            (f"{date_prefix}%",),
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"id": r[0], "start_ts": r[1], "end_ts": r[2], "duration_seconds": r[3]} for r in rows]


async def get_sessions_last_n_days(n: int) -> list[dict]:
    """Return all desk sessions with start_ts within the last *n* days."""
    cutoff = (datetime.now() - timedelta(days=n)).isoformat()
    async with connect() as db:
        async with db.execute(
            "SELECT id, start_ts, end_ts, duration_seconds FROM desk_sessions "
            "WHERE start_ts > ? ORDER BY start_ts ASC",
            (cutoff,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"id": r[0], "start_ts": r[1], "end_ts": r[2], "duration_seconds": r[3]} for r in rows]


async def get_recent_sessions(limit: int = 20) -> list[dict]:
    limit = max(1, min(limit, 200))
    async with connect() as db:
        async with db.execute(
            "SELECT id, start_ts, end_ts, duration_seconds FROM desk_sessions "
            "ORDER BY start_ts DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"id": r[0], "start_ts": r[1], "end_ts": r[2], "duration_seconds": r[3]} for r in rows]
