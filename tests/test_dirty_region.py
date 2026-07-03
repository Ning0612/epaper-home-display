"""Unit tests for app.display.dirty_region."""
from __future__ import annotations

from PIL import Image

from app.display.dirty_region import MAX_REGIONS, compute_dirty_regions, pack_mono_buffer

WIDTH, HEIGHT = 800, 480


def _blank(color=(255, 255, 255)) -> Image.Image:
    return Image.new("RGB", (WIDTH, HEIGHT), color)


def _with_patch(base: Image.Image, box: tuple[int, int, int, int], color=(0, 0, 0)) -> Image.Image:
    img = base.copy()
    left, top, right, bottom = box
    for y in range(top, bottom):
        for x in range(left, right):
            img.putpixel((x, y), color)
    return img


class TestComputeDirtyRegions:
    def test_no_baseline_returns_none(self):
        curr = _blank()
        assert compute_dirty_regions(None, curr) is None

    def test_size_mismatch_returns_none(self):
        prev = Image.new("RGB", (100, 100), (255, 255, 255))
        curr = _blank()
        assert compute_dirty_regions(prev, curr) is None

    def test_identical_images_return_empty_list(self):
        prev = _blank()
        curr = _blank()
        assert compute_dirty_regions(prev, curr) == []

    def test_single_small_patch_returns_one_aligned_region(self):
        prev = _blank()
        curr = _with_patch(prev, (100, 100, 120, 120))

        regions = compute_dirty_regions(prev, curr)

        assert regions is not None
        assert len(regions) == 1
        xs, ys, xe, ye = regions[0]
        assert xs % 8 == 0
        assert xe % 8 == 0
        assert xs <= 100 and xe >= 120
        assert ys <= 100 and ye >= 120

    def test_far_apart_patches_return_two_regions(self):
        prev = _blank()
        curr = _with_patch(prev, (0, 0, 20, 20))
        curr = _with_patch(curr, (700, 400, 720, 420))

        regions = compute_dirty_regions(prev, curr)

        assert regions is not None
        assert len(regions) == 2
        for xs, ys, xe, ye in regions:
            # Each region must be tightly localized, not spanning the gap
            # between the two patches.
            assert (xe - xs) < 200
            assert (ye - ys) < 200

    def test_too_many_scattered_regions_merge_into_one(self):
        prev = _blank()
        curr = prev
        # Eight small patches spread far apart so each lands in its own
        # connected component, exceeding MAX_REGIONS.
        assert MAX_REGIONS < 8
        boxes = [
            (x * 100, y * 100, x * 100 + 10, y * 100 + 10)
            for y in range(2)
            for x in range(4)
        ]
        for box in boxes:
            curr = _with_patch(curr, box)

        regions = compute_dirty_regions(prev, curr)

        assert regions is not None
        assert len(regions) == 1
        xs, ys, xe, ye = regions[0]
        all_left = min(b[0] for b in boxes)
        all_top = min(b[1] for b in boxes)
        all_right = max(b[2] for b in boxes)
        all_bottom = max(b[3] for b in boxes)
        assert xs <= all_left and xe >= all_right
        assert ys <= all_top and ye >= all_bottom


class TestPackMonoBuffer:
    def test_all_black_image_packs_to_ff_bytes(self):
        # Matches EPD.getbuffer(): hardware-verified on real epd7in5_V2 (a
        # theoretical no-invert derivation looked right on paper but rendered
        # partial refreshes with flipped black/white on the actual panel).
        img = Image.new("1", (16, 4), 0)
        buf = pack_mono_buffer(img)
        assert len(buf) == (16 // 8) * 4
        assert all(b == 0xFF for b in buf)

    def test_all_white_image_packs_to_zero_bytes(self):
        img = Image.new("1", (16, 4), 1)
        buf = pack_mono_buffer(img)
        assert len(buf) == (16 // 8) * 4
        assert all(b == 0x00 for b in buf)

    def test_buffer_length_matches_dimensions(self):
        img = Image.new("RGB", (40, 10), (0, 0, 0))
        buf = pack_mono_buffer(img)
        assert len(buf) == (40 // 8) * 10
