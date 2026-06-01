from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.loops.display import _maybe_advance_carousel
from app.state import state


@pytest.fixture(autouse=True)
def reset_carousel_state():
    state.image_playlist = []
    state.carousel_index = 0
    state.custom_image_path = None
    state.carousel_last_advance = None
    yield
    state.image_playlist = []
    state.carousel_index = 0
    state.custom_image_path = None
    state.carousel_last_advance = None


def _make_settings(enabled=True, interval=30, mode="sequential"):
    s = MagicMock()
    s.images.carousel_enabled = enabled
    s.images.carousel_interval_minutes = interval
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

    def test_no_op_before_interval_elapsed(self):
        state.image_playlist = ["a.png", "b.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        state.carousel_last_advance = datetime.now()
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings(interval=30))
        assert state.custom_image_path == "a.png"

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
        # Playlist was [A, B, C]; A deleted externally → [B, C]; stale index=2 (was C)
        # Re-sync finds C at index 1; next sequential = index 0 (B)
        state.image_playlist = ["b.png", "c.png"]
        state.custom_image_path = "c.png"
        state.carousel_index = 2  # stale: was correct when A was present
        with patch("app.loops.display.os.path.exists", return_value=True):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "b.png"
        assert state.carousel_index == 0

    def test_resync_inside_loop_after_removal_shifts_index(self):
        # [A, missing, C, D]; current=A (idx 0), next=missing (idx 1)
        # After removing missing → [A, C, D], re-sync sets idx=0 (A), next=(0+1)%3=1 (C)
        state.image_playlist = ["a.png", "missing.png", "c.png", "d.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 0
        with patch("app.loops.display.os.path.exists", side_effect=lambda p: p != "missing.png"):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "c.png"
        assert "missing.png" not in state.image_playlist

    def test_playlist_collapses_to_one_stale_current_updates_to_remaining(self):
        # [current_missing, b]; current=current_missing, next=b which is also missing
        # → playlist collapses to [current_missing] alone; custom_image_path was current_missing
        # Fix: after collapse, custom_image_path should point to the surviving item
        state.image_playlist = ["current.png", "b_missing.png"]
        state.custom_image_path = "current.png"
        state.carousel_index = 0
        # "current.png" exists but next candidate "b_missing.png" doesn't
        # → remove b_missing → playlist = ["current.png"] → while exits
        # custom_image_path is already "current.png" which is still in playlist → index stays 0
        with patch("app.loops.display.os.path.exists", side_effect=lambda p: p == "current.png"):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "current.png"
        assert state.carousel_index == 0
        assert state.image_playlist == ["current.png"]

    def test_playlist_collapses_next_missing_keeps_current(self):
        # current=m1 (not yet tried as candidate), next=m2 missing
        # → m2 removed, playlist=[m1], while exits
        # collapse: m1 still in playlist → custom_image_path unchanged (renderer handles missing via "Image Error")
        state.image_playlist = ["m1.png", "m2.png"]
        state.custom_image_path = "m1.png"
        state.carousel_index = 0
        with patch("app.loops.display.os.path.exists", return_value=False):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "m1.png"
        assert state.carousel_index == 0
        assert state.image_playlist == ["m1.png"]

    def test_playlist_collapses_current_missing_switches_to_survivor(self):
        # [a_missing, surviving]; current points to a_missing (stale)
        # while loop: re-sync can't find a_missing → index = 0 % 2 = 0, next = idx 1 = surviving
        # surviving exists → BUT wait: we check playlist[idx=1] which is surviving
        # Actually: re-sync: a_missing not in [a_missing, surviving]... wait it IS
        # Let me re-check: custom=a_missing, playlist=[a_missing, surviving]
        # re-sync: a_missing in playlist → idx=0, next = 1 = surviving, surviving exists → advance
        # So this is actually NOT a collapse case; it would advance normally.
        # Test the actual collapse: current=a_missing, next=b_missing, only c survives
        state.image_playlist = ["a_missing.png", "b_missing.png", "c.png"]
        state.custom_image_path = "a_missing.png"
        state.carousel_index = 0
        missing = {"a_missing.png", "b_missing.png"}
        # sequential: current=a_missing(idx0), next=b_missing(idx1) → remove b_missing
        # re-sync: a_missing still in [a_missing, c], idx=0, next=1=c → c exists → advance ✓
        with patch("app.loops.display.os.path.exists", side_effect=lambda p: p not in missing):
            _maybe_advance_carousel(_make_settings())
        assert state.custom_image_path == "c.png"
        assert "b_missing.png" not in state.image_playlist

    def test_stale_index_corrected_after_collapse_to_one(self):
        # stale carousel_index=1 after collapse to 1 item → should be reset to 0
        state.image_playlist = ["a.png", "b_missing.png"]
        state.custom_image_path = "a.png"
        state.carousel_index = 1  # stale: was pointing to b_missing
        with patch("app.loops.display.os.path.exists", side_effect=lambda p: p != "b_missing.png"):
            _maybe_advance_carousel(_make_settings())
        # sequential: re-sync a.png→idx=0, next=1=b_missing → remove → playlist=[a.png]
        # collapse cleanup: a.png in playlist → carousel_index = index of a.png = 0
        assert state.carousel_index == 0
        assert state.image_playlist == ["a.png"]
