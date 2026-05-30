from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from app.storage.db import connect

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().isoformat()


def _safe_json_loads(raw: str) -> dict:
    """Parse raw_json safely; always return a plain dict."""
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


async def log_env(
    temperature: float | None,
    humidity: float | None,
    light_raw: int | None,
    light_bright: bool,
) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO indoor_env_logs (ts, temperature, humidity, light_raw, light_bright) VALUES (?,?,?,?,?)",
            (_now(), temperature, humidity, light_raw, int(light_bright)),
        )
        await db.commit()


async def log_presence(score: float, state: str, reason: str) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO presence_logs (ts, score, state, reason) VALUES (?,?,?,?)",
            (_now(), score, state, reason),
        )
        await db.commit()


async def log_door_event(door_state: str, raw: dict) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO door_events (ts, state, raw_json) VALUES (?,?,?)",
            (_now(), door_state, json.dumps(raw)),
        )
        await db.commit()


async def log_face_event(identity: str, known: bool, raw: dict) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO face_events (ts, identity, known, raw_json) VALUES (?,?,?,?)",
            (_now(), identity, int(known), json.dumps(raw)),
        )
        await db.commit()


async def log_alarm_decision(decision: str, reason: str, score: float) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO alarm_decisions (ts, decision, reason, score) VALUES (?,?,?,?)",
            (_now(), decision, reason, score),
        )
        await db.commit()


async def log_system_event(level: str, module: str, message: str) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO system_events (ts, level, module, message) VALUES (?,?,?,?)",
            (_now(), level, module, message),
        )
        await db.commit()


async def get_recent_door_events(seconds: int = 300) -> list[dict]:
    cutoff = (datetime.now() - timedelta(seconds=seconds)).isoformat()
    async with connect() as db:
        async with db.execute(
            "SELECT ts, state, raw_json FROM door_events WHERE ts > ? ORDER BY ts DESC LIMIT 200",
            (cutoff,),
        ) as cursor:
            rows = await cursor.fetchall()
    # standard fields placed last so they override any matching keys in raw_json
    return [{**_safe_json_loads(r[2]), "timestamp": r[0], "state": r[1]} for r in rows]


async def get_recent_face_events(seconds: int = 600) -> list[dict]:
    cutoff = (datetime.now() - timedelta(seconds=seconds)).isoformat()
    async with connect() as db:
        async with db.execute(
            "SELECT ts, identity, known, raw_json FROM face_events WHERE ts > ? ORDER BY ts DESC LIMIT 200",
            (cutoff,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [
        {**_safe_json_loads(r[3]), "timestamp": r[0], "identity": r[1], "known": bool(r[2])}
        for r in rows
    ]


async def get_env_logs(limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 500))
    async with connect() as db:
        async with db.execute(
            "SELECT ts, temperature, humidity, light_raw, light_bright "
            "FROM indoor_env_logs ORDER BY ts DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [
        {"ts": r[0], "temperature": r[1], "humidity": r[2], "light_raw": r[3], "light_bright": bool(r[4])}
        for r in rows
    ]


async def get_presence_logs(limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 500))
    async with connect() as db:
        async with db.execute(
            "SELECT ts, score, state, reason FROM presence_logs ORDER BY ts DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"ts": r[0], "score": r[1], "state": r[2], "reason": r[3]} for r in rows]


async def log_ai_usage(data: dict) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO ai_usage_logs (ts, raw_json) VALUES (?,?)",
            (_now(), json.dumps(data)),
        )
        await db.commit()


async def get_system_events(limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 500))
    async with connect() as db:
        async with db.execute(
            "SELECT ts, level, module, message FROM system_events ORDER BY ts DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"ts": r[0], "level": r[1], "module": r[2], "message": r[3]} for r in rows]


# ── Desk sessions ──────────────────────────────────────────────────────────────

def _to_iso(dt: datetime) -> str:
    return dt.isoformat()


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


# ── Notification queue ─────────────────────────────────────────────────────────

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
