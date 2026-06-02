from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.state import state
from app.webui.templates.desk import _DESK_HTML

if TYPE_CHECKING:
    from app.config import Settings


def create_desk_router(settings: "Settings") -> APIRouter:
    router = APIRouter()

    @router.get("/desk", response_class=HTMLResponse)
    async def desk_page():
        return HTMLResponse(_DESK_HTML)

    @router.get("/api/desk/stats")
    async def desk_stats():
        from app.storage.logs import get_sessions_for_date
        now = datetime.now()
        today_sessions = await get_sessions_for_date(now.date())

        today_completed_sec = sum(
            s["duration_seconds"] for s in today_sessions
            if s["duration_seconds"] is not None
        )
        ongoing_sec = 0
        if state.desk_session_start is not None and state.desk_session_start.date() == now.date():
            ongoing_sec = int((now - state.desk_session_start).total_seconds())

        today_count = len([s for s in today_sessions if s["duration_seconds"] is not None])
        if state.desk_session_start is not None and state.desk_session_start.date() == now.date():
            today_count += 1

        current_segment_sec = 0
        last_change_ts = None
        if state.presence == "OCCUPIED" and state.desk_session_start:
            current_segment_sec = int((now - state.desk_session_start).total_seconds())
            last_change_ts = state.desk_session_start.isoformat()
        elif state.presence == "UNOCCUPIED":
            completed = [s for s in today_sessions if s["end_ts"] is not None]
            if completed:
                last_end = max(s["end_ts"] for s in completed)
                try:
                    last_end_dt = datetime.fromisoformat(last_end)
                    current_segment_sec = int((now - last_end_dt).total_seconds())
                    last_change_ts = last_end
                except ValueError:
                    pass

        return {
            "presence": state.presence,
            "light_raw": state.light_raw,
            "threshold": settings.sensors.light.bright_threshold,
            "today_total_seconds": today_completed_sec + ongoing_sec,
            "today_session_count": today_count,
            "current_segment_seconds": current_segment_sec,
            "session_start_ts": state.desk_session_start.isoformat() if state.desk_session_start else None,
            "last_change_ts": last_change_ts,
        }

    @router.get("/api/desk/history")
    async def desk_history():
        from app.storage.logs import get_sessions_last_n_days
        now = datetime.now()
        all_sessions = await get_sessions_last_n_days(30)

        cutoff_24h = (now - timedelta(hours=24)).isoformat()
        timeline_24h = [
            s for s in all_sessions
            if (s["end_ts"] is None and s["start_ts"] is not None)
            or (s["end_ts"] is not None and s["end_ts"] >= cutoff_24h)
            or s["start_ts"] >= cutoff_24h
        ]
        if state.desk_session_start is not None and state.desk_session_id is not None:
            existing_ids = {s["id"] for s in timeline_24h}
            if state.desk_session_id not in existing_ids:
                timeline_24h.append({
                    "id": state.desk_session_id,
                    "start_ts": state.desk_session_start.isoformat(),
                    "end_ts": None,
                    "duration_seconds": None,
                })

        daily_totals: dict = defaultdict(int)
        for s in all_sessions:
            if s["duration_seconds"] is not None:
                date_key = s["start_ts"][:10]
                daily_totals[date_key] += s["duration_seconds"]

        if state.desk_session_start is not None and state.desk_session_start.date() == now.date():
            ongoing_sec = int((now - state.desk_session_start).total_seconds())
            daily_totals[now.date().isoformat()] += ongoing_sec

        today = now.date()
        daily_30d = []
        for i in range(29, -1, -1):
            d = today - timedelta(days=i)
            date_str = d.isoformat()
            daily_30d.append({"date": date_str, "total_seconds": daily_totals.get(date_str, 0)})

        return {"timeline_24h": timeline_24h, "daily_30d": daily_30d}

    @router.get("/api/desk/sessions")
    async def desk_sessions(limit: int = Query(20, ge=1, le=200)):
        from app.storage.logs import get_recent_sessions
        return {"sessions": await get_recent_sessions(limit)}

    return router
