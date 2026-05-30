from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.state import state


def create_read_only_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.get("/state")
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
            "codex_usage_5h": state.codex_usage_5h,
            "codex_usage_week": state.codex_usage_week,
            "codex_5h_reset": state.codex_5h_reset,
            "codex_weekly_reset": state.codex_weekly_reset,
            "claude_usage_5h": state.claude_usage_5h,
            "claude_usage_week": state.claude_usage_week,
            "claude_5h_reset": state.claude_5h_reset,
        })

    @router.get("/logs/env")
    async def get_env_logs_route(limit: int = 50):
        from app.storage.logs import get_env_logs
        return {"logs": await get_env_logs(limit)}

    @router.get("/logs/presence")
    async def get_presence_logs_route(limit: int = 50):
        from app.storage.logs import get_presence_logs
        return {"logs": await get_presence_logs(limit)}

    @router.get("/logs/events")
    async def get_events(limit: int = 50):
        from app.storage.logs import get_system_events
        return {"events": await get_system_events(limit)}

    return router
