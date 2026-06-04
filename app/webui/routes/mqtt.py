from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

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
        return {
            "connected": state.mqtt_connected,
            "broker_host": settings.mqtt.broker_host,
            "broker_port": settings.mqtt.broker_port,
            "last_rx": state.mqtt_last_rx_by_topic,
            "rx_log": state.mqtt_rx_log,
            "tx_log": state.mqtt_tx_log,
        }

    return router
