from __future__ import annotations

from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class _AuthMiddleware(BaseHTTPMiddleware):
    _PUBLIC = frozenset({"/health", "/login", "/logout"})
    # Prefix-matched public routes (AP mode WiFi portal — no login required)
    _PUBLIC_PREFIXES = ("/wifi", "/api/wifi/")

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
        return await call_next(request)
