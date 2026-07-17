import asyncio
import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from app.loops import display as display_loop
from app.loops import presence as presence_loop
from app.state import AgentState


class _RecordingEpaper:
    def __init__(self) -> None:
        self.display_count = 0
        self.clear_count = 0

    def display(self, image, full_refresh: bool = False) -> None:
        self.display_count += 1

    def clear(self) -> None:
        self.clear_count += 1


async def _wait_until(predicate, task: asyncio.Task) -> None:
    for _ in range(100):
        if predicate():
            return
        if task.done():
            task.result()
        await asyncio.sleep(0.01)
    raise AssertionError("timed out waiting for display loop")


async def _stop_after_iteration(_seconds: float) -> None:
    raise _StopPresenceLoop


class _StopPresenceLoop(BaseException):
    pass


@pytest.mark.asyncio
async def test_startup_renders_dashboard_while_unoccupied(monkeypatch, settings):
    test_state = AgentState(presence="UNOCCUPIED")
    monkeypatch.setattr(display_loop, "state", test_state)

    async def startup_data_ready() -> None:
        return None

    monkeypatch.setattr(display_loop, "_wait_for_startup_data", startup_data_ready)
    monkeypatch.setattr(display_loop, "render_dashboard", lambda *_args: object())

    epaper = _RecordingEpaper()
    display_queue: asyncio.Queue[str] = asyncio.Queue()
    executor = ThreadPoolExecutor(max_workers=1)
    task = asyncio.create_task(display_loop._display_loop(epaper, executor, display_queue, settings))
    try:
        await _wait_until(lambda: epaper.display_count == 1, task)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        executor.shutdown(wait=True)

    assert epaper.clear_count == 0


@pytest.mark.asyncio
async def test_away_clears_once_and_wifi_connected_can_render(monkeypatch, settings):
    test_state = AgentState(presence="OCCUPIED")
    monkeypatch.setattr(display_loop, "state", test_state)

    async def startup_data_ready() -> None:
        return None

    monkeypatch.setattr(display_loop, "_wait_for_startup_data", startup_data_ready)
    monkeypatch.setattr(display_loop, "render_dashboard", lambda *_args: object())

    epaper = _RecordingEpaper()
    display_queue: asyncio.Queue[str] = asyncio.Queue()
    executor = ThreadPoolExecutor(max_workers=1)
    task = asyncio.create_task(display_loop._display_loop(epaper, executor, display_queue, settings))
    try:
        await _wait_until(lambda: epaper.display_count == 1, task)

        test_state.presence = "UNOCCUPIED"
        display_queue.put_nowait("presence_away")
        await _wait_until(lambda: epaper.clear_count == 1, task)
        await asyncio.sleep(0.05)
        assert epaper.display_count == 1
        assert epaper.clear_count == 1

        display_queue.put_nowait("wifi_connected")
        await _wait_until(lambda: epaper.display_count == 2, task)
        await asyncio.sleep(0.05)
        assert epaper.clear_count == 1
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        executor.shutdown(wait=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_presence", ["OCCUPIED", "UNKNOWN"])
async def test_presence_away_transition_wakes_display_queue(monkeypatch, settings, initial_presence):
    now = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
    test_state = AgentState(
        presence=initial_presence,
        light_raw=600,
        light_is_bright=True,
        light_state_since=now - timedelta(seconds=settings.sensors.light.unoccupied_after_seconds),
    )
    monkeypatch.setattr(presence_loop, "state", test_state)
    monkeypatch.setattr(presence_loop, "configured_now", lambda _timezone: now)

    async def log_presence_stub(*_args) -> None:
        return None

    monkeypatch.setattr(presence_loop, "log_presence", log_presence_stub)
    monkeypatch.setattr(presence_loop.asyncio, "sleep", _stop_after_iteration)

    display_queue: asyncio.Queue[str] = asyncio.Queue()
    with pytest.raises(_StopPresenceLoop):
        await presence_loop._presence_loop(display_queue, object(), settings)

    assert test_state.presence == "UNOCCUPIED"
    assert display_queue.get_nowait() == "presence_away"
