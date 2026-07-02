from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

import asyncio

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.services.weather import WeatherService
from app.webui.config_helpers import _save_to_config
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


def create_app(
    settings: "Settings",
    weather_service: WeatherService,
    display_queue: "asyncio.Queue | None" = None,
) -> FastAPI:
    if not settings.webui.session_secret:
        settings.webui.session_secret = secrets.token_hex(32)
        _save_to_config({"webui": {"session_secret": settings.webui.session_secret}})

    app = FastAPI(title="ePaper Home Display", version="0.1.0")
    # SessionMiddleware must be outermost so session is populated before _AuthMiddleware runs
    app.add_middleware(_AuthMiddleware, settings=settings)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.webui.session_secret,
        max_age=86400 * 7,
        https_only=False,
        same_site="strict",
    )

    app.include_router(create_auth_router(settings))
    app.include_router(create_read_only_router())
    app.include_router(create_settings_router(settings, weather_service))
    app.include_router(create_desk_router(settings))
    app.include_router(create_environment_router(settings))
    app.include_router(create_images_router(settings, display_queue))
    app.include_router(create_wifi_router(settings))

    @app.get("/")
    async def root():
        return RedirectResponse(url="/settings", status_code=302)

    return app
