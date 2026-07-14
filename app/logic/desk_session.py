from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.timezone import elapsed_seconds, instant_after, instant_before, instant_before_or_equal, instant_max, instant_min


_EMBED_COLORS = {
    "low": 15158332,
    "medium": 15132194,
    "high": 3447003,
    "complete": 3066993,
}

DESK_HEATMAP_REFERENCE_SECONDS = 8 * 60 * 60


def format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration: '3h 20m', '45m', '0m'."""
    if seconds <= 0:
        return "0m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours == 0:
        return f"{minutes}m"
    if minutes == 0:
        return f"{hours}h"
    return f"{hours}h {minutes}m"


def format_bar(desk_sec: int, total_sec: int, width: int = 15) -> str:
    """Render progress bar: absence (░) on left, desk time (█) on right."""
    if total_sec <= 0:
        return "░" * width
    desk_ratio = desk_sec / total_sec
    desk_chars = round(desk_ratio * width)
    desk_chars = max(0, min(width, desk_chars))
    absence_chars = width - desk_chars
    return "░" * absence_chars + "█" * desk_chars


def _resolve_zone(timezone_name: str | None):
    if not timezone_name:
        return None
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _parse_session_datetime(value: object, zone=None, naive_zone=None) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None and (naive_zone is not None or zone is not None):
        parsed = parsed.replace(tzinfo=naive_zone or zone)
    if parsed.tzinfo is not None and zone is not None:
        parsed = parsed.astimezone(zone)
    elif parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _seconds_between(start: datetime, end: datetime) -> int:
    return elapsed_seconds(start, end)


def aggregate_sessions_by_day(
    sessions: list[dict],
    year: int,
    now: datetime | None = None,
    timezone_name: str | None = None,
    legacy_timezone: tzinfo | None = None,
) -> list[dict]:
    """Split, merge, and aggregate desk sessions across local midnights.

    New records carry an ISO-8601 offset. Legacy records without one are
    interpreted in ``legacy_timezone`` when supplied, then bucketed in the
    configured ``timezone_name``.
    """
    zone = _resolve_zone(timezone_name)
    naive_zone = legacy_timezone or zone
    year_start = datetime(year, 1, 1, tzinfo=zone)
    year_end = datetime(year + 1, 1, 1, tzinfo=zone)
    effective_now = now or datetime.now(tz=zone)
    if effective_now.tzinfo is None and zone is not None:
        effective_now = effective_now.replace(tzinfo=zone)
    elif effective_now.tzinfo is not None and zone is not None:
        effective_now = effective_now.astimezone(zone)
    elif effective_now.tzinfo is not None:
        effective_now = effective_now.astimezone().replace(tzinfo=None)
    totals: dict[date, int] = {}
    session_counts: dict[date, int] = {}
    ongoing_days: set[date] = set()
    intervals: list[tuple[datetime, datetime]] = []

    for session in sessions:
        start = _parse_session_datetime(session.get("start_ts"), zone, naive_zone)
        if start is None:
            continue
        end_raw = session.get("end_ts")
        if end_raw is None:
            ongoing = True
            end = effective_now
        else:
            end = _parse_session_datetime(end_raw, zone, naive_zone)
            if end is None:
                continue
            ongoing = False
        if instant_before_or_equal(end, start):
            continue

        clipped_start = instant_max(start, year_start)
        clipped_end = instant_min(end, year_end)
        if not instant_before(clipped_start, clipped_end):
            continue
        intervals.append((clipped_start, clipped_end))

        cursor = clipped_start
        while instant_before(cursor, clipped_end):
            next_day = datetime.combine(cursor.date() + timedelta(days=1), time.min, tzinfo=zone)
            overlap_end = instant_min(clipped_end, next_day)
            if _seconds_between(cursor, overlap_end) > 0:
                session_counts[cursor.date()] = session_counts.get(cursor.date(), 0) + 1
                if ongoing:
                    ongoing_days.add(cursor.date())
            cursor = next_day

    intervals.sort(key=lambda interval: interval[0].astimezone(timezone.utc) if interval[0].tzinfo else interval[0])
    merged: list[tuple[datetime, datetime]] = []
    for start, end in intervals:
        if not merged or instant_after(start, merged[-1][1]):
            merged.append((start, end))
        elif instant_after(end, merged[-1][1]):
            merged[-1] = (merged[-1][0], end)

    for interval_start, interval_end in merged:
        cursor = interval_start
        while instant_before(cursor, interval_end):
            next_day = datetime.combine(cursor.date() + timedelta(days=1), time.min, tzinfo=zone)
            overlap_end = instant_min(interval_end, next_day)
            seconds = _seconds_between(cursor, overlap_end)
            if seconds > 0:
                totals[cursor.date()] = totals.get(cursor.date(), 0) + seconds
            cursor = next_day

    days = (year_end - year_start).days
    now_date = effective_now.date()
    result = []
    for index in range(days):
        current_date = (year_start + timedelta(days=index)).date()
        total_seconds = totals.get(current_date, 0)
        if current_date > now_date:
            status = "future"
        elif current_date == now_date and current_date in ongoing_days:
            status = "ongoing"
        elif total_seconds > 0:
            status = "recorded"
        else:
            status = "empty"
        result.append(
            {
                "date": current_date.isoformat(),
                "total_seconds": total_seconds,
                "session_count": session_counts.get(current_date, 0),
                "status": status,
            }
        )
    return result


def compute_day_stats(sessions: list[dict]) -> dict:
    """Aggregate stats from completed desk sessions.

    Returns total_seconds, count, longest_seconds, desk_ratio (fraction of 24h).
    """
    completed = [
        s for s in sessions
        if isinstance(s.get("duration_seconds"), int) and s["duration_seconds"] >= 0
    ]
    if not completed:
        return {"total_seconds": 0, "count": 0, "longest_seconds": 0, "desk_ratio": 0.0}
    total_seconds = sum(s["duration_seconds"] for s in completed)
    longest_seconds = max(s["duration_seconds"] for s in completed)
    return {
        "total_seconds": total_seconds,
        "count": len(completed),
        "longest_seconds": longest_seconds,
        "desk_ratio": total_seconds / 86400,
    }


def format_session_end_msg(session: dict) -> str:
    """Format single session-end Discord notification."""
    start_dt = datetime.fromisoformat(session["start_ts"])
    end_dt = datetime.fromisoformat(session["end_ts"])
    duration = format_duration(session["duration_seconds"])
    return (
        f"📖 書桌前時段結束\n"
        f"{start_dt.strftime('%H:%M')} → {end_dt.strftime('%H:%M')}（{duration}）"
    )


def format_daily_summary(date_str: str, sessions: list[dict]) -> str:
    """Format daily summary in Discord notification format.

    Example output:
        2026-05-30
        離開 62% [░░░░░░░░░██████] 書桌前 38%
        書桌前 9h 10m / 最長一次 3h 20m / 次數 5
    """
    stats = compute_day_stats(sessions)
    total_sec = stats["total_seconds"]
    count = stats["count"]
    longest_sec = stats["longest_seconds"]

    desk_pct = round(total_sec / 86400 * 100)
    absence_pct = 100 - desk_pct
    bar = format_bar(total_sec, 86400)
    total_str = format_duration(total_sec)
    longest_str = format_duration(longest_sec)

    return (
        f"{date_str}\n"
        f"離開 {absence_pct}% [{bar}] 書桌前 {desk_pct}%\n"
        f"書桌前 {total_str} / 最長一次 {longest_str} / 次數 {count}"
    )


def format_daily_summary_embed(date_str: str, sessions: list[dict]) -> dict:
    """Build the L2 Discord embed used for daily desk-presence reports."""
    stats = compute_day_stats(sessions)
    total_sec = stats["total_seconds"]
    count = stats["count"]
    desk_pct = max(0, min(999, int(total_sec / 86400 * 100)))
    filled = min(10, desk_pct // 10)
    if desk_pct < 50:
        level, block = "low", "🟥"
    elif desk_pct < 80:
        level, block = "medium", "🟨"
    elif desk_pct < 100:
        level, block = "high", "🟦"
    else:
        level, block = "complete", "🟩"
    progress = block * filled + "⬜" * (10 - filled)
    total_str = format_duration(total_sec)
    longest_str = format_duration(stats["longest_seconds"])
    conclusion = f"書桌前 {total_str}，共 {count} 次"
    return {
        "embeds": [
            {
                "title": f"📊 在席日報 · {date_str}",
                "description": f"{progress}  {desk_pct}%\n{conclusion}",
                "fields": [
                    {"name": "書桌前", "value": total_str, "inline": True},
                    {"name": "最長一次", "value": longest_str, "inline": True},
                    {"name": "次數", "value": str(count), "inline": True},
                ],
                "color": _EMBED_COLORS[level],
            }
        ]
    }
