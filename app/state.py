from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class AgentState:
    temperature: float | None = None
    humidity: float | None = None
    light_raw: int | None = None
    light_is_bright: bool = False

    presence: Literal["OCCUPIED", "UNOCCUPIED", "UNKNOWN"] = "UNKNOWN"
    presence_score: float = 0.0
    desk_session_id: int | None = None
    desk_session_start: datetime | None = None

    weather_current: dict | None = None
    weather_forecast: list[dict] = field(default_factory=list)
    weather_fetched_at: datetime | None = None

    last_door_event: dict | None = None
    last_face_event: dict | None = None
    last_alert: dict | None = None
    last_alarm_decision: str | None = None
    alert_face_event: dict | None = None
    security_status: dict | None = None

    mqtt_connected: bool = False
    mqtt_last_rx_by_topic: dict = field(default_factory=dict)
    mqtt_rx_log: list = field(default_factory=list)  # newest first, max 50
    mqtt_tx_log: list = field(default_factory=list)  # newest first, max 20

    display_busy: bool = False
    active_reminder: str | None = None

    custom_image_path: str | None = None
    image_playlist: list[str] = field(default_factory=list)
    carousel_index: int = 0
    carousel_refresh_count: int = 0
    claude_usage_5h: float | None = None
    claude_usage_week: float | None = None
    claude_5h_reset: str | None = None
    claude_7d_reset: str | None = None
    codex_usage_5h: float | None = None
    codex_usage_week: float | None = None
    codex_5h_reset: str | None = None
    codex_7d_reset: str | None = None

    display_page: Literal["dashboard", "alert", "ap_mode"] = "dashboard"
    last_snapshot_image: Any = None          # PIL Image | None — used by e-paper renderer
    last_camera_frame_bytes: bytes | None = None  # raw JPEG — served directly to WebUI
    last_camera_frame_at: datetime | None = None
    alert_page_started_at: datetime | None = None
    alert_last_triggered_at: datetime | None = None
    alert_dismissed_at: datetime | None = None

    wifi_mode: Literal["client", "ap", "unknown"] = "unknown"
    ap_ssid: str = ""
    ap_password: str = ""
    ap_ip: str = ""

    started_at: datetime = field(default_factory=datetime.now)


state = AgentState()
