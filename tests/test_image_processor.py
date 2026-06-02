"""Unit tests for app.display.image_processor."""
from __future__ import annotations

import io
import os
import tempfile

import pytest
from PIL import Image

from app.display.image_processor import make_display_image, make_preview_bytes, _TARGET_W, _TARGET_H


def _make_tmp_image(mode: str = "RGB", size: tuple = (800, 600), color=(128, 64, 32)) -> str:
    img = Image.new(mode, size, color)
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    img.save(path)
    return path


class TestMakeDisplayImage:
    def test_output_size(self):
        path = _make_tmp_image()
        try:
            result = make_display_image(path)
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_output_mode_is_rgb(self):
        path = _make_tmp_image()
        try:
            result = make_display_image(path)
            assert result.mode == "RGB"
        finally:
            os.unlink(path)

    def test_pixels_are_valid_rgb(self):
        """Output pixels must be valid RGB values (each channel 0–255)."""
        path = _make_tmp_image()
        try:
            result = make_display_image(path)
            assert all(0 <= c <= 255 for px in result.get_flattened_data() for c in px)
        finally:
            os.unlink(path)

    def test_with_valid_crop(self):
        path = _make_tmp_image(size=(1000, 800))
        try:
            result = make_display_image(path, crop={"x": 100, "y": 100, "w": 400, "h": 600})
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_crop_beyond_bounds_uses_white_padding(self):
        path = _make_tmp_image(size=(200, 200), color=(0, 0, 0))
        try:
            # Crop far outside image — should return correct size without raising
            result = make_display_image(path, crop={"x": 100, "y": 100, "w": 500, "h": 500})
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_negative_offset_top_left_is_white(self):
        """Negative x/y crop: out-of-bounds top-left area should be white after padding."""
        # Black image; crop starts 50px before image on both axes.
        # The top-left region of the crop is outside the image → white padding.
        path = _make_tmp_image(size=(200, 200), color=(0, 0, 0))
        try:
            result = make_display_image(path, crop={"x": -50, "y": -50, "w": 250, "h": 250})
            assert result.size == (_TARGET_W, _TARGET_H)
            # Top-left output pixel maps to the padding region → should be white
            assert result.getpixel((0, 0)) == (255, 255, 255)
        finally:
            os.unlink(path)

    def test_fully_outside_image_is_white(self):
        """Crop completely outside the image should produce an all-white result."""
        path = _make_tmp_image(size=(200, 200), color=(0, 0, 0))
        try:
            result = make_display_image(path, crop={"x": 300, "y": 300, "w": 280, "h": 448})
            assert result.size == (_TARGET_W, _TARGET_H)
            pixels = set(result.get_flattened_data())
            assert pixels == {(255, 255, 255)}, f"Expected all-white, got: {pixels}"
        finally:
            os.unlink(path)

    def test_crop_right_overflow_white_corner(self):
        """Crop extending beyond right edge: far-right output pixels should be white."""
        path = _make_tmp_image(size=(200, 200), color=(0, 0, 0))
        try:
            # Crop starts inside image (x=100) but extends 300px right (x+w=400 > img_w=200)
            result = make_display_image(path, crop={"x": 100, "y": 0, "w": 300, "h": 200})
            assert result.size == (_TARGET_W, _TARGET_H)
            # Far-right output column maps to the out-of-bounds padding → white
            assert result.getpixel((_TARGET_W - 1, _TARGET_H // 2)) == (255, 255, 255)
        finally:
            os.unlink(path)

    def test_invalid_crop_zero_width_raises(self):
        path = _make_tmp_image()
        try:
            with pytest.raises(ValueError, match="Invalid crop"):
                make_display_image(path, crop={"x": 0, "y": 0, "w": 0, "h": 100})
        finally:
            os.unlink(path)

    def test_invalid_crop_negative_height_raises(self):
        path = _make_tmp_image()
        try:
            with pytest.raises(ValueError):
                make_display_image(path, crop={"x": 0, "y": 0, "w": 100, "h": -1})
        finally:
            os.unlink(path)

    def test_rgba_input_handled(self):
        path = _make_tmp_image(mode="RGBA", size=(400, 600), color=(100, 150, 200, 128))
        try:
            result = make_display_image(path)
            assert result.size == (_TARGET_W, _TARGET_H)
            assert result.mode == "RGB"
        finally:
            os.unlink(path)

    def test_grayscale_input_handled(self):
        path = _make_tmp_image(mode="L", size=(400, 600), color=128)
        try:
            result = make_display_image(path)
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_nonexistent_file_raises(self):
        with pytest.raises(OSError):
            make_display_image("/nonexistent/path.png")

    def test_portrait_input(self):
        path = _make_tmp_image(size=(300, 900))
        try:
            result = make_display_image(path)
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_landscape_input(self):
        path = _make_tmp_image(size=(1200, 400))
        try:
            result = make_display_image(path)
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)


class TestTransform:
    def test_rotate_90_returns_correct_size(self):
        path = _make_tmp_image(size=(300, 200))
        try:
            result = make_display_image(path, transform={"rotate": 90})
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_rotate_180_returns_correct_size(self):
        path = _make_tmp_image()
        try:
            result = make_display_image(path, transform={"rotate": 180})
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_flip_x_returns_correct_size(self):
        path = _make_tmp_image()
        try:
            result = make_display_image(path, transform={"flip_x": True})
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_flip_y_returns_correct_size(self):
        path = _make_tmp_image()
        try:
            result = make_display_image(path, transform={"flip_y": True})
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_combined_flip_and_rotate(self):
        path = _make_tmp_image(size=(400, 300))
        try:
            result = make_display_image(
                path, transform={"rotate": 90, "flip_x": True, "flip_y": False}
            )
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_no_transform_same_as_none(self):
        """Empty transform dict behaves same as transform=None."""
        path = _make_tmp_image()
        try:
            r1 = make_display_image(path, transform=None)
            r2 = make_display_image(path, transform={})
            assert r1.get_flattened_data() == r2.get_flattened_data()
        finally:
            os.unlink(path)

    def test_rotate_360_noop(self):
        path = _make_tmp_image()
        try:
            r1 = make_display_image(path, transform=None)
            r2 = make_display_image(path, transform={"rotate": 360})
            assert r1.get_flattened_data() == r2.get_flattened_data()
        finally:
            os.unlink(path)

    def test_flip_x_swaps_halves(self):
        """After flipX the original right-white half should appear on the left."""
        img = Image.new("L", (200, 200), 255)   # all white
        for y in range(200):
            for x in range(100):
                img.putpixel((x, y), 0)           # left half → black
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        img.save(path)
        try:
            result = make_display_image(path, transform={"flip_x": True})
            # After flip: left should be white (was right), right should be black (was left)
            lx = _TARGET_W // 8          # safely in left quarter
            rx = _TARGET_W * 7 // 8     # safely in right quarter
            my = _TARGET_H // 2
            assert result.getpixel((lx, my)) == (255, 255, 255), "left side should be white after flipX"
            assert result.getpixel((rx, my)) == (0, 0, 0),       "right side should be black after flipX"
        finally:
            os.unlink(path)

    def test_rotate_90cw_top_becomes_right(self):
        """After 90° CW the original top-white half should appear on the right side."""
        img = Image.new("L", (200, 200), 0)      # all black
        for y in range(100):
            for x in range(200):
                img.putpixel((x, y), 255)         # top half → white
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        img.save(path)
        try:
            result = make_display_image(path, transform={"rotate": 90})
            # After 90° CW: original top (white) → right side, original bottom (black) → left
            lx = _TARGET_W // 8
            rx = _TARGET_W * 7 // 8
            my = _TARGET_H // 2
            assert result.getpixel((rx, my)) == (255, 255, 255), "right side should be white after 90° CW"
            assert result.getpixel((lx, my)) == (0, 0, 0),       "left side should be black after 90° CW"
        finally:
            os.unlink(path)


class TestMakePreviewBytes:
    def test_returns_valid_png(self):
        path = _make_tmp_image()
        try:
            data = make_preview_bytes(path)
            assert data[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes
            img = Image.open(io.BytesIO(data))
            assert img.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_with_crop(self):
        path = _make_tmp_image(size=(800, 600))
        try:
            data = make_preview_bytes(path, crop={"x": 50, "y": 50, "w": 300, "h": 480})
            assert len(data) > 0
        finally:
            os.unlink(path)

    def test_pixels_are_epaper_palette_only(self):
        """Preview bytes must contain only the 6 e-paper palette colors."""
        _EPAPER_COLORS = {
            (0, 0, 0),
            (255, 255, 255),
            (255, 255, 0),
            (255, 0, 0),
            (0, 0, 255),
            (0, 255, 0),
        }
        # Colorful source image to exercise quantization
        path = _make_tmp_image(color=(128, 64, 200))
        try:
            data = make_preview_bytes(path)
            img = Image.open(io.BytesIO(data)).convert("RGB")
            unknown = set(img.get_flattened_data()) - _EPAPER_COLORS
            assert not unknown, f"Non-palette pixels found: {unknown}"
        finally:
            os.unlink(path)
