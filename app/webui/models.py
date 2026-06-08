from __future__ import annotations

import math

from pydantic import BaseModel, field_validator


class _LocationBody(BaseModel):
    lat: float
    lon: float


class _WeatherBody(BaseModel):
    api_key: str | None = None
    units: str | None = None
    fetch_interval_seconds: int | None = None


class _MQTTBody(BaseModel):
    broker_host: str | None = None
    broker_port: int | None = None
    client_id: str | None = None
    username: str | None = None
    password: str | None = None


class _DisplayBody(BaseModel):
    model: str | None = None
    dashboard_interval_minutes: int | None = None
    full_refresh_every: int | None = None


class _PresenceBody(BaseModel):
    bright_threshold: int | None = None


class _VoiceBody(BaseModel):
    enabled: bool | None = None
    player: str | None = None
    tts_engine: str | None = None
    tts_language: str | None = None
    tts_speed: int | None = None
    volume: int | None = None
    alsa_mixer_control: str | None = None


class _VoiceTestBody(BaseModel):
    volume: int | None = None
    alsa_mixer_control: str | None = None
    tts_engine: str | None = None
    tts_language: str | None = None
    tts_speed: int | None = None


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


class _CropBody(BaseModel):
    x: float
    y: float
    w: float
    h: float

    @field_validator("x", "y", "w", "h")
    @classmethod
    def _must_be_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("must be a finite number")
        return v


class _TransformBody(BaseModel):
    rotate: int = 0
    flip_x: bool = False
    flip_y: bool = False


class _PreviewBody(BaseModel):
    id: str
    crop: _CropBody
    transform: _TransformBody = _TransformBody()


class _ConfirmBody(BaseModel):
    crop: _CropBody
    transform: _TransformBody = _TransformBody()


class _CarouselBody(BaseModel):
    enabled: bool | None = None
    interval_refreshes: int | None = None
    mode: str | None = None  # "sequential" | "random"
