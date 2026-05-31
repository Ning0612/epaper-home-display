from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, date, timezone
from typing import TypeAlias

from PIL import Image, ImageDraw, ImageFont

from app.display.renderer_constants import FG, _WEATHER_SEVERITY

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
            icon_l = raw.convert("L").resize((size, size), Image.LANCZOS)
            alpha: Image.Image | None = None
            if raw.mode == "RGBA":
                alpha = raw.split()[3].resize((size, size), Image.LANCZOS)
            result: _IconAsset = (icon_l, alpha)
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
    icon_l, alpha = asset
    img.paste(icon_l, (x, y), alpha)
    return True


def _draw_progress_bar(
    draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, pct: float
) -> None:
    pct = max(0.0, min(1.0, pct))
    draw.rectangle([(x, y), (x + w - 1, y + h - 1)], outline=FG, width=1)
    fill_w = int((w - 2) * pct)
    if fill_w > 0:
        draw.rectangle([(x + 1, y + 1), (x + fill_w, y + h - 2)], fill=FG)


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


def _cx_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    col_x: int,
    col_w: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Draw text horizontally centered within [col_x, col_x+col_w)."""
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    draw.text((col_x + (col_w - tw) // 2, y), text, font=font, fill=FG)
