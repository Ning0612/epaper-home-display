from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from app.logic.desk_session import DESK_HEATMAP_REFERENCE_SECONDS, aggregate_sessions_by_day
from app.state import state
from app.timezone import (
    configured_now,
    configured_zone,
    elapsed_seconds,
    instant_after,
    instant_before,
    system_local_timezone,
)
from app.webui.templates.desk import _DESK_HTML

if TYPE_CHECKING:
    from app.config import Settings


def create_desk_router(settings: "Settings") -> APIRouter:
    router = APIRouter()

    def _desk_clock():
        try:
            zone = configured_zone(settings.timezone)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="設定的時區無效") from exc
        return configured_now(settings.timezone), zone

    def _parse_in_zone(value: object, zone, legacy_timezone=None):
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=legacy_timezone or zone)
        return parsed.astimezone(zone)

    def _session_overlaps(session: dict, range_start: datetime, range_end: datetime, zone, legacy_timezone) -> bool:
        start = _parse_in_zone(session.get("start_ts"), zone, legacy_timezone)
        if start is None:
            return False
        end_raw = session.get("end_ts")
        end = None if end_raw is None else _parse_in_zone(end_raw, zone, legacy_timezone)
        if end_raw is not None and end is None:
            return False
        if end is not None and not instant_before(start, end):
            return False
        return instant_before(start, range_end) and (end is None or instant_after(end, range_start))

    @router.get("/desk", response_class=HTMLResponse)
    async def desk_page():
        return HTMLResponse(_DESK_HTML)

    @router.get("/api/desk/stats")
    async def desk_stats():
        from app.storage.logs import get_sessions_for_date
        now, zone = _desk_clock()
        today_sessions = await get_sessions_for_date(
            now.date(),
            timezone_name=settings.timezone,
            legacy_timezone=system_local_timezone(),
        )
        state_start = (
            state.desk_session_start.astimezone(zone)
            if state.desk_session_start is not None and state.desk_session_start.tzinfo is not None
            else state.desk_session_start.replace(tzinfo=zone) if state.desk_session_start is not None else None
        )

        today_completed_sec = sum(
            s["duration_seconds"] for s in today_sessions
            if s["duration_seconds"] is not None
        )
        ongoing_sec = 0
        if state_start is not None and state_start.date() == now.date():
            ongoing_sec = elapsed_seconds(state_start, now)

        today_count = len([s for s in today_sessions if s["duration_seconds"] is not None])
        if state_start is not None and state_start.date() == now.date():
            today_count += 1

        current_segment_sec = 0
        last_change_ts = None
        if state.presence == "OCCUPIED" and state_start:
            current_segment_sec = elapsed_seconds(state_start, now)
            last_change_ts = state_start.isoformat()
        elif state.presence == "UNOCCUPIED":
            completed = []
            for session in today_sessions:
                if session["end_ts"] is None:
                    continue
                parsed_end = _parse_in_zone(session["end_ts"], zone)
                if parsed_end is not None:
                    completed.append((parsed_end, session["end_ts"]))
            if completed:
                last_end_dt, last_end = max(completed, key=lambda item: item[0].timestamp())
                try:
                    current_segment_sec = elapsed_seconds(last_end_dt, now)
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
            "session_start_ts": state_start.isoformat() if state_start else None,
            "last_change_ts": last_change_ts,
        }

    @router.get("/api/desk/history")
    async def desk_history():
        from app.storage.logs import get_sessions_last_n_days
        now, zone = _desk_clock()
        legacy_timezone = system_local_timezone()
        all_sessions = await get_sessions_last_n_days(
            30,
            now=now,
            timezone_name=settings.timezone,
            legacy_timezone=legacy_timezone,
        )

        cutoff_24h = now - timedelta(hours=24)
        timeline_24h = [
            s for s in all_sessions
            if (
                (start := _parse_in_zone(s.get("start_ts"), zone, legacy_timezone)) is not None
                and instant_before(start, now)
                and (
                    s.get("end_ts") is None
                    or (
                        (end := _parse_in_zone(s.get("end_ts"), zone, legacy_timezone)) is not None
                        and not instant_before(end, cutoff_24h)
                    )
                )
            )
        ]
        state_start = (
            state.desk_session_start.astimezone(zone)
            if state.desk_session_start is not None and state.desk_session_start.tzinfo is not None
            else state.desk_session_start.replace(tzinfo=zone) if state.desk_session_start is not None else None
        )
        if state_start is not None and state.desk_session_id is not None:
            existing_ids = {s["id"] for s in timeline_24h}
            if state.desk_session_id not in existing_ids:
                timeline_24h.append({
                    "id": state.desk_session_id,
                    "start_ts": state_start.isoformat(),
                    "end_ts": None,
                    "duration_seconds": None,
                })

        daily_totals: dict = defaultdict(int)
        for s in all_sessions:
            if s["duration_seconds"] is not None:
                start = _parse_in_zone(s.get("start_ts"), zone, legacy_timezone)
                if start is not None:
                    daily_totals[start.date().isoformat()] += s["duration_seconds"]

        if state_start is not None and state_start.date() == now.date():
            ongoing_sec = elapsed_seconds(state_start, now)
            daily_totals[now.date().isoformat()] += ongoing_sec

        today = now.date()
        daily_30d = []
        for i in range(29, -1, -1):
            d = today - timedelta(days=i)
            date_str = d.isoformat()
            daily_30d.append({"date": date_str, "total_seconds": daily_totals.get(date_str, 0)})

        return {"timeline_24h": timeline_24h, "daily_30d": daily_30d}

    @router.get("/api/desk/heatmap")
    async def desk_heatmap(year: int | None = Query(default=None, ge=2000, le=2100)):
        from app.storage.logs import get_sessions_overlapping

        now, zone = _desk_clock()
        target_year = year or now.year
        if target_year > now.year:
            raise HTTPException(status_code=400, detail="不可查詢未來年份")

        year_start = datetime(target_year, 1, 1, tzinfo=zone)
        year_end = datetime(target_year + 1, 1, 1, tzinfo=zone)
        legacy_timezone = system_local_timezone()
        sessions = await get_sessions_overlapping(
            year_start,
            year_end,
            timezone_name=settings.timezone,
            legacy_timezone=legacy_timezone,
        )
        sessions = [
            session for session in sessions
            if _session_overlaps(session, year_start, year_end, zone, legacy_timezone)
        ]
        state_start = (
            state.desk_session_start.astimezone(zone)
            if state.desk_session_start is not None and state.desk_session_start.tzinfo is not None
            else state.desk_session_start.replace(tzinfo=zone) if state.desk_session_start is not None else None
        )
        if state_start is not None and instant_before(state_start, year_end):
            existing_ids = {session.get("id") for session in sessions}
            current_start_ts = state_start.isoformat()
            has_current_session = state.desk_session_id in existing_ids
            if not has_current_session:
                has_current_session = any(
                    session.get("end_ts") is None
                    and _parse_in_zone(session.get("start_ts"), zone, legacy_timezone) == state_start
                    for session in sessions
                )
            if not has_current_session:
                sessions.append(
                    {
                        "id": state.desk_session_id,
                        "start_ts": current_start_ts,
                        "end_ts": None,
                        "duration_seconds": None,
                    }
                )
        days = aggregate_sessions_by_day(
            sessions,
            target_year,
            now=now,
            timezone_name=settings.timezone,
            legacy_timezone=legacy_timezone,
        )
        total_seconds = sum(day["total_seconds"] for day in days)
        return {
            "year": target_year,
            "timezone": settings.timezone,
            "as_of": now.isoformat(),
            "days": days,
            "total_seconds": total_seconds,
            "active_days": sum(day["total_seconds"] > 0 for day in days),
            "reference_seconds": DESK_HEATMAP_REFERENCE_SECONDS,
            "summary": {
                "total_seconds": total_seconds,
                "active_days": sum(day["total_seconds"] > 0 for day in days),
                "session_count": len(sessions),
                "has_ongoing": any(session.get("end_ts") is None for session in sessions),
            },
        }

    @router.get("/api/desk/sessions")
    async def desk_sessions(limit: int = Query(20, ge=1, le=200)):
        from app.storage.logs import get_recent_sessions
        return {"sessions": await get_recent_sessions(limit)}

    return router
