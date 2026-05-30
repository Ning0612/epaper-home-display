from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from app.state import state
from app.webui.models import _AIUsageBody


def create_ai_usage_router() -> APIRouter:
    router = APIRouter()

    @router.post("/ai_usage")
    async def post_ai_usage(body: _AIUsageBody):
        from app.storage.logs import log_ai_usage
        if body.codex_5h_pct is not None:
            state.codex_usage_5h = max(0.0, min(1.0, body.codex_5h_pct / 100.0))
        if body.codex_5h_reset is not None:
            state.codex_5h_reset = body.codex_5h_reset
        if body.codex_weekly_pct is not None:
            state.codex_usage_week = max(0.0, min(1.0, body.codex_weekly_pct / 100.0))
        if body.codex_weekly_reset is not None:
            state.codex_weekly_reset = body.codex_weekly_reset
        if body.claude_5h_pct is not None:
            state.claude_usage_5h = max(0.0, min(1.0, body.claude_5h_pct / 100.0))
        if body.claude_5h_reset is not None:
            state.claude_5h_reset = body.claude_5h_reset
        await log_ai_usage(body.model_dump())
        return {"ok": True, "updated_at": datetime.now().isoformat()}

    return router
