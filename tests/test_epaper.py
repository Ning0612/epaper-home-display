"""Unit tests for app.display.epaper.RealEpaper."""
from __future__ import annotations

from PIL import Image

from app.display.epaper import RealEpaper

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


class _FakeEpdNoPartial:
    """Mimics epd7in3e: no init_fast/display_fast/display_Partial/init_part."""

    width = WIDTH
    height = HEIGHT

    def __init__(self) -> None:
        self.calls: list[str] = []

    def init(self) -> None:
        self.calls.append("init")

    def getbuffer(self, image: Image.Image):
        return image

    def display(self, buf) -> None:
        self.calls.append("display")

    def Clear(self) -> None:
        self.calls.append("Clear")

    def sleep(self) -> None:
        self.calls.append("sleep")


class _FakeEpdPartial:
    """Mimics epd7in5_V2: has init_fast, init_part, display_Partial (no display_fast)."""

    width = WIDTH
    height = HEIGHT

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.partial_calls: list[tuple[int, int, int, int]] = []
        self.partial_buffers: list[bytearray] = []

    def init(self) -> None:
        self.calls.append("init")

    def init_fast(self) -> None:
        self.calls.append("init_fast")

    def init_part(self) -> None:
        self.calls.append("init_part")

    def getbuffer(self, image: Image.Image):
        return image

    def display(self, buf) -> None:
        self.calls.append("display")

    def display_Partial(self, buf, xs, ys, xe, ye) -> None:
        self.calls.append("display_Partial")
        self.partial_calls.append((xs, ys, xe, ye))
        self.partial_buffers.append(bytearray(buf))

    def Clear(self) -> None:
        self.calls.append("Clear")

    def sleep(self) -> None:
        self.calls.append("sleep")


def _make_real_epaper(epd_instance) -> RealEpaper:
    class _Module:
        @staticmethod
        def EPD():
            return epd_instance

    return RealEpaper(_Module())


class TestRealEpaperWithoutPartialSupport:
    def test_repeated_display_always_uses_full_path(self):
        fake = _FakeEpdNoPartial()
        epaper = _make_real_epaper(fake)

        image = _blank()
        epaper.display(image, full_refresh=False)
        epaper.display(image, full_refresh=False)

        assert "display_Partial" not in fake.calls
        assert fake.calls.count("display") == 2
        assert fake.calls.count("init") == 2


class TestRealEpaperWithPartialSupport:
    def test_first_call_has_no_baseline_and_uses_fallback(self):
        fake = _FakeEpdPartial()
        epaper = _make_real_epaper(fake)

        epaper.display(_blank(), full_refresh=False)

        assert fake.calls == ["init_fast", "display", "sleep"]
        assert epaper._last_image is not None

    def test_identical_second_call_skips_panel_write(self):
        fake = _FakeEpdPartial()
        epaper = _make_real_epaper(fake)
        image = _blank()

        epaper.display(image, full_refresh=False)
        fake.calls.clear()
        epaper.display(image, full_refresh=False)

        assert fake.calls == []

    def test_partial_buffer_matches_getbuffer_convention(self):
        # Hardware-verified on real epd7in5_V2: the buffer handed to
        # display_Partial() must use the same inverted convention as
        # EPD.getbuffer() (convert("1") then XOR 0xFF), not raw mode-1 bytes.
        fake = _FakeEpdPartial()
        epaper = _make_real_epaper(fake)
        base = _blank()

        epaper.display(base, full_refresh=False)
        fake.calls.clear()

        box = (104, 104, 112, 112)  # 8-aligned so no region growth surprises
        changed = _with_patch(base, box, color=(0, 0, 0))
        epaper.display(changed, full_refresh=False)

        assert len(fake.partial_calls) == 1
        xs, ys, xe, ye = fake.partial_calls[0]
        sent_buf = fake.partial_buffers[0]

        raw_crop = changed.crop((xs, ys, xe, ye)).convert("1").tobytes("raw")
        expected = bytearray(b ^ 0xFF for b in raw_crop)
        assert sent_buf == expected

    def test_small_change_uses_partial_path(self):
        fake = _FakeEpdPartial()
        epaper = _make_real_epaper(fake)
        base = _blank()

        epaper.display(base, full_refresh=False)
        fake.calls.clear()

        changed = _with_patch(base, (100, 100, 120, 120))
        epaper.display(changed, full_refresh=False)

        assert fake.calls[0] == "init_part"
        assert fake.calls.count("display_Partial") >= 1
        assert fake.calls[-1] == "sleep"
        assert "init" not in fake.calls
        assert "display" not in fake.calls

    def test_full_refresh_forces_full_path_even_with_baseline(self):
        fake = _FakeEpdPartial()
        epaper = _make_real_epaper(fake)
        base = _blank()

        epaper.display(base, full_refresh=False)
        fake.calls.clear()

        changed = _with_patch(base, (100, 100, 120, 120))
        epaper.display(changed, full_refresh=True)

        assert fake.calls == ["init", "display", "sleep"]
        assert "display_Partial" not in fake.calls

    def test_clear_resets_baseline_so_next_display_uses_fallback(self):
        fake = _FakeEpdPartial()
        epaper = _make_real_epaper(fake)
        base = _blank()

        epaper.display(base, full_refresh=False)
        fake.calls.clear()

        epaper.clear()
        assert epaper._last_image is None
        fake.calls.clear()

        changed = _with_patch(base, (100, 100, 120, 120))
        epaper.display(changed, full_refresh=False)

        assert fake.calls == ["init_fast", "display", "sleep"]
        assert "display_Partial" not in fake.calls
