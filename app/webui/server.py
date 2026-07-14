from __future__ import annotations

from typing import TYPE_CHECKING

import asyncio

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.services.weather import WeatherService
from app.webui.middleware import _AuthMiddleware
from app.webui.routes.auth import create_auth_router
from app.webui.routes.desk import create_desk_router
from app.webui.routes.environment import create_environment_router
from app.webui.routes.images import create_images_router
from app.webui.routes.read_only import create_read_only_router
from app.webui.routes.settings import create_settings_router
from app.webui.routes.wifi import create_wifi_router

if TYPE_CHECKING:
    from app.config import Settings
    from app.services.mqtt_client import MQTTService
    from app.services.printer_mqtt import BambuMQTTService


def create_app(
    settings: "Settings",
    weather_service: WeatherService,
    mqtt_service: "MQTTService",
    printer_service: "BambuMQTTService",
    display_queue: "asyncio.Queue | None" = None,
) -> FastAPI:
    app = FastAPI(title="ePaper Home Display", version="0.1.0")
    app.add_middleware(_AuthMiddleware, settings=settings)

    app.include_router(create_auth_router(settings))
    app.include_router(create_read_only_router())
    app.include_router(create_settings_router(settings, weather_service, mqtt_service, printer_service))
    app.include_router(create_desk_router(settings))
    app.include_router(create_environment_router(settings))
    app.include_router(create_images_router(settings, display_queue))
    app.include_router(create_wifi_router(settings))

    @app.get("/")
    async def root():
        return RedirectResponse(url="/settings", status_code=302)

    return app
