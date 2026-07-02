from __future__ import annotations

import math
import re
from dataclasses import dataclass


_GCODE_STATE_RE = re.compile(r"^[A-Za-z_]{1,32}$")
_MAX_REMAINING_MIN = 10080
_MAX_TASK_NAME_LEN = 100


@dataclass(frozen=True)
class PrintStatus:
    pct: float | None
    remaining_min: int | None
    task_name: str | None
    gcode_state: str | None


def _parse_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return f if math.isfinite(f) else None
    return None


def _parse_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return None


def _parse_percent(value: object) -> float | None:
    pct = _parse_float(value)
    if pct is None or not (0.0 <= pct <= 100.0):
        return None
    normalized = pct / 100.0
    if not math.isfinite(normalized) or not (0.0 <= normalized <= 1.0):
        return None
    return normalized


def _parse_remaining_min(value: object) -> int | None:
    minutes = _parse_int(value)
    if minutes is None or not (0 <= minutes <= _MAX_REMAINING_MIN):
        return None
    return minutes


def _parse_task_name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > _MAX_TASK_NAME_LEN:
        return None
    return text


def _parse_gcode_state(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().upper()
    if not _GCODE_STATE_RE.fullmatch(text):
        return None
    return text


def parse_print_status(print_obj: dict) -> PrintStatus | None:
    """Parse a Bambu `print` report object with per-field incremental semantics."""
    if not isinstance(print_obj, dict):
        return None

    task_name = _parse_task_name(print_obj.get("subtask_name"))
    if task_name is None:
        task_name = _parse_task_name(print_obj.get("gcode_file"))

    return PrintStatus(
        pct=_parse_percent(print_obj.get("mc_percent")),
        remaining_min=_parse_remaining_min(print_obj.get("mc_remaining_time")),
        task_name=task_name,
        gcode_state=_parse_gcode_state(print_obj.get("gcode_state")),
    )


def format_remaining(minutes: int | None) -> str:
    if minutes is None or minutes < 0:
        return "--"
    hours, mins = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h{mins:02d}m"
    return f"{mins}m"
