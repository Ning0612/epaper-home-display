from __future__ import annotations

import io
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from app.state import state

if TYPE_CHECKING:
    from app.config import Settings


def create_read_only_router(settings: "Settings | None" = None) -> APIRouter:
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
            "display_page": state.display_page,
            "alert_last_triggered_at": (
                state.alert_last_triggered_at.isoformat()
                if state.alert_last_triggered_at else None
            ),
            "started_at": state.started_at.isoformat(),
            "codex_usage_5h": state.codex_usage_5h,
            "codex_usage_week": state.codex_usage_week,
            "codex_5h_reset": state.codex_5h_reset,
            "codex_weekly_reset": state.codex_weekly_reset,
            "claude_usage_5h": state.claude_usage_5h,
            "claude_usage_week": state.claude_usage_week,
            "claude_5h_reset": state.claude_5h_reset,
            # last_snapshot_image is a PIL Image — intentionally excluded from JSON
        })

    @router.get("/api/preview/alert", response_class=Response)
    async def preview_alert_page():
        """Return a PNG rendering of the alert page (for WebUI simulation/debug)."""
        import asyncio
        from app.display.renderer_alert import render_alert_page

        _settings = settings
        img = await asyncio.to_thread(render_alert_page, state, _settings, datetime.now())
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")

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
