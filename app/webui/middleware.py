from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.webui.routes.auth import (
    _current_csrf_token,
    _csrf_matches,
    _preauth_csrf_token,
    _set_csrf_cookie,
    _valid_session,
)

if TYPE_CHECKING:
    from app.config import Settings


class _AuthMiddleware(BaseHTTPMiddleware):
    _PUBLIC = frozenset({"/health", "/login"})
    # AP mode is a local setup portal.  It is public only before an admin
    # password has ever been configured; afterwards it uses the normal session.
    _PUBLIC_API_PREFIX = "/api/wifi/"
    _SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

    def __init__(self, app, settings: "Settings | None" = None, **kwargs):
        super().__init__(app, **kwargs)
        self._settings = settings

    @staticmethod
    def _wants_html(request: Request) -> bool:
        return "text/html" in request.headers.get("accept", "")

    @staticmethod
    def _login_redirect(request: Request) -> RedirectResponse:
        next_url = quote(request.url.path, safe="/")
        return RedirectResponse(url=f"/login?next={next_url}", status_code=303)

    @staticmethod
    def _unauthorized(request: Request, detail: str = "Unauthorized") -> Response:
        if _AuthMiddleware._wants_html(request):
            return _AuthMiddleware._login_redirect(request)
        return JSONResponse({"detail": detail}, status_code=401)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_wifi_public = path == "/wifi" or path.startswith(self._PUBLIC_API_PREFIX)

        if is_wifi_public:
            password_configured = bool(
                self._settings
                and getattr(getattr(self._settings, "webui", None), "password_hash", "")
            )
            if password_configured and not _valid_session(request):
                return self._unauthorized(request)
            session_valid = _valid_session(request) if not password_configured else True
            request.state.authenticated = session_valid
            # First-run AP setup uses the per-process pre-auth token.  A
            # configured device must use the session-bound token instead.
            expected_csrf = _current_csrf_token() if session_valid else _preauth_csrf_token()
            request.state.csrf_token = expected_csrf
            if request.method.upper() not in self._SAFE_METHODS:
                supplied = request.headers.get("x-csrf-token")
                if not _csrf_matches(supplied, expected_csrf):
                    return JSONResponse({"detail": "CSRF token invalid"}, status_code=403)
            response = await call_next(request)
            if path == "/wifi" and request.method.upper() == "GET":
                _set_csrf_cookie(response, request, expected_csrf or _preauth_csrf_token())
            response.headers["Cache-Control"] = "no-store"
            return response

        if path in self._PUBLIC:
            response = await call_next(request)
            if path == "/login" and request.method.upper() == "GET":
                _set_csrf_cookie(response, request, _preauth_csrf_token())
            response.headers["Cache-Control"] = "no-store"
            return response

        if not _valid_session(request):
            return self._unauthorized(request)

        request.state.authenticated = True
        request.state.csrf_token = _current_csrf_token()
        if request.method.upper() not in self._SAFE_METHODS:
            supplied = request.headers.get("x-csrf-token")
            if not _csrf_matches(supplied, _current_csrf_token()):
                return JSONResponse({"detail": "CSRF token invalid"}, status_code=403)

        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        if _current_csrf_token():
            _set_csrf_cookie(response, request, _current_csrf_token())
        return response
