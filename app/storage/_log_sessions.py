from __future__ import annotations

from datetime import datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo

from app.storage.db import connect
from app.storage._log_helpers import _to_iso
from app.timezone import instant_after, instant_before


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


async def get_sessions_for_date(
    target_date,
    timezone_name: str | None = None,
    legacy_timezone: tzinfo | None = None,
) -> list[dict]:
    """Return all desk sessions whose start_ts falls on *target_date* (datetime.date)."""
    if timezone_name:
        target_zone = ZoneInfo(timezone_name)
        async with connect() as db:
            async with db.execute(
                "SELECT id, start_ts, end_ts, duration_seconds FROM desk_sessions ORDER BY start_ts ASC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            _session_dict(row)
            for row in rows
            if (start := _parse_for_zone(row[1], target_zone, legacy_timezone)) is not None
            and start.date() == target_date
        ]

    date_prefix = target_date.isoformat()
    async with connect() as db:
        async with db.execute(
            "SELECT id, start_ts, end_ts, duration_seconds FROM desk_sessions "
            "WHERE start_ts LIKE ? ORDER BY start_ts ASC",
            (f"{date_prefix}%",),
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"id": r[0], "start_ts": r[1], "end_ts": r[2], "duration_seconds": r[3]} for r in rows]


async def get_sessions_last_n_days(
    n: int,
    now: datetime | None = None,
    timezone_name: str | None = None,
    legacy_timezone: tzinfo | None = None,
) -> list[dict]:
    """Return all desk sessions with start_ts within the last *n* days."""
    if timezone_name:
        target_zone = ZoneInfo(timezone_name)
        range_end = _coerce_bound(now or datetime.now(), target_zone)
        range_start = range_end - timedelta(days=n)
        async with connect() as db:
            async with db.execute(
                "SELECT id, start_ts, end_ts, duration_seconds FROM desk_sessions ORDER BY start_ts ASC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            _session_dict(row)
            for row in rows
            if (start := _parse_for_zone(row[1], target_zone, legacy_timezone)) is not None
            and instant_after(start, range_start)
            and not instant_after(start, range_end)
        ]

    cutoff = ((now or datetime.now()) - timedelta(days=n)).isoformat()
    async with connect() as db:
        async with db.execute(
            "SELECT id, start_ts, end_ts, duration_seconds FROM desk_sessions "
            "WHERE start_ts > ? ORDER BY start_ts ASC",
            (cutoff,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"id": r[0], "start_ts": r[1], "end_ts": r[2], "duration_seconds": r[3]} for r in rows]


def _parse_for_zone(value: object, target_zone, legacy_timezone: tzinfo | None) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=legacy_timezone or target_zone)
    return parsed.astimezone(target_zone)


def _coerce_bound(value: datetime, target_zone) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=target_zone)
    return value.astimezone(target_zone)


def _coarse_iso(value: datetime) -> str:
    """Keep the SQL prefilter comparable to legacy naive local timestamps."""
    return value.replace(tzinfo=None).isoformat() if value.tzinfo is not None else value.isoformat()


def _session_dict(row) -> dict:
    return {"id": row[0], "start_ts": row[1], "end_ts": row[2], "duration_seconds": row[3]}


async def get_sessions_overlapping(
    start_ts: datetime,
    end_ts: datetime,
    timezone_name: str | None = None,
    legacy_timezone: tzinfo | None = None,
) -> list[dict]:
    """Return sessions with any overlap in the half-open [start_ts, end_ts) range.

    When ``timezone_name`` is supplied, rows are filtered after parsing so
    offset-aware records and legacy naive records can coexist safely.
    """
    if timezone_name:
        target_zone = ZoneInfo(timezone_name)
        range_start = _coerce_bound(start_ts, target_zone)
        range_end = _coerce_bound(end_ts, target_zone)
        coarse_start = _coarse_iso(range_start - timedelta(days=2))
        coarse_end = _coarse_iso(range_end + timedelta(days=2))
        async with connect() as db:
            async with db.execute(
                "SELECT id, start_ts, end_ts, duration_seconds FROM desk_sessions "
                "WHERE start_ts < ? AND (end_ts IS NULL OR end_ts > ?) ORDER BY start_ts ASC",
                (coarse_end, coarse_start),
            ) as cursor:
                rows = await cursor.fetchall()
        sessions = []
        for row in rows:
            parsed_start = _parse_for_zone(row[1], target_zone, legacy_timezone)
            if parsed_start is None:
                continue
            parsed_end = None if row[2] is None else _parse_for_zone(row[2], target_zone, legacy_timezone)
            if row[2] is not None and parsed_end is None:
                continue
            if parsed_end is not None and not instant_before(parsed_start, parsed_end):
                continue
            if instant_before(parsed_start, range_end) and (
                parsed_end is None or instant_after(parsed_end, range_start)
            ):
                sessions.append(_session_dict(row))
        return sessions

    async with connect() as db:
        async with db.execute(
            "SELECT id, start_ts, end_ts, duration_seconds FROM desk_sessions "
            "WHERE start_ts < ? AND (end_ts IS NULL OR end_ts > ?) ORDER BY start_ts ASC",
            (_to_iso(end_ts), _to_iso(start_ts)),
        ) as cursor:
            rows = await cursor.fetchall()
    return [_session_dict(row) for row in rows]


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
