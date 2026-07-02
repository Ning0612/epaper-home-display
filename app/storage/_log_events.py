from __future__ import annotations

import logging

from app.storage.db import connect
from app.storage._log_helpers import _now

logger = logging.getLogger(__name__)


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


async def log_system_event(level: str, module: str, message: str) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO system_events (ts, level, module, message) VALUES (?,?,?,?)",
            (_now(), level, module, message),
        )
        await db.commit()


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


async def get_system_events(limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 500))
    async with connect() as db:
        async with db.execute(
            "SELECT ts, level, module, message FROM system_events ORDER BY ts DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"ts": r[0], "level": r[1], "module": r[2], "message": r[3]} for r in rows]
