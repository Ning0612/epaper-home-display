from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class AgentState:
    temperature: float | None = None
    humidity: float | None = None
    light_raw: int | None = None
    light_is_bright: bool = False

    presence: Literal["OCCUPIED", "UNOCCUPIED", "UNKNOWN"] = "UNKNOWN"
    presence_score: float = 0.0

    weather_current: dict | None = None
    weather_forecast: list[dict] = field(default_factory=list)
    weather_fetched_at: datetime | None = None

    last_door_event: dict | None = None
    last_face_event: dict | None = None
    last_alert: dict | None = None
    security_status: dict | None = None

    display_busy: bool = False
    active_reminder: str | None = None
    started_at: datetime = field(default_factory=datetime.now)


state = AgentState()
