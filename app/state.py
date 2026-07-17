from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class AgentState:
    temperature: float | None = None
    humidity: float | None = None
    light_raw: int | None = None
    # Legacy field name: True means raw >= threshold, which is actual dark light
    # for this sensor circuit.
    light_is_bright: bool = False
    light_state_since: datetime | None = None

    presence: Literal["OCCUPIED", "UNOCCUPIED", "UNKNOWN"] = "UNKNOWN"
    presence_score: float = 0.0
    desk_session_id: int | None = None
    desk_session_start: datetime | None = None

    weather_current: dict | None = None
    weather_forecast: list[dict] = field(default_factory=list)
    weather_fetched_at: datetime | None = None

    display_busy: bool = False
    active_reminder: str | None = None

    custom_image_path: str | None = None
    image_playlist: list[str] = field(default_factory=list)
    carousel_index: int = 0
    carousel_refresh_count: int = 0
    carousel_skip_next_advance: bool = False
    claude_usage_5h: float | None = None
    claude_usage_week: float | None = None
    claude_5h_reset: str | None = None
    claude_7d_reset: str | None = None
    codex_usage_5h: float | None = None
    codex_usage_week: float | None = None
    codex_5h_reset: str | None = None
    codex_7d_reset: str | None = None
    hydra_current_ml: int | None = None
    hydra_goal_ml: int | None = None
    hydra_pct: float | None = None
    hydra_updated_at: datetime | None = None
    hydra_broker_connected: bool = False
    hydra_device_online: bool = False
    printer_pct: float | None = None
    printer_remaining_min: int | None = None
    printer_task_name: str | None = None
    printer_gcode_state: str | None = None
    printer_updated_at: datetime | None = None
    printer_broker_connected: bool = False

    display_page: Literal["dashboard", "ap_mode"] = "dashboard"

    wifi_mode: Literal["client", "ap", "unknown"] = "unknown"
    ap_ssid: str = ""
    ap_password: str = ""
    ap_ip: str = ""

    started_at: datetime = field(default_factory=datetime.now)


state = AgentState()
