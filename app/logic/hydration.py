from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class HydrationStatus:
    current_ml: int
    goal_ml: int
    pct: float | None
    event: str | None


def _parse_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return None


def _parse_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return f if math.isfinite(f) else None
    return None


def parse_status(payload: dict) -> HydrationStatus | None:
    current_ml = _parse_int(payload.get("current_ml"))
    goal_ml = _parse_int(payload.get("goal_ml"))
    if current_ml is None or goal_ml is None:
        return None
    # 上限 9999ml（~10 公升/日）：物理上不可能的數值一律視為無效 payload，
    # 同時保證 Water 卡片在最壞情況下的文字寬度仍落在版面可用空間內（見量測結果）。
    if not (0 <= current_ml <= 9999) or not (0 <= goal_ml <= 9999):
        return None

    pct = _parse_float(payload.get("pct"))
    # 拒絕不合理的極端值（例如 1e308）：雖然 isfinite，但 *100 後仍可能溢位成 inf，
    # 讓下游 int(round(pct*100)) 崩潰。合理範圍上限抓 -10.0~10.0（-1000%~1000%），
    # 已遠超過任何實際喝水進度會出現的比例。
    if pct is not None and not (-10.0 <= pct <= 10.0):
        pct = None
    if pct is None and goal_ml > 0:
        pct = current_ml / goal_ml
    elif goal_ml <= 0:
        pct = None

    raw_event = payload.get("event")
    event = raw_event if isinstance(raw_event, str) else None
    return HydrationStatus(
        current_ml=current_ml,
        goal_ml=goal_ml,
        pct=pct,
        event=event,
    )
