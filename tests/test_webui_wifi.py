import asyncio
from types import SimpleNamespace

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.config import Settings
from app.state import state
from app.webui import middleware as auth_middleware
from app.webui.routes import auth
from app.webui.routes import wifi


def _request(path: str, method: str = "GET", extra_headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    headers = [] if extra_headers and any(key == b"accept" for key, _ in extra_headers) else [(b"accept", b"*/*")]
    if extra_headers:
        headers.extend(extra_headers)
    return Request({
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "scheme": "http",
        "server": ("127.0.0.1", 8000),
        "client": ("127.0.0.1", 1),
    })


async def _call_next(_request: Request) -> Response:
    return Response("ok")


def test_wifi_profile_creation_never_puts_password_in_argv(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(wifi.subprocess, "run", fake_run)

    ok, _ = wifi._prepare_wifi_profile_sync("Home WiFi", "secret-pass")

    assert ok is True
    add_command = calls[1][0]
    assert "secret-pass" not in add_command
    assert "wifi-sec.psk" not in add_command
    assert "wifi-sec.key-mgmt" in add_command


def test_wifi_activation_reads_password_from_stdin(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(wifi.subprocess, "run", fake_run)

    ok, message = wifi._activate_wifi_profile_sync("secret-pass")

    assert ok is True
    assert message == "連線成功"
    assert "secret-pass" not in captured["command"]
    assert captured["input"] == "secret-pass\n"
    assert "--ask" in captured["command"]


def test_wifi_portal_redirects_to_desk_once_client_connected(monkeypatch):
    router = wifi.create_wifi_router(Settings())
    route = next(r for r in router.routes if r.path == "/wifi")

    monkeypatch.setattr(state, "wifi_mode", "client")
    response = asyncio.run(route.endpoint(_request("/wifi")))
    assert response.status_code == 303
    assert response.headers["location"] == "/desk"


@pytest.mark.parametrize("mode", ["ap", "unknown"])
def test_wifi_portal_still_renders_before_client_connected(monkeypatch, mode):
    router = wifi.create_wifi_router(Settings())
    route = next(r for r in router.routes if r.path == "/wifi")

    monkeypatch.setattr(state, "wifi_mode", mode)
    response = asyncio.run(route.endpoint(_request("/wifi")))
    assert response.status_code == 200


def test_configured_device_requires_login_for_wifi_portal():
    auth.invalidate_session()
    settings = Settings()
    settings.webui.password_hash = "configured"
    middleware = auth_middleware._AuthMiddleware(None, settings=settings)

    response = asyncio.run(middleware.dispatch(
        _request("/wifi", extra_headers=[(b"accept", b"text/html")]),
        _call_next,
    ))

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/wifi"


@pytest.mark.parametrize("path", ["/api/wifi/scan", "/api/wifi/connect"])
def test_configured_wifi_api_requires_login(path):
    auth.invalidate_session()
    settings = Settings()
    settings.webui.password_hash = "configured"
    middleware = auth_middleware._AuthMiddleware(None, settings=settings)

    response = asyncio.run(middleware.dispatch(_request(path), _call_next))

    assert response.status_code == 401


def test_logout_requires_session_bound_csrf():
    auth.invalidate_session()
    token, _ = auth._issue_session()
    middleware = auth_middleware._AuthMiddleware(None, settings=Settings())

    response = asyncio.run(middleware.dispatch(
        _request("/logout", "POST", [(b"cookie", f"session={token}".encode())]),
        _call_next,
    ))

    assert response.status_code == 403
    assert auth.current_token == token


def test_password_change_failure_rate_limit_has_bounded_counter():
    from app.webui.routes import settings as settings_routes

    settings_routes._AUTH_CHANGE_FAILURES.clear()
    ip = "192.0.2.10"
    for _ in range(settings_routes._AUTH_CHANGE_MAX):
        settings_routes._record_auth_change_failure(ip)

    assert settings_routes._auth_change_rate_limited(ip)
    settings_routes._AUTH_CHANGE_FAILURES.clear()


def test_first_run_wifi_write_requires_preauth_csrf():
    auth.invalidate_session()
    settings = Settings()
    middleware = auth_middleware._AuthMiddleware(None, settings=settings)

    missing = asyncio.run(middleware.dispatch(_request("/api/wifi/connect", "POST"), _call_next))
    assert missing.status_code == 403

    allowed = asyncio.run(middleware.dispatch(
        _request(
            "/api/wifi/connect",
            "POST",
            [(b"x-csrf-token", auth._preauth_csrf_token().encode())],
        ),
        _call_next,
    ))
    assert allowed.status_code == 200
