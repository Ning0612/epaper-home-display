import pytest
from starlette.requests import Request

from app.webui.routes import auth


def _request_with_cookie(value: str, scheme: str = "http") -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [(b"cookie", value.encode())],
        "scheme": scheme,
        "server": ("127.0.0.1", 8000),
        "client": ("127.0.0.1", 1),
    })


@pytest.fixture(autouse=True)
def reset_auth_state():
    auth.invalidate_session()
    auth._login_failures.clear()
    yield
    auth.invalidate_session()


def test_session_rotation_replaces_previous_token():
    old_token, _ = auth._issue_session(now=100.0)
    new_token, _ = auth._issue_session(now=200.0)

    assert not auth._valid_session(_request_with_cookie(f"session={old_token}"), now=200.0)
    assert auth._valid_session(_request_with_cookie(f"session={new_token}"), now=200.0)


def test_session_expires_after_idle_timeout():
    token, _ = auth._issue_session(now=100.0)

    assert not auth._valid_session(
        _request_with_cookie(f"session={token}"),
        now=100.0 + auth._SESSION_IDLE_SECONDS + 1,
    )


def test_session_expires_after_absolute_timeout_even_if_recently_touched():
    token, _ = auth._issue_session(now=300.0)
    auth.last_activity = 300.0 + auth._SESSION_ABSOLUTE_SECONDS

    assert auth._valid_session(
        _request_with_cookie(f"session={token}"),
        now=300.0 + auth._SESSION_ABSOLUTE_SECONDS,
    )
    assert not auth._valid_session(
        _request_with_cookie(f"session={token}"),
        now=300.0 + auth._SESSION_ABSOLUTE_SECONDS + 1,
    )


def test_csrf_and_next_url_guards():
    _, csrf_token = auth._issue_session(now=100.0)

    assert auth._csrf_matches(csrf_token, csrf_token)
    assert not auth._csrf_matches("wrong", csrf_token)
    assert auth._sanitize_next("/settings?tab=weather") == "/settings"
    assert auth._sanitize_next("https://evil.example/") == "/settings"
    assert auth._sanitize_next("//evil.example/") == "/settings"
    assert auth._sanitize_next("/%2f%2fevil.example/") == "/settings"


def test_session_cookie_name_uses_host_prefix_only_for_https():
    assert auth._session_cookie_name(_request_with_cookie("", "http")) == "session"
    assert auth._session_cookie_name(_request_with_cookie("", "https")) == "__Host-session"
