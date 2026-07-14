from __future__ import annotations

import os
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def configured_zone(timezone_name: str) -> ZoneInfo:
    """Return a configured IANA zone or raise a useful configuration error."""
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid IANA timezone: {timezone_name!r}") from exc


def configured_now(timezone_name: str) -> datetime:
    """Return an aware timestamp in the configured IANA zone."""
    return datetime.now(tz=configured_zone(timezone_name))


def utc_instant(value: datetime) -> datetime:
    """Normalize an aware datetime for unambiguous instant comparisons."""
    return value.astimezone(timezone.utc) if value.tzinfo is not None else value


def elapsed_seconds(start: datetime, end: datetime) -> int:
    """Return elapsed seconds, respecting DST folds for aware datetimes."""
    return int((utc_instant(end) - utc_instant(start)).total_seconds())


def instant_before(left: datetime, right: datetime) -> bool:
    return utc_instant(left) < utc_instant(right)


def instant_before_or_equal(left: datetime, right: datetime) -> bool:
    return utc_instant(left) <= utc_instant(right)


def instant_after(left: datetime, right: datetime) -> bool:
    return utc_instant(left) > utc_instant(right)


def instant_min(left: datetime, right: datetime) -> datetime:
    return left if instant_before_or_equal(left, right) else right


def instant_max(left: datetime, right: datetime) -> datetime:
    return left if instant_after(left, right) else right


def system_local_timezone() -> tzinfo:
    """Best-effort local zone detection for legacy naive timestamps.

    Desk sessions written before timezone-aware timestamps were introduced have
    no offset metadata. On Raspberry Pi, /etc/localtime normally points into
    the IANA zoneinfo tree, which lets us recover the original wall-clock zone.
    Windows falls back to its current fixed offset; this is sufficient for the
    test/dev environment and keeps the helper dependency-free.
    """
    env_name = os.environ.get("TZ", "").strip().lstrip(":")
    if env_name:
        try:
            return ZoneInfo(env_name)
        except (ZoneInfoNotFoundError, ValueError):
            pass

    if os.name != "nt":
        for candidate in (Path("/etc/localtime"), Path("/etc/timezone")):
            try:
                raw = candidate.read_text(encoding="utf-8").strip() if candidate.name == "timezone" else ""
                resolved = raw or str(candidate.resolve())
                if raw:
                    try:
                        return ZoneInfo(raw)
                    except (ZoneInfoNotFoundError, ValueError):
                        pass
                marker = "/zoneinfo/"
                if marker in resolved:
                    return ZoneInfo(resolved.split(marker, 1)[1])
            except (OSError, ValueError, ZoneInfoNotFoundError):
                continue

    return datetime.now().astimezone().tzinfo or timezone.utc
