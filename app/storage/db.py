from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

logger = logging.getLogger(__name__)

_DB_PATH = "data/epaper-home-display.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS indoor_env_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    temperature  REAL,
    humidity     REAL,
    light_raw    INTEGER,
    light_bright INTEGER
);

CREATE TABLE IF NOT EXISTS presence_logs (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     TEXT NOT NULL,
    score  REAL,
    state  TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS weather_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    data_json TEXT
);

CREATE TABLE IF NOT EXISTS door_events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    state    TEXT,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS face_events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    identity TEXT,
    known    INTEGER,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS alarm_decisions (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    decision TEXT,
    reason   TEXT,
    score    REAL
);

CREATE TABLE IF NOT EXISTS system_events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    level   TEXT,
    module  TEXT,
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_door_events_ts   ON door_events(ts);
CREATE INDEX IF NOT EXISTS idx_face_events_ts   ON face_events(ts);
CREATE INDEX IF NOT EXISTS idx_presence_logs_ts ON presence_logs(ts);
CREATE INDEX IF NOT EXISTS idx_indoor_env_ts    ON indoor_env_logs(ts);

CREATE TABLE IF NOT EXISTS desk_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    start_ts         TEXT NOT NULL,
    end_ts           TEXT,
    duration_seconds INTEGER
);
CREATE INDEX IF NOT EXISTS idx_desk_sessions_start ON desk_sessions(start_ts);

CREATE TABLE IF NOT EXISTS notification_queue (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_ts    TEXT NOT NULL,
    type          TEXT NOT NULL,
    message       TEXT NOT NULL,
    attempts      INTEGER DEFAULT 0,
    next_retry_ts TEXT NOT NULL,
    sent          INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_notif_queue_pending ON notification_queue(sent, next_retry_ts);

CREATE TABLE IF NOT EXISTS images (
    id            TEXT PRIMARY KEY,
    filename      TEXT NOT NULL,
    display_path  TEXT NOT NULL,
    tmp_path      TEXT,
    file_size     INTEGER,
    created_ts    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_images_created ON images(created_ts);
"""


async def init_db(path: str = "data/epaper-home-display.db") -> None:
    global _DB_PATH
    _DB_PATH = path
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=3000")
        await db.executescript(_SCHEMA)
        await db.commit()
    logger.info("Database ready (WAL): %s", path)


def get_db_path() -> str:
    return _DB_PATH


@asynccontextmanager
async def connect() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Open a connection with busy_timeout pre-set on every call."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("PRAGMA busy_timeout=3000")
        yield db
