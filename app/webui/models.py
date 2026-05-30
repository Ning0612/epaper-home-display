from __future__ import annotations

from pydantic import BaseModel


class _LocationBody(BaseModel):
    lat: float
    lon: float


class _AIUsageBody(BaseModel):
    codex_5h_pct: float | None = None
    codex_5h_reset: str | None = None
    codex_weekly_pct: float | None = None
    codex_weekly_reset: str | None = None
    claude_5h_pct: float | None = None
    claude_5h_reset: str | None = None


class _WeatherBody(BaseModel):
    api_key: str | None = None
    units: str | None = None
    fetch_interval_seconds: int | None = None


class _MQTTBody(BaseModel):
    broker_host: str | None = None
    broker_port: int | None = None
    client_id: str | None = None


class _DisplayBody(BaseModel):
    model: str | None = None
    dashboard_trigger_second: int | None = None
    full_refresh_every: int | None = None


class _PresenceBody(BaseModel):
    bright_threshold: int | None = None


class _VoiceBody(BaseModel):
    enabled: bool | None = None
    player: str | None = None


class _NotificationsBody(BaseModel):
    discord_webhook_url: str | None = None
    notify_device_online: bool | None = None
    notify_session_end: bool | None = None
    session_end_min_minutes: int | None = None
    notify_daily_summary: bool | None = None
    daily_summary_time: str | None = None


class _GeneralBody(BaseModel):
    timezone: str | None = None


class _AuthBody(BaseModel):
    current_password: str
    new_password: str
