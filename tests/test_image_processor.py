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

    def test_output_mode_is_grayscale(self):
        path = _make_tmp_image()
        try:
            result = make_display_image(path)
            assert result.mode == "L"
        finally:
            os.unlink(path)

    def test_pixels_only_black_or_white(self):
        """Floyd-Steinberg dithering to 1-bit then L should produce only 0/255."""
        path = _make_tmp_image()
        try:
            result = make_display_image(path)
            pixels = set(result.get_flattened_data())
            assert pixels.issubset({0, 255}), f"Unexpected pixel values: {pixels - {0, 255}}"
        finally:
            os.unlink(path)

    def test_with_valid_crop(self):
        path = _make_tmp_image(size=(1000, 800))
        try:
            result = make_display_image(path, crop={"x": 100, "y": 100, "w": 400, "h": 600})
            assert result.size == (_TARGET_W, _TARGET_H)
        finally:
            os.unlink(path)

    def test_crop_clamped_when_out_of_bounds(self):
        path = _make_tmp_image(size=(200, 200))
        try:
            # Crop exceeds image bounds — should not raise, should clamp
            result = make_display_image(path, crop={"x": 100, "y": 100, "w": 500, "h": 500})
            assert result.size == (_TARGET_W, _TARGET_H)
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
            assert result.mode == "L"
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
