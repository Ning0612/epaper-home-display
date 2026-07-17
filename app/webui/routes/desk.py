from __future__ import annotations

from datetime import datetime, time, timedelta
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

    def _state_start_in_zone(zone):
        if state.desk_session_start is None:
            return None
        if state.desk_session_start.tzinfo is not None:
            return state.desk_session_start.astimezone(zone)
        return state.desk_session_start.replace(tzinfo=zone)

    def _append_state_session(sessions: list[dict], state_start, zone, legacy_timezone) -> None:
        if state_start is None:
            return
        if state.desk_session_id is not None and any(
            session.get("id") == state.desk_session_id for session in sessions
        ):
            return
        if any(
            session.get("end_ts") is None
            and _parse_in_zone(session.get("start_ts"), zone, legacy_timezone) == state_start
            for session in sessions
        ):
            return
        sessions.append({
            "id": state.desk_session_id,
            "start_ts": state_start.isoformat(),
            "end_ts": None,
            "duration_seconds": None,
        })

    def _clip_sessions_to_range(
        sessions: list[dict], range_start: datetime, range_end: datetime, zone, legacy_timezone
    ) -> list[dict]:
        clipped_sessions = []
        for session in sessions:
            start = _parse_in_zone(session.get("start_ts"), zone, legacy_timezone)
            if start is None:
                continue
            end_raw = session.get("end_ts")
            end = None if end_raw is None else _parse_in_zone(end_raw, zone, legacy_timezone)
            if end_raw is not None and end is None:
                continue
            effective_end = range_end if end is None else end
            if not instant_before(start, effective_end):
                continue
            if not instant_before(start, range_end) or not instant_after(effective_end, range_start):
                continue
            clipped_start = range_start if instant_before(start, range_start) else start
            clipped_end = range_end if instant_after(effective_end, range_end) else effective_end
            if not instant_before(clipped_start, clipped_end):
                continue
            clipped = dict(session)
            clipped["start_ts"] = clipped_start.isoformat()
            clipped["end_ts"] = None if end is None else clipped_end.isoformat()
            clipped_sessions.append(clipped)
        return clipped_sessions

    def _aggregate_sessions_in_range(
        sessions: list[dict], range_start: datetime, range_end: datetime, zone, legacy_timezone
    ) -> dict[str, dict]:
        clipped_sessions = _clip_sessions_to_range(sessions, range_start, range_end, zone, legacy_timezone)
        rows_by_date = {}
        for year in range(range_start.year, range_end.year + 1):
            for row in aggregate_sessions_by_day(
                clipped_sessions,
                year,
                now=range_end,
                timezone_name=settings.timezone,
                legacy_timezone=legacy_timezone,
            ):
                if range_start.date() <= datetime.fromisoformat(row["date"]).date() <= range_end.date():
                    rows_by_date[row["date"]] = row
        return rows_by_date

    @router.get("/desk", response_class=HTMLResponse)
    async def desk_page():
        return HTMLResponse(_DESK_HTML)

    @router.get("/api/desk/status")
    async def desk_status():
        from app.storage.logs import get_sessions_overlapping
        now, zone = _desk_clock()
        today_start = datetime.combine(now.date(), time.min, tzinfo=zone)
        today_sessions = await get_sessions_overlapping(
            today_start,
            now,
            timezone_name=settings.timezone,
            legacy_timezone=system_local_timezone(),
        )
        legacy_timezone = system_local_timezone()
        state_start = _state_start_in_zone(zone)
        _append_state_session(today_sessions, state_start, zone, legacy_timezone)
        today_row = _aggregate_sessions_in_range(today_sessions, today_start, now, zone, legacy_timezone).get(
            now.date().isoformat(),
            {"total_seconds": 0, "session_count": 0},
        )

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
                parsed_end = _parse_in_zone(session["end_ts"], zone, legacy_timezone)
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
            "today_total_seconds": today_row["total_seconds"],
            "today_session_count": today_row["session_count"],
            "current_segment_seconds": current_segment_sec,
            "session_start_ts": state_start.isoformat() if state_start else None,
            "last_change_ts": last_change_ts,
            "now_epoch": int(now.timestamp()),
            "current_date": now.date().isoformat(),
            "timezone": settings.timezone,
        }

    async def _desk_history_data(history_days: int = 366) -> dict:
        from app.storage.logs import get_sessions_overlapping
        now, zone = _desk_clock()
        legacy_timezone = system_local_timezone()
        history_start = datetime.combine(
            now.date() - timedelta(days=history_days - 1),
            time.min,
            tzinfo=zone,
        )
        all_sessions = await get_sessions_overlapping(
            history_start,
            now,
            timezone_name=settings.timezone,
            legacy_timezone=legacy_timezone,
        )

        state_start = _state_start_in_zone(zone)
        _append_state_session(all_sessions, state_start, zone, legacy_timezone)
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
        daily_rows = _aggregate_sessions_in_range(all_sessions, history_start, now, zone, legacy_timezone)

        today = now.date()
        daily_history = []
        for i in range(history_days - 1, -1, -1):
            d = today - timedelta(days=i)
            date_str = d.isoformat()
            daily_history.append({
                "date": date_str,
                "total_seconds": daily_rows.get(date_str, {}).get("total_seconds", 0),
                "session_count": daily_rows.get(date_str, {}).get("session_count", 0),
            })

        return {
            "timeline_24h": timeline_24h,
            "daily_30d": daily_history[-30:],
            "daily_history": daily_history,
        }

    @router.get("/api/desk/timeline")
    async def desk_timeline():
        data = await _desk_history_data()
        return {"timeline_24h": data["timeline_24h"]}

    @router.get("/api/desk/daily")
    async def desk_daily():
        data = await _desk_history_data()
        return {
            "daily_30d": data["daily_30d"],
            "daily_history": data["daily_history"],
        }

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
        state_start = _state_start_in_zone(zone)
        if state_start is not None and instant_before(state_start, year_end):
            _append_state_session(sessions, state_start, zone, legacy_timezone)
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
