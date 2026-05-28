"""Hardware test: Waveshare 7.5" V2 e-Paper. Run on Pi: python -m scripts.test_epaper"""
from __future__ import annotations

import sys
import time


def main() -> None:
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
        from waveshare_epd import epd7in5_V2
    except ImportError as e:
        print(f"ERROR: Waveshare driver not found in lib/waveshare_epd/ — {e}")
        sys.exit(1)

    from PIL import Image, ImageDraw, ImageFont

    print("Initialising e-Paper 7.5\" V2 ...")
    epd = epd7in5_V2.EPD()
    epd.init()
    print("  init OK")

    print("Clearing display ...")
    epd.Clear()
    print("  clear OK")

    print("Drawing test image ...")
    img = Image.new("L", (800, 480), 255)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(10, 10), (790, 470)], outline=0, width=3)
    try:
        font = ImageFont.truetype("assets/fonts/DejaVuSans.ttf", 40)
    except (IOError, OSError):
        font = ImageFont.load_default()
    draw.text((50, 200), "ePaper Home Display Test OK", font=font, fill=0)

    epd.display(epd.getbuffer(img))
    print("  display OK")

    time.sleep(3)
    epd.sleep()
    print("  sleep OK")
    print("PASS")


if __name__ == "__main__":
    main()
