from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.state import state
from app.webui.routes.desk import create_desk_router
from app.webui.templates.desk import _DESK_HTML


def test_desk_routes_follow_unified_api_paths():
    paths = {route.path for route in create_desk_router(Settings()).routes}

    assert {
        "/desk",
        "/api/desk/status",
        "/api/desk/timeline",
        "/api/desk/daily",
        "/api/desk/heatmap",
        "/api/desk/sessions",
    } <= paths
    assert "/api/desk/stats" not in paths
    assert "/api/desk/history" not in paths


def test_desk_template_uses_unified_analysis_terms_and_footer_timestamp():
    for term in ("年度書桌前熱力圖", "目前時段", "今日切換次數", "光線數值", "最後更新："):
        assert term in _DESK_HTML
    assert "不在" not in _DESK_HTML
    assert "年度在席熱力圖" not in _DESK_HTML
    assert _DESK_HTML.count('id="s-light"') == 1
    assert _DESK_HTML.count('id="s-thresh"') == 1
    assert "fetch('/api/desk/status')" in _DESK_HTML
    assert "fetch('/api/desk/timeline')" in _DESK_HTML
    assert "fetch('/api/desk/daily')" in _DESK_HTML


def _desk_endpoint(router, path):
    return next(route.endpoint for route in router.routes if route.path == path)


@pytest.mark.asyncio
async def test_desk_split_endpoints_keep_explicit_response_shapes(monkeypatch):
    async def fake_get_sessions_for_date(*args, **kwargs):
        return []

    async def fake_get_sessions_last_n_days(*args, **kwargs):
        return []

    async def fake_get_recent_sessions(limit=20):
        assert limit == 20
        return [{"id": 1, "start_ts": "2026-07-14T09:00:00+08:00", "end_ts": None}]

    monkeypatch.setattr("app.storage.logs.get_sessions_for_date", fake_get_sessions_for_date)
    monkeypatch.setattr("app.storage.logs.get_sessions_last_n_days", fake_get_sessions_last_n_days)
    monkeypatch.setattr("app.storage.logs.get_recent_sessions", fake_get_recent_sessions)
    monkeypatch.setattr(state, "presence", "UNOCCUPIED")
    monkeypatch.setattr(state, "light_raw", 640)
    monkeypatch.setattr(state, "desk_session_start", None)

    router = create_desk_router(Settings())
    status = await _desk_endpoint(router, "/api/desk/status")()
    timeline = await _desk_endpoint(router, "/api/desk/timeline")()
    daily = await _desk_endpoint(router, "/api/desk/daily")()
    sessions = await _desk_endpoint(router, "/api/desk/sessions")(limit=20)

    assert status["light_raw"] == 640
    assert "today_total_seconds" in status
    assert list(timeline) == ["timeline_24h"]
    assert len(daily["daily_30d"]) == 30
    assert sessions["sessions"][0]["id"] == 1


@pytest.mark.asyncio
async def test_desk_heatmap_endpoint_returns_year_and_reference(monkeypatch):
    sessions = [
        {
            "id": 1,
            "start_ts": "2024-12-31T23:00:00+08:00",
            "end_ts": "2025-01-01T02:30:00+08:00",
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
