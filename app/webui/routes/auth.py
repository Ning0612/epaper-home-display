from __future__ import annotations

import asyncio
import hmac
import secrets
import time
from collections import defaultdict
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlsplit

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from starlette.requests import Request
from starlette.responses import Response

from app.webui.config_helpers import _save_to_config
from app.webui.templates.login import _render_login

if TYPE_CHECKING:
    from app.config import Settings


_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# The device intentionally keeps one server-side session slot.  A new login
# replaces the previous token, and a reboot clears these module-level values.
current_token: str | None = None
session_start: float | None = None
last_activity: float | None = None
session_csrf: str | None = None

_PREAUTH_CSRF_TOKEN = secrets.token_urlsafe(32)
_SESSION_IDLE_SECONDS = 30 * 60
_SESSION_ABSOLUTE_SECONDS = 24 * 60 * 60
_SESSION_COOKIE = "session"
_CSRF_COOKIE = "csrf"

# In-memory login rate limiter: tracks recent failure timestamps per client IP.
_login_failures: dict[str, list[float]] = defaultdict(list)
_RATE_WINDOW = 300  # 5-minute sliding window
_RATE_MAX = 10       # max failures before temporary block
_RATE_IP_CAP = 1024  # prevent spoofed source addresses from growing memory forever


def _issue_session(now: float | None = None) -> tuple[str, str]:
    """Rotate the single session slot and return its token and bound CSRF token."""
    global current_token, session_start, last_activity, session_csrf
    timestamp = time.monotonic() if now is None else now
    current_token = secrets.token_urlsafe(32)  # 256 bits from the OS CSPRNG
    session_csrf = secrets.token_urlsafe(32)
    session_start = timestamp
    last_activity = timestamp
    return current_token, session_csrf


def invalidate_session() -> None:
    """Revoke the current server-side session immediately."""
    global current_token, session_start, last_activity, session_csrf
    current_token = None
    session_start = None
    last_activity = None
    session_csrf = None


def _session_cookie_name(request: Request) -> str:
    return "__Host-session" if request.url.scheme.lower() == "https" else _SESSION_COOKIE


def _set_csrf_cookie(response: Response, request: Request, token: str) -> None:
    secure = request.url.scheme.lower() == "https"
    response.set_cookie(
        _CSRF_COOKIE,
        token,
        max_age=_SESSION_ABSOLUTE_SECONDS,
        httponly=False,
        secure=secure,
        samesite="strict",
        path="/",
    )


def _set_auth_cookies(response: Response, request: Request, token: str, csrf_token: str) -> None:
    secure = request.url.scheme.lower() == "https"
    response.set_cookie(
        _session_cookie_name(request),
        token,
        max_age=_SESSION_ABSOLUTE_SECONDS,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )
    _set_csrf_cookie(response, request, csrf_token)


def _clear_auth_cookies(response: Response, request: Request) -> None:
    response.delete_cookie(_SESSION_COOKIE, path="/")
    response.delete_cookie("__Host-session", path="/")
    response.delete_cookie(_CSRF_COOKIE, path="/")


def _valid_session(request: Request, now: float | None = None) -> bool:
    """Validate and touch the single session slot without yielding to another request."""
    global last_activity
    if current_token is None or session_start is None or last_activity is None:
        return False
    supplied = request.cookies.get(_session_cookie_name(request), "")
    if not supplied or not hmac.compare_digest(supplied, current_token):
        return False
    timestamp = time.monotonic() if now is None else now
    if timestamp - session_start > _SESSION_ABSOLUTE_SECONDS or timestamp - last_activity > _SESSION_IDLE_SECONDS:
        invalidate_session()
        return False
    # This check and update are intentionally synchronous and atomic on the
    # single asyncio event loop; do not insert an await between them.
    last_activity = timestamp
    return True


def _current_csrf_token() -> str | None:
    return session_csrf


def _preauth_csrf_token() -> str:
    return _PREAUTH_CSRF_TOKEN


def _csrf_matches(supplied: str | None, expected: str | None) -> bool:
    return bool(supplied and expected and hmac.compare_digest(supplied, expected))


def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    recent = [timestamp for timestamp in _login_failures.get(ip, []) if now - timestamp < _RATE_WINDOW]
    _login_failures[ip] = recent
    return len(recent) >= _RATE_MAX


def _record_failure(ip: str) -> int:
    """Append a failure timestamp and cap the number of tracked client IPs."""
    now = time.monotonic()
    recent = [timestamp for timestamp in _login_failures.get(ip, []) if now - timestamp < _RATE_WINDOW]
    recent.append(now)
    if ip not in _login_failures and len(_login_failures) >= _RATE_IP_CAP:
        oldest_ip = min(_login_failures, key=lambda key: _login_failures[key][-1] if _login_failures[key] else 0)
        _login_failures.pop(oldest_ip, None)
    _login_failures[ip] = recent
    return len(recent)


def _clear_login_failures(ip: str) -> None:
    _login_failures.pop(ip, None)


def _sanitize_next(next_url: str) -> str:
    """Reject open-redirect candidates; only allow safe internal-path redirects."""
    try:
        parts = urlsplit(next_url)
    except Exception:
        return "/settings"
    if parts.scheme or parts.netloc:
        return "/settings"
    decoded = unquote(parts.path)
    if not decoded.startswith("/") or decoded.startswith("//") or "\\" in decoded:
        return "/settings"
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in decoded):
        return "/settings"
    return parts.path or "/settings"


def _login_response(
    request: Request,
    next_url: str,
    error: str = "",
    is_setup: bool = False,
    status_code: int = 200,
) -> HTMLResponse:
    response = HTMLResponse(
        _render_login(
            next_url=next_url,
            error=error,
            is_setup=is_setup,
            csrf_token=_PREAUTH_CSRF_TOKEN,
        ),
        status_code=status_code,
    )
    _set_csrf_cookie(response, request, _PREAUTH_CSRF_TOKEN)
    response.headers["Cache-Control"] = "no-store"
    return response


def _redirect_with_session(request: Request, url: str, token: str, csrf_token: str) -> RedirectResponse:
    response = RedirectResponse(url=url, status_code=303)
    _set_auth_cookies(response, request, token, csrf_token)
    response.headers["Cache-Control"] = "no-store"
    return response


def create_auth_router(settings: "Settings") -> APIRouter:
    router = APIRouter()

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, next: str = "/settings"):
        is_setup = not bool(settings.webui.password_hash)
        return _login_response(request, _sanitize_next(next), is_setup=is_setup)

    @router.post("/login", response_class=HTMLResponse)
    async def login_post(
        request: Request,
        password: str = Form(...),
        password_confirm: str = Form(""),
        next: str = Form("/settings"),
        csrf: str = Form(""),
    ):
        client_ip = request.client.host if request.client else "unknown"
        safe_next = _sanitize_next(next)
        is_setup = not bool(settings.webui.password_hash)

        if not _csrf_matches(csrf, _PREAUTH_CSRF_TOKEN):
            return _login_response(request, safe_next, "登入頁已過期，請重新載入後再試", is_setup=is_setup, status_code=403)
        if _is_rate_limited(client_ip):
            return _login_response(request, safe_next, "嘗試次數過多，請稍後再試", is_setup=is_setup, status_code=429)

        if is_setup:
            if len(password) < 8:
                count = _record_failure(client_ip)
                await asyncio.sleep(min(count * 0.25, 2.0))
                return _login_response(request, safe_next, "密碼長度至少 8 個字元", is_setup=True, status_code=400)
            if password != password_confirm:
                count = _record_failure(client_ip)
                await asyncio.sleep(min(count * 0.25, 2.0))
                return _login_response(request, safe_next, "兩次密碼不一致", is_setup=True, status_code=400)
            new_hash = _pwd_ctx.hash(password)
            _save_to_config({"webui": {"password_hash": new_hash}})
            settings.webui.password_hash = new_hash
            _clear_login_failures(client_ip)
            token, csrf_token = _issue_session()
            return _redirect_with_session(request, safe_next, token, csrf_token)

        if not _pwd_ctx.verify(password, settings.webui.password_hash):
            count = _record_failure(client_ip)
            await asyncio.sleep(min(count * 0.5, 3.0))
            return _login_response(request, safe_next, "密碼錯誤", status_code=401)

        _clear_login_failures(client_ip)
        token, csrf_token = _issue_session()
        return _redirect_with_session(request, safe_next, token, csrf_token)

    @router.post("/logout")
    async def logout(request: Request):
        invalidate_session()
        response = RedirectResponse(url="/login", status_code=303)
        _clear_auth_cookies(response, request)
        response.headers["Cache-Control"] = "no-store"
        return response

    return router
