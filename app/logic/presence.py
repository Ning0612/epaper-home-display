from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from app.config import PresenceConfig

PresenceState = Literal["OCCUPIED", "UNOCCUPIED", "UNKNOWN"]


def compute_presence(
    light_is_bright: bool,
    recent_door_events: list[dict],
    recent_face_events: list[dict],
    button_override: bool,
    config: PresenceConfig,
    now: datetime | None = None,
) -> tuple[float, PresenceState]:
    """Pure function — safe to unit-test without any hardware."""
    if now is None:
        now = datetime.now()

    score = 0.0

    if light_is_bright:
        score += config.light_weight

    door_cutoff = now - timedelta(seconds=config.door_window_seconds)
    if any(_parse_ts(e.get("timestamp", "")) > door_cutoff for e in recent_door_events):
        score += config.door_weight

    face_cutoff = now - timedelta(seconds=config.face_window_seconds)
    known_recent = [
        e for e in recent_face_events
        if e.get("known") and _parse_ts(e.get("timestamp", "")) > face_cutoff
    ]
    if known_recent:
        score += config.face_weight

    if button_override:
        return score, "OCCUPIED"

    result: PresenceState = "OCCUPIED" if score >= config.threshold else "UNOCCUPIED"
    return score, result


def _parse_ts(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return datetime.min
