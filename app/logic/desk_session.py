from __future__ import annotations

from datetime import datetime


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


def compute_day_stats(sessions: list[dict]) -> dict:
    """Aggregate stats from completed desk sessions.

    Returns total_seconds, count, longest_seconds, desk_ratio (fraction of 24h).
    """
    completed = [s for s in sessions if s.get("duration_seconds") is not None]
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
