from __future__ import annotations

import json
from datetime import datetime


def _now() -> str:
    return datetime.now().isoformat()


def _to_iso(dt: datetime) -> str:
    return dt.isoformat()


def _safe_json_loads(raw: str) -> dict:
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}
