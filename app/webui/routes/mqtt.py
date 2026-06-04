from __future__ import annotations

import io
from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

from app.state import state
from app.webui.templates.mqtt import _MQTT_HTML

if TYPE_CHECKING:
    from app.config import Settings


def create_mqtt_router(settings: "Settings") -> APIRouter:
    router = APIRouter()

    @router.get("/mqtt", response_class=HTMLResponse)
    async def mqtt_page():
        return HTMLResponse(_MQTT_HTML)

    @router.get("/api/mqtt/status")
    async def mqtt_status():
        frame_at = state.last_camera_frame_at.isoformat() if state.last_camera_frame_at else None
        return {
            "connected": state.mqtt_connected,
            "broker_host": settings.mqtt.broker_host,
            "broker_port": settings.mqtt.broker_port,
            "last_rx": state.mqtt_last_rx_by_topic,
            "rx_log": state.mqtt_rx_log,
            "tx_log": state.mqtt_tx_log,
            "camera_frame_at": frame_at,
            "camera_available": state.last_snapshot_image is not None and frame_at is not None,
        }

    @router.get("/api/mqtt/camera/latest", response_class=Response)
    async def camera_latest():
        """Return the latest MQTT camera frame as JPEG, or 204 when none available."""
        img = state.last_snapshot_image
        if img is None or state.last_camera_frame_at is None:
            return Response(status_code=204)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return Response(content=buf.getvalue(), media_type="image/jpeg")

    return router
