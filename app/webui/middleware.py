from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.webui.routes.auth import _pw_version

if TYPE_CHECKING:
    from app.config import Settings


class _AuthMiddleware(BaseHTTPMiddleware):
    _PUBLIC = frozenset({"/health", "/login", "/logout"})
    # Prefix-matched public routes (AP mode WiFi portal — no login required)
    _PUBLIC_PREFIXES = ("/wifi", "/api/wifi/")

    def __init__(self, app, settings: "Settings | None" = None, **kwargs):
        super().__init__(app, **kwargs)
        self._settings = settings

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_public = (
            path in self._PUBLIC
            or any(path.startswith(p) for p in self._PUBLIC_PREFIXES)
        )
        if not is_public:
            if not request.session.get("authenticated"):
                if "text/html" in request.headers.get("accept", ""):
                    return RedirectResponse(
                        url=f"/login?next={path}", status_code=302
                    )
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            # Invalidate sessions that pre-date a password change
            if self._settings and self._settings.webui.password_hash:
                expected = _pw_version(
                    self._settings.webui.password_hash,
                    self._settings.webui.session_secret,
                )
                if request.session.get("pw_version") != expected:
                    request.session.clear()
                    if "text/html" in request.headers.get("accept", ""):
                        return RedirectResponse(
                            url=f"/login?next={path}", status_code=302
                        )
                    return JSONResponse({"detail": "Session expired"}, status_code=401)
        return await call_next(request)
