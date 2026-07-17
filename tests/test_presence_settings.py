from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.config import LightConfig, Settings
from app.webui import models as webui_models
from app.webui.routes import settings as settings_routes


def _presence_endpoint(settings: Settings):
    router = settings_routes.create_settings_router(settings, Mock(), Mock(), Mock())
    return next(route.endpoint for route in router.routes if route.path == "/settings/presence")


def test_presence_debounce_defaults():
    light = Settings().sensors.light

    assert light.unoccupied_after_seconds == 180
    assert light.occupied_after_seconds == 30


@pytest.mark.parametrize(
    "kwargs",
    [
        {"unoccupied_after_seconds": -1},
        {"occupied_after_seconds": 86401},
    ],
)
def test_light_config_rejects_invalid_debounce_durations(kwargs):
    with pytest.raises(ValueError):
        LightConfig(**kwargs)


@pytest.mark.asyncio
async def test_presence_settings_are_persisted_and_applied(monkeypatch):
    settings = Settings()
    saved = {}
    monkeypatch.setattr(settings_routes, "_save_to_config", saved.update)

    result = await _presence_endpoint(settings)(
        webui_models._PresenceBody(
            bright_threshold=650,
            unoccupied_after_seconds=180,
            occupied_after_seconds=30,
        )
    )

    assert result == {"ok": True}
    assert saved == {
        "sensors": {
            "light": {
                "bright_threshold": 650,
                "unoccupied_after_seconds": 180,
                "occupied_after_seconds": 30,
            }
        }
    }
    assert settings.sensors.light.bright_threshold == 650
    assert settings.sensors.light.unoccupied_after_seconds == 180
    assert settings.sensors.light.occupied_after_seconds == 30


@pytest.mark.asyncio
async def test_presence_settings_reject_negative_or_excessive_durations():
    endpoint = _presence_endpoint(Settings())

    for field, value in (
        ("unoccupied_after_seconds", -1),
        ("occupied_after_seconds", 86401),
    ):
        body = webui_models._PresenceBody(**{field: value})
        with pytest.raises(HTTPException) as exc_info:
            await endpoint(body)
        assert exc_info.value.status_code == 400
