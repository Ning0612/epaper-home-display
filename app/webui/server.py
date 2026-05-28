from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.state import state

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


def create_app(settings: "Settings") -> FastAPI:
    app = FastAPI(title="ePaper Home Display", version="0.1.0")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/state")
    async def get_state():
        return JSONResponse({
            "temperature": state.temperature,
            "humidity": state.humidity,
            "light_raw": state.light_raw,
            "light_is_bright": state.light_is_bright,
            "presence": state.presence,
            "presence_score": state.presence_score,
            "weather_current": state.weather_current,
            "weather_forecast": state.weather_forecast,
            "weather_fetched_at": state.weather_fetched_at.isoformat() if state.weather_fetched_at else None,
            "last_door_event": state.last_door_event,
            "last_face_event": state.last_face_event,
            "last_alert": state.last_alert,
            "security_status": state.security_status,
            "active_reminder": state.active_reminder,
            "display_busy": state.display_busy,
            "started_at": state.started_at.isoformat(),
        })

    @app.get("/logs/env")
    async def get_env_logs(limit: int = 50):
        from app.storage.logs import get_env_logs
        return {"logs": await get_env_logs(limit)}

    @app.get("/logs/presence")
    async def get_presence_logs(limit: int = 50):
        from app.storage.logs import get_presence_logs
        return {"logs": await get_presence_logs(limit)}

    @app.get("/logs/events")
    async def get_events(limit: int = 50):
        from app.storage.logs import get_system_events
        return {"events": await get_system_events(limit)}

    return app
