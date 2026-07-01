"""Hardware test: e-Paper display. Panel driver is selected from config.yaml's
display.model (same source the WebUI settings page reads/writes), so this test
always exercises whichever panel is actually configured.

Run on Pi: python -m scripts.test_epaper
"""
from __future__ import annotations

import sys

from PIL import Image, ImageDraw, ImageFont

from app.config import load_settings
from app.display.epaper import MockEpaper, create_epaper

_SIZE = (800, 480)  # native resolution of both supported panels (epd7in3e, epd7in5_V2)

_COLOR_SWATCHES = (
    (255, 0, 0),
    (255, 255, 0),
    (0, 0, 255),
    (0, 255, 0),
)


def main() -> None:
    settings = load_settings()
    model = settings.display.model
    is_color = settings.display.is_color
    print(f"Configured display.model = {model!r} ({'color' if is_color else 'black/white'})")

    epaper = create_epaper(settings.display)
    if isinstance(epaper, MockEpaper):
        print(
            "ERROR: no matching driver in lib/waveshare_epd/ for "
            f"{model!r} (or display.use_mock is true) — falling back to MockEpaper, "
            "no physical panel will be tested"
        )
        sys.exit(1)

    print("Clearing display ...")
    epaper.clear()
    print("  clear OK")

    print("Drawing test image ...")
    img = Image.new("RGB", _SIZE, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(10, 10), (_SIZE[0] - 10, _SIZE[1] - 10)], outline=(0, 0, 0), width=3)
    try:
        font = ImageFont.truetype("assets/fonts/DejaVuSans.ttf", 40)
    except (IOError, OSError):
        font = ImageFont.load_default()
    draw.text(
        (50, 200),
        f"ePaper Home Display Test OK ({model})",
        font=font,
        fill=(255, 0, 0) if is_color else (0, 0, 0),
    )
    if is_color:
        swatch_w = (_SIZE[0] - 20) // len(_COLOR_SWATCHES)
        for i, color in enumerate(_COLOR_SWATCHES):
            x0 = 10 + i * swatch_w
            draw.rectangle([(x0, 300), (x0 + swatch_w - 5, 400)], fill=color)

    epaper.display(img, full_refresh=True)
    print("  display OK")
    print("PASS")


if __name__ == "__main__":
    main()
