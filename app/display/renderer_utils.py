from __future__ import annotations

import logging
import math
from collections import Counter
from datetime import datetime, date, timezone
from typing import TypeAlias

from PIL import Image, ImageDraw, ImageFont

from app.display.renderer_constants import FG, COLOR_RED, COLOR_ORANGE, COLOR_GREEN, COLOR_BLUE, _WEATHER_SEVERITY

logger = logging.getLogger(__name__)

_FONT_PATH = "assets/fonts/DejaVuSans.ttf"
_FONT_BOLD_PATH = "assets/fonts/DejaVuSans-Bold.ttf"

_FONT_CACHE: dict[tuple[int, bool], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
_IconAsset: TypeAlias = tuple[Image.Image, Image.Image | None]
_ICON_CACHE: dict[tuple[str, int], _IconAsset | None] = {}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = (size, bold)
    if key not in _FONT_CACHE:
        path = _FONT_BOLD_PATH if bold else _FONT_PATH
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except (IOError, OSError):
            if bold:
                try:
                    _FONT_CACHE[key] = ImageFont.truetype(_FONT_PATH, size)
                except (IOError, OSError):
                    _FONT_CACHE[key] = ImageFont.load_default()
            else:
                _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def _load_weather_icon(main: str, size: int) -> _IconAsset | None:
    if not main:
        return None
    key = (main, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    path = f"assets/weather_icons/{main}.png"
    try:
        with Image.open(path) as raw:
            raw.load()
            icon_img = raw.convert("RGB").resize((size, size), Image.LANCZOS)
            alpha: Image.Image | None = None
            if raw.mode == "RGBA":
                alpha = raw.split()[3].resize((size, size), Image.LANCZOS)
            result: _IconAsset = (icon_img, alpha)
    except (IOError, OSError, IndexError) as e:
        logger.warning("weather icon load failed (%s): %s", path, e)
        _ICON_CACHE[key] = None
        return None
    _ICON_CACHE[key] = result
    return result


def _paste_icon(img: Image.Image, main: str, size: int, x: int, y: int) -> bool:
    asset = _load_weather_icon(main, size)
    if asset is None:
        return False
    icon_img, alpha = asset
    img.paste(icon_img, (x, y), alpha)
    return True


def _draw_progress_bar(
    draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, pct: float,
    fill: tuple[int, int, int] = FG,
) -> None:
    pct = max(0.0, min(1.0, pct))
    draw.rectangle([(x, y), (x + w - 1, y + h - 1)], outline=FG, width=1)
    fill_w = int((w - 2) * pct)
    if fill_w > 0:
        draw.rectangle([(x + 1, y + 1), (x + fill_w, y + h - 2)], fill=fill)


def _ellipsize(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_w: int,
) -> str:
    if not text:
        return text

    def _text_w(value: str) -> int:
        bb = draw.textbbox((0, 0), value, font=font)
        return bb[2] - bb[0]

    if _text_w(text) <= max_w:
        return text
    ellipsis = "…"
    if _text_w(ellipsis) > max_w:
        return ""
    lo, hi = 0, len(text)
    best = ellipsis
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = text[:mid].rstrip() + ellipsis
        if _text_w(candidate) <= max_w:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def _weather_item(payload: dict) -> dict:
    return (payload.get("weather") or [{}])[0]


def _pick_daily_forecast(forecast_list: list[dict], count: int = 4) -> list[dict]:
    today = date.today()
    by_day: dict[date, list[dict]] = {}
    for entry in forecast_list:
        dt_unix = entry.get("dt")
        try:
            if dt_unix is not None:
                # dt is a UTC Unix timestamp; fromtimestamp converts to host local time
                d = datetime.fromtimestamp(int(dt_unix)).date()
            else:
                # dt_txt is UTC; convert to local before taking date
                dt_txt = entry.get("dt_txt", "")
                utc_dt = datetime.strptime(dt_txt[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                d = utc_dt.astimezone().date()
        except (TypeError, ValueError, OSError):
            continue
        if d < today:
            continue
        by_day.setdefault(d, []).append(entry)

    result: list[dict] = []
    for d in sorted(by_day.keys())[:count]:
        slots = by_day[d]

        temps = [s.get("main", {}).get("temp") for s in slots]
        temps = [t for t in temps if isinstance(t, (int, float))]
        avg_temp: float | None = sum(temps) / len(temps) if temps else None

        mains = [_weather_item(s).get("main", "") for s in slots]
        mains = [m for m in mains if m]
        if mains:
            counts = Counter(mains)
            mode_main = max(counts, key=lambda m: (counts[m], _WEATHER_SEVERITY.get(m, 0)))
        else:
            mode_main = ""

        pops = [s.get("pop") or 0 for s in slots]
        try:
            max_pop: float = max(float(p) for p in pops)
        except (TypeError, ValueError):
            max_pop = 0.0

        noon = next(
            (s for s in slots if isinstance(s.get("dt_txt"), str) and "12:00:00" in s["dt_txt"]),
            slots[0],
        )
        result.append({
            "dt_txt": d.strftime("%Y-%m-%d 12:00:00"),  # local date, avoids UTC/local mismatch in renderer
            "weather": [{"main": mode_main}],
            "main": {"temp": avg_temp},
            "pop": max_pop,
        })

    return result


def _usage_color(pct: float | None, color: bool = True) -> tuple[int, int, int]:
    """Return display color for a usage progress bar: green <60%, orange 60-80%, red >=80%."""
    if not color or pct is None:
        return FG
    if pct >= 0.80:
        return COLOR_RED
    if pct >= 0.60:
        return COLOR_ORANGE
    return COLOR_GREEN


def _temp_color(temp: float | None, color: bool = True) -> tuple[int, int, int]:
    """Return display color for a temperature value."""
    if not color or temp is None:
        return FG
    if temp >= 30:
        return COLOR_RED
    if temp <= 15:
        return COLOR_BLUE
    return FG


def _draw_thermometer_icon(
    draw: ImageDraw.ImageDraw, x: int, y: int, size: int, fill: tuple[int, int, int] = FG,
) -> None:
    """Draw a hollow (outline) thermometer glyph inside the [x, x+size] x [y, y+size] box."""
    if size <= 0:
        return
    cx = x + size / 2
    bulb_r = size * 0.28
    bulb_cy = y + size - bulb_r
    stem_w = size * 0.30
    stem_top = y + size * 0.05
    lw = max(1, round(size * 0.09))
    half_w = stem_w / 2

    # Stop the stem's side lines where they meet the bulb circle so the
    # outline reads as a clean capsule-on-circle, not a line crossing
    # through the middle of the bulb.
    inset = bulb_r * bulb_r - half_w * half_w
    stem_bottom = bulb_cy - math.sqrt(inset) if inset > 0 else bulb_cy

    draw.line([(cx - half_w, stem_bottom), (cx - half_w, stem_top + half_w)], fill=fill, width=lw)
    draw.line([(cx + half_w, stem_bottom), (cx + half_w, stem_top + half_w)], fill=fill, width=lw)
    draw.arc([cx - half_w, stem_top, cx + half_w, stem_top + stem_w], 180, 360, fill=fill, width=lw)
    draw.ellipse([cx - bulb_r, bulb_cy - bulb_r, cx + bulb_r, bulb_cy + bulb_r], outline=fill, width=lw)


def _draw_droplet_icon(
    draw: ImageDraw.ImageDraw, x: int, y: int, size: int, fill: tuple[int, int, int] = FG,
) -> None:
    """Draw a hollow (outline) water-drop glyph inside the [x, x+size] x [y, y+size] box."""
    if size <= 0:
        return
    cx = x + size / 2
    r = size * 0.32
    circle_cy = y + size - r - size * 0.02
    apex_y = y + size * 0.05
    lw = max(1, round(size * 0.09))

    # Tail lines meet the circle exactly on its boundary (not inside it) so
    # the outline reads as a single seamless teardrop instead of a triangle
    # overlapping a circle.
    angle = math.radians(55)
    left_pt = (cx - r * math.sin(angle), circle_cy - r * math.cos(angle))
    right_pt = (cx + r * math.sin(angle), circle_cy - r * math.cos(angle))

    draw.ellipse([cx - r, circle_cy - r, cx + r, circle_cy + r], outline=fill, width=lw)
    draw.line([(cx, apex_y), left_pt], fill=fill, width=lw)
    draw.line([(cx, apex_y), right_pt], fill=fill, width=lw)


def _cx_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    col_x: int,
    col_w: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int] = FG,
) -> None:
    """Draw text horizontally centered within [col_x, col_x+col_w)."""
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    draw.text((col_x + (col_w - tw) // 2, y), text, font=font, fill=fill)
