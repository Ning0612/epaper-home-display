from __future__ import annotations

from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class _AuthMiddleware(BaseHTTPMiddleware):
    _PUBLIC = frozenset({"/health", "/login", "/logout", "/ai_usage"})

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in self._PUBLIC:
            if not request.session.get("authenticated"):
                if "text/html" in request.headers.get("accept", ""):
                    return RedirectResponse(
                        url=f"/login?next={request.url.path}", status_code=302
                    )
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)
