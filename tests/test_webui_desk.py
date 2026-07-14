from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.state import state
from app.webui.routes.desk import create_desk_router


@pytest.mark.asyncio
async def test_desk_heatmap_endpoint_returns_year_and_reference(monkeypatch):
    sessions = [
        {
            "id": 1,
            "start_ts": "2024-12-31T23:00:00",
            "end_ts": "2025-01-01T02:30:00",
            "duration_seconds": 12600,
        }
    ]

    async def fake_get_sessions_overlapping(start_ts, end_ts, **kwargs):
        assert start_ts.isoformat() == "2025-01-01T00:00:00+08:00"
        assert end_ts.isoformat() == "2026-01-01T00:00:00+08:00"
        return sessions

    monkeypatch.setattr("app.storage.logs.get_sessions_overlapping", fake_get_sessions_overlapping)
    router = create_desk_router(Settings())
    endpoint = next(route.endpoint for route in router.routes if route.path == "/api/desk/heatmap")

    payload = await endpoint(year=2025)

    assert payload["year"] == 2025
    assert payload["timezone"] == "Asia/Taipei"
    assert payload["reference_seconds"] == 8 * 60 * 60
    assert payload["active_days"] == 1
    assert payload["total_seconds"] == 9000
    assert payload["days"][0]["total_seconds"] == 9000
    assert payload["summary"]["session_count"] == 1


@pytest.mark.asyncio
async def test_desk_heatmap_endpoint_rejects_future_year():
    router = create_desk_router(Settings())
    endpoint = next(route.endpoint for route in router.routes if route.path == "/api/desk/heatmap")

    with pytest.raises(HTTPException, match="不可查詢未來年份"):
        await endpoint(year=datetime.now().year + 1)


@pytest.mark.asyncio
async def test_desk_heatmap_endpoint_includes_in_memory_ongoing_session(monkeypatch):
    async def fake_get_sessions_overlapping(start_ts, end_ts, **kwargs):
        return []

    monkeypatch.setattr("app.storage.logs.get_sessions_overlapping", fake_get_sessions_overlapping)
    monkeypatch.setattr(state, "desk_session_id", 9001)
    monkeypatch.setattr(state, "desk_session_start", datetime.now() - timedelta(minutes=15))
    router = create_desk_router(Settings())
    endpoint = next(route.endpoint for route in router.routes if route.path == "/api/desk/heatmap")

    payload = await endpoint(year=datetime.now().year)

    assert payload["summary"]["session_count"] == 1
    assert payload["summary"]["has_ongoing"] is True
    assert any(day["status"] == "ongoing" for day in payload["days"])


@pytest.mark.asyncio
async def test_desk_heatmap_endpoint_does_not_include_current_session_in_history(monkeypatch):
    async def fake_get_sessions_overlapping(start_ts, end_ts, **kwargs):
        return []

    monkeypatch.setattr("app.storage.logs.get_sessions_overlapping", fake_get_sessions_overlapping)
    monkeypatch.setattr(state, "desk_session_id", 9002)
    monkeypatch.setattr(state, "desk_session_start", datetime.now() - timedelta(minutes=15))
    router = create_desk_router(Settings())
    endpoint = next(route.endpoint for route in router.routes if route.path == "/api/desk/heatmap")

    payload = await endpoint(year=datetime.now().year - 1)

    assert payload["summary"]["session_count"] == 0
    assert payload["summary"]["has_ongoing"] is False


@pytest.mark.asyncio
async def test_desk_heatmap_endpoint_rejects_invalid_timezone():
    router = create_desk_router(Settings(timezone="Not/AZone"))
    endpoint = next(route.endpoint for route in router.routes if route.path == "/api/desk/heatmap")

    with pytest.raises(HTTPException, match="設定的時區無效"):
        await endpoint(year=2025)


@pytest.mark.asyncio
async def test_desk_heatmap_endpoint_excludes_reverse_intervals(monkeypatch):
    async def fake_get_sessions_overlapping(start_ts, end_ts, **kwargs):
        return [{
            "id": 5,
            "start_ts": "2025-06-02T11:00:00+08:00",
            "end_ts": "2025-06-02T10:00:00+08:00",
            "duration_seconds": 3600,
        }]

    monkeypatch.setattr("app.storage.logs.get_sessions_overlapping", fake_get_sessions_overlapping)
    router = create_desk_router(Settings())
    endpoint = next(route.endpoint for route in router.routes if route.path == "/api/desk/heatmap")

    payload = await endpoint(year=2025)

    assert payload["summary"]["session_count"] == 0
    assert payload["total_seconds"] == 0
