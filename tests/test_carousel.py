from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.loops.display import _maybe_advance_carousel
from app.state import state


@pytest.fixture(autouse=True)
def reset_carousel_state():
    state.image_playlist = []
    state.carousel_index = 0
    state.custom_image_path = None
    state.carousel_refresh_count = 0
    state.carousel_skip_next_advance = False
    yield
    state.image_playlist = []
    state.carousel_index = 0
    state.custom_image_path = None
    state.carousel_refresh_count = 0
    state.carousel_skip_next_advance = False


def _make_settings(enabled=True, interval=1, mode="sequential"):
    s = MagicMock()
    s.images.carousel_enabled = enabled
    s.images.carousel_interval_refreshes = interval
    s.images.carousel_mode = mode
    return s


class TestMaybeAdvanceCarousel:
    def test_no_op_when_disabled(self):
        state.image_playlist = ["a.png", "b.png"]
        state.custom_image_path = "a.png"
        _maybe_advance_carousel(_make_settings(enabled=False))
        assert state.custom_image_path == "a.png"

    def test_no_op_with_single_image(self):
        state.image_playlist = ["a.png"]
        state.custom_image_path = "a.png"
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "a.png"

    def test_no_op_before_interval_count_reached(self):
        state.image_playlist = ["a.png", "b.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        state.carousel_refresh_count = 0
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings(interval=5))
        # count is now 1, threshold is 5 — should not advance
        assert state.custom_image_path == "a.png"
        assert state.carousel_refresh_count == 1

    def test_advances_when_count_reaches_interval(self):
        state.image_playlist = ["a.png", "b.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        state.carousel_refresh_count = 4  # next call will reach threshold=5
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings(interval=5))
        assert state.custom_image_path == "b.png"
        assert state.carousel_refresh_count == 0

    def test_counter_resets_after_advance(self):
        state.image_playlist = ["a.png", "b.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        state.carousel_refresh_count = 0
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings(interval=1))
        assert state.carousel_refresh_count == 0

    def test_sequential_advance(self):
        state.image_playlist = ["a.png", "b.png", "c.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "b.png"
        assert state.carousel_index == 1

    def test_sequential_wraps_at_end(self):
        state.image_playlist = ["a.png", "b.png", "c.png"]
        state.custom_image_path = "c.png"
        state.carousel_index = 2
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "a.png"
        assert state.carousel_index == 0

    def test_skips_one_missing_file(self):
        state.image_playlist = ["a.png", "missing.png", "c.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        with patch("app.loops.display.os.path.exists", side_effect=lambda p: p != "missing.png"):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "c.png"
        assert "missing.png" not in state.image_playlist

    def test_skips_multiple_consecutive_missing_files(self):
        state.image_playlist = ["a.png", "m1.png", "m2.png", "d.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        missing = {"m1.png", "m2.png"}
        with patch("app.loops.display.os.path.exists", side_effect=lambda p: p not in missing):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "d.png"
        assert "m1.png" not in state.image_playlist
        assert "m2.png" not in state.image_playlist

    def test_resync_after_external_deletion_before_current_image(self):
        state.image_playlist = ["b.png", "c.png"]
        state.custom_image_path = "c.png"
        state.carousel_index = 2  # stale: was correct when A was present
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "b.png"
        assert state.carousel_index == 0

    def test_resync_inside_loop_after_removal_shifts_index(self):
        state.image_playlist = ["a.png", "missing.png", "c.png", "d.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        with patch("app.loops.display.os.path.exists", side_effect=lambda p: p != "missing.png"):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "c.png"
        assert "missing.png" not in state.image_playlist

    def test_playlist_collapses_to_one_stale_current_updates_to_remaining(self):
        state.image_playlist = ["current.png", "b_missing.png"]
        state.custom_image_path = "current.png"
        state.carousel_index = 0
        with patch("app.loops.display.os.path.exists", side_effect=lambda p: p == "current.png"):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "current.png"
        assert state.carousel_index == 0
        assert state.image_playlist == ["current.png"]

    def test_playlist_collapses_next_missing_keeps_current(self):
        state.image_playlist = ["m1.png", "m2.png"]
        state.custom_image_path = "m1.png"
        state.carousel_index = 0
        with patch("app.loops.display.os.path.exists", return_value=False):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "m1.png"
        assert state.carousel_index == 0
        assert state.image_playlist == ["m1.png"]

    def test_playlist_collapses_current_missing_switches_to_survivor(self):
        state.image_playlist = ["a_missing.png", "b_missing.png", "c.png"]
        state.custom_image_path = "a_missing.png"
        state.carousel_index = 0
        missing = {"a_missing.png", "b_missing.png"}
        with patch("app.loops.display.os.path.exists", side_effect=lambda p: p not in missing):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "c.png"
        assert "b_missing.png" not in state.image_playlist

    def test_skip_next_advance_consumed_without_advancing(self):
        state.image_playlist = ["a.png", "b.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        state.carousel_refresh_count = 0
        state.carousel_skip_next_advance = True
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings(interval=1))
        assert state.custom_image_path == "a.png"
        assert state.carousel_refresh_count == 0
        assert state.carousel_skip_next_advance is False

    def test_skip_next_advance_only_suppresses_once(self):
        state.image_playlist = ["a.png", "b.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        state.carousel_refresh_count = 0
        state.carousel_skip_next_advance = True
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings(interval=1))  # consumed, no advance
            _maybe_advance_carousel(_make_settings(interval=1))  # normal advance now applies
        assert state.custom_image_path == "b.png"

    def test_stale_index_corrected_after_collapse_to_one(self):
        state.image_playlist = ["a.png", "b_missing.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 1  # stale
        with patch("app.loops.display.os.path.exists", side_effect=lambda p: p != "b_missing.png"):
            _maybe_advance_carousel(_make_settings())
        assert state.carousel_index == 0
        assert state.image_playlist == ["a.png"]
