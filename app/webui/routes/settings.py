from __future__ import annotations

import asyncio
import dataclasses
import logging
import re
import subprocess
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from app.webui.config_helpers import _save_to_config
from app.webui.models import (
    _LocationBody, _WeatherBody, _MQTTBody, _DisplayBody,
    _PresenceBody, _VoiceBody, _NotificationsBody, _GeneralBody, _AuthBody,
)
from app.webui.routes.auth import _pwd_ctx
from app.webui.templates.settings import _SETTINGS_HTML

if TYPE_CHECKING:
    from app.config import Settings
    from app.services.weather import WeatherService

logger = logging.getLogger(__name__)


def create_settings_router(settings: "Settings", weather_service: "WeatherService") -> APIRouter:
    router = APIRouter()

    @router.get("/settings", response_class=HTMLResponse)
    async def settings_page():
        lat = round(settings.weather.lat, 5)
        lon = round(settings.weather.lon, 5)
        html = (
            _SETTINGS_HTML
            .replace("__LAT__", str(lat))
            .replace("__LON__", str(lon))
        )
        return HTMLResponse(html)

    @router.get("/settings/config")
    async def get_config():
        d = dataclasses.asdict(settings)
        w = d.get("weather", {})
        api_key = w.pop("api_key", "")
        w["api_key_set"] = bool(api_key)
        dc = d.get("discord", {})
        webhook = dc.pop("webhook_url", "")
        dc["webhook_set"] = bool(webhook)
        wu = d.get("webui", {})
        wu.pop("password_hash", None)
        wu.pop("session_secret", None)
        return JSONResponse(d)

    @router.get("/settings/wifi")
    async def get_wifi():
        info: dict[str, str] = {}

        async def _run(cmd: list[str]) -> str:
            return await asyncio.to_thread(
                lambda: subprocess.check_output(
                    cmd, text=True, stderr=subprocess.DEVNULL, timeout=3
                )
            )

        try:
            ssid = (await _run(["iwgetid", "wlan0", "-r"])).strip()
            info["SSID"] = ssid or "—"
        except Exception:
            info["SSID"] = "無法取得"
        try:
            out = await _run(["ip", "-4", "addr", "show", "wlan0"])
            for line in out.splitlines():
                if "inet " in line:
                    info["IP 位址"] = line.strip().split()[1]
                    break
            else:
                info["IP 位址"] = "無法取得"
        except Exception:
            info["IP 位址"] = "無法取得"
        try:
            out = await _run(["iwconfig", "wlan0"])
            m = re.search(r"Signal level=(-?\d+)\s*dBm", out)
            info["訊號強度"] = f"{m.group(1)} dBm" if m else "無法取得"
        except Exception:
            info["訊號強度"] = "無法取得"
        return info

    @router.put("/settings/location")
    async def set_location(body: _LocationBody):
        if not (-90 <= body.lat <= 90):
            raise HTTPException(400, detail="lat must be -90..90")
        if not (-180 <= body.lon <= 180):
            raise HTTPException(400, detail="lon must be -180..180")

        lat = round(body.lat, 5)
        lon = round(body.lon, 5)
        try:
            _save_to_config({"weather": {"lat": lat, "lon": lon}})
        except Exception as exc:
            logger.error("Failed to persist location: %s", exc)
            raise HTTPException(500, detail="Failed to persist location")

        settings.weather.lat = lat
        settings.weather.lon = lon
        weather_service.set_location(lat, lon)
        return {"ok": True, "lat": lat, "lon": lon}

    @router.put("/settings/weather")
    async def set_weather(body: _WeatherBody):
        patch = body.model_dump(exclude_none=True)
        if "fetch_interval_seconds" in patch and not (60 <= patch["fetch_interval_seconds"] <= 3600):
            raise HTTPException(400, detail="fetch_interval_seconds must be 60–3600")
        if "units" in patch and patch["units"] not in ("metric", "imperial", "standard"):
            raise HTTPException(400, detail="units must be metric/imperial/standard")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"weather": patch})
        except Exception as exc:
            logger.error("Failed to persist weather settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.weather, k, v)
        return {"ok": True}

    @router.put("/settings/mqtt")
    async def set_mqtt(body: _MQTTBody):
        patch = body.model_dump(exclude_none=True)
        if "broker_host" in patch and not patch["broker_host"].strip():
            raise HTTPException(400, detail="broker_host must not be empty")
        if "broker_port" in patch and not (1 <= patch["broker_port"] <= 65535):
            raise HTTPException(400, detail="broker_port must be 1–65535")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"mqtt": patch})
        except Exception as exc:
            logger.error("Failed to persist MQTT settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.mqtt, k, v)
        return {"ok": True}

    @router.put("/settings/display")
    async def set_display(body: _DisplayBody):
        patch = body.model_dump(exclude_none=True)
        if "dashboard_trigger_second" in patch and not (0 <= patch["dashboard_trigger_second"] <= 59):
            raise HTTPException(400, detail="dashboard_trigger_second must be 0–59")
        if "full_refresh_every" in patch and not (1 <= patch["full_refresh_every"] <= 100):
            raise HTTPException(400, detail="full_refresh_every must be 1–100")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"display": patch})
        except Exception as exc:
            logger.error("Failed to persist display settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.display, k, v)
        return {"ok": True}

    @router.put("/settings/presence")
    async def set_presence(body: _PresenceBody):
        patch = body.model_dump(exclude_none=True)
        if "bright_threshold" in patch and not (0 <= patch["bright_threshold"] <= 1023):
            raise HTTPException(400, detail="bright_threshold must be 0–1023")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"sensors": {"light": patch}})
        except Exception as exc:
            logger.error("Failed to persist presence settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.sensors.light, k, v)
        return {"ok": True}

    @router.put("/settings/voice")
    async def set_voice(body: _VoiceBody):
        patch = body.model_dump(exclude_none=True)
        if "player" in patch and not patch["player"].strip():
            raise HTTPException(400, detail="player must not be empty")
        if not patch:
            return {"ok": True}

        try:
            _save_to_config({"voice": patch})
        except Exception as exc:
            logger.error("Failed to persist voice settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        for k, v in patch.items():
            setattr(settings.voice, k, v)
        return {"ok": True}

    @router.put("/settings/notifications")
    async def set_notifications(body: _NotificationsBody):
        patch = body.model_dump(exclude_none=True)
        url = patch.get("discord_webhook_url", "")
        if url and not url.startswith("https://"):
            raise HTTPException(400, detail="discord_webhook_url must start with https://")
        if "session_end_min_minutes" in patch and not (1 <= patch["session_end_min_minutes"] <= 60):
            raise HTTPException(400, detail="session_end_min_minutes must be 1–60")
        if "daily_summary_time" in patch:
            t = patch["daily_summary_time"]
            m = re.match(r"^(\d{2}):(\d{2})$", t)
            if not m or not (0 <= int(m.group(1)) <= 23) or not (0 <= int(m.group(2)) <= 59):
                raise HTTPException(400, detail="daily_summary_time must be HH:MM (00:00–23:59)")

        discord_patch: dict = {}
        if "discord_webhook_url" in patch:
            discord_patch["webhook_url"] = patch["discord_webhook_url"]
        for key in (
            "notify_device_online", "notify_session_end", "session_end_min_minutes",
            "notify_daily_summary", "daily_summary_time",
        ):
            if key in patch:
                discord_patch[key] = patch[key]

        if not discord_patch:
            return {"ok": True}

        try:
            _save_to_config({"discord": discord_patch})
        except Exception as exc:
            logger.error("Failed to persist notification settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        if "webhook_url" in discord_patch:
            settings.discord.webhook_url = discord_patch["webhook_url"]
        for key in (
            "notify_device_online", "notify_session_end", "session_end_min_minutes",
            "notify_daily_summary", "daily_summary_time",
        ):
            if key in discord_patch:
                setattr(settings.discord, key, discord_patch[key])
        return {"ok": True}

    @router.put("/settings/general")
    async def set_general(body: _GeneralBody):
        if body.timezone is None:
            return {"ok": True}
        tz = body.timezone.strip()
        if not tz:
            raise HTTPException(400, detail="timezone must not be empty")

        try:
            _save_to_config({"timezone": tz})
        except Exception as exc:
            logger.error("Failed to persist general settings: %s", exc)
            raise HTTPException(500, detail="Failed to persist settings")

        settings.timezone = tz
        return {"ok": True}

    @router.put("/settings/auth")
    async def set_auth(body: _AuthBody):
        if not settings.webui.password_hash:
            raise HTTPException(400, detail="No password configured. Use the login page for first-time setup.")
        if not _pwd_ctx.verify(body.current_password, settings.webui.password_hash):
            raise HTTPException(403, detail="目前密碼錯誤")
        if len(body.new_password) < 8:
            raise HTTPException(400, detail="密碼長度至少 8 個字元")
        new_hash = _pwd_ctx.hash(body.new_password)
        _save_to_config({"webui": {"password_hash": new_hash}})
        settings.webui.password_hash = new_hash
        return {"ok": True}

    return router
