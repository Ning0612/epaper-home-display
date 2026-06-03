from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.state import state
from app.webui.templates.environment import _ENV_HTML

if TYPE_CHECKING:
    from app.config import Settings


_REF_PATTERNS: dict[str, re.Pattern[str]] = {
    "day":   re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "month": re.compile(r"^\d{4}-\d{2}$"),
    "year":  re.compile(r"^\d{4}$"),
}


def _validate_ref(scale: str, ref: str | None) -> str | None:
    if ref is None:
        return None
    if not _REF_PATTERNS[scale].fullmatch(ref):
        raise HTTPException(status_code=422, detail=f"ref 格式不符 scale={scale}")
    return ref


def create_environment_router(settings: "Settings") -> APIRouter:
    router = APIRouter()

    @router.get("/environment", response_class=HTMLResponse)
    async def env_page():
        return HTMLResponse(_ENV_HTML)

    @router.get("/api/env/current")
    async def env_current():
        from app.storage.logs import get_env_today_extremes
        today = await get_env_today_extremes()
        return {
            "temperature": state.temperature,
            "humidity": state.humidity,
            "today": today,
        }

    @router.get("/api/env/chart")
    async def env_chart(
        scale: str = Query("day", pattern="^(day|month|year)$"),
        ref: str | None = Query(None),
    ):
        from app.storage.logs import get_env_daily, get_env_monthly, get_env_yearly
        validated = _validate_ref(scale, ref)
        now = datetime.now()
        if scale == "day":
            target = validated or now.date().isoformat()
            return await get_env_daily(target)
        elif scale == "month":
            target = validated or now.strftime("%Y-%m")
            return await get_env_monthly(target)
        else:
            target = validated or str(now.year)
            return await get_env_yearly(target)

    @router.get("/api/env/years")
    async def env_years():
        from app.storage.logs import get_available_years
        return {"years": await get_available_years()}

    return router
