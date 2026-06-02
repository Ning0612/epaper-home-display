from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from collections import defaultdict
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, unquote

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from starlette.requests import Request

from app.webui.config_helpers import _save_to_config
from app.webui.templates.login import _render_login

if TYPE_CHECKING:
    from app.config import Settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory login rate limiter: tracks recent failure timestamps per client IP.
# Persists across requests but not across process restarts (intentional for LAN device).
_login_failures: dict[str, list[float]] = defaultdict(list)
_RATE_WINDOW = 300    # 5-minute sliding window
_RATE_MAX = 10        # max failures before temporary block


def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    recent = [t for t in _login_failures.get(ip, []) if now - t < _RATE_WINDOW]
    _login_failures[ip] = recent
    return len(recent) >= _RATE_MAX


def _record_failure(ip: str) -> int:
    """Append a failure timestamp; return count of recent failures."""
    now = time.monotonic()
    recent = [t for t in _login_failures.get(ip, []) if now - t < _RATE_WINDOW]
    recent.append(now)
    _login_failures[ip] = recent
    return len(recent)


def _pw_version(pw_hash: str, secret: str = "") -> str:
    """HMAC of bcrypt hash with session secret — changes when password changes, never exposes hash bits."""
    if not pw_hash:
        return ""
    return hmac.new(secret.encode(), pw_hash.encode(), hashlib.sha256).hexdigest()[:16]


def _sanitize_next(next_url: str) -> str:
    """Reject open-redirect candidates; only allow safe internal-path redirects."""
    try:
        parts = urlsplit(next_url)
    except Exception:
        return "/settings"
    if parts.scheme or parts.netloc:
        return "/settings"
    raw_path = parts.path
    decoded = unquote(raw_path)  # decode once to catch %5c → \, %2f%2f → //
    if not decoded.startswith("/") or decoded.startswith("//") or "\\" in decoded:
        return "/settings"
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in decoded):
        return "/settings"
    return raw_path


def create_auth_router(settings: "Settings") -> APIRouter:
    router = APIRouter()

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(next: str = "/settings"):
        is_setup = not bool(settings.webui.password_hash)
        return HTMLResponse(_render_login(next_url=_sanitize_next(next), is_setup=is_setup))

    @router.post("/login", response_class=HTMLResponse)
    async def login_post(
        request: Request,
        password: str = Form(...),
        password_confirm: str = Form(""),
        next: str = Form("/settings"),
    ):
        client_ip = (request.client.host if request.client else "unknown")
        is_setup = not bool(settings.webui.password_hash)
        safe_next = _sanitize_next(next)

        if not is_setup and _is_rate_limited(client_ip):
            return HTMLResponse(
                _render_login(safe_next, "嘗試次數過多，請稍後再試", is_setup=False),
                status_code=429,
            )

        if is_setup:
            if len(password) < 8:
                return HTMLResponse(
                    _render_login(safe_next, "密碼長度至少 8 個字元", is_setup=True), status_code=400
                )
            if password != password_confirm:
                return HTMLResponse(
                    _render_login(safe_next, "兩次密碼不一致", is_setup=True), status_code=400
                )
            new_hash = _pwd_ctx.hash(password)
            if settings.webui.password_hash:
                is_setup = False
            else:
                _save_to_config({"webui": {"password_hash": new_hash}})
                settings.webui.password_hash = new_hash
                request.session["authenticated"] = True
                request.session["pw_version"] = _pw_version(new_hash, settings.webui.session_secret)
                return RedirectResponse(url=safe_next, status_code=302)

        if not _pwd_ctx.verify(password, settings.webui.password_hash):
            count = _record_failure(client_ip)
            await asyncio.sleep(min(count * 0.5, 3.0))  # progressive backoff, max 3 s
            return HTMLResponse(
                _render_login(safe_next, "密碼錯誤", is_setup=False), status_code=401
            )
        request.session["authenticated"] = True
        request.session["pw_version"] = _pw_version(
            settings.webui.password_hash, settings.webui.session_secret
        )
        return RedirectResponse(url=safe_next, status_code=302)

    @router.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse(url="/login", status_code=302)

    return router
