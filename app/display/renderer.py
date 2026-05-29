from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, date
from typing import TYPE_CHECKING, TypeAlias

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from app.config import Settings
    from app.state import AgentState

logger = logging.getLogger(__name__)

DISPLAY_W, DISPLAY_H = 800, 480
BG = 255
FG = 0
PAD = 8
MARGIN = 8   # screen-edge whitespace

# Content boundary (with screen margin)
_CX = MARGIN                        # 8
_CY = MARGIN                        # 8
_CW = DISPLAY_W - 2 * MARGIN       # 784
_CH = DISPLAY_H - 2 * MARGIN       # 464
_GAP = 8                            # gap between adjacent cards

_LEFT_W = 480                       # width of left column

# ── Weather card: top-left, starts at screen margin ───────────────────────
WEATHER_X, WEATHER_Y = _CX, _CY    # 8, 8
WEATHER_W, WEATHER_H = _LEFT_W, 340

# ── Image card: right column, spans full content height ───────────────────
IMAGE_X = _CX + _LEFT_W + _GAP     # 496
IMAGE_Y = _CY                       # 8
IMAGE_W = (_CX + _CW) - IMAGE_X    # 296
IMAGE_H = _CH                       # 464

# ── Row2: below weather card ──────────────────────────────────────────────
ROW2_Y = WEATHER_Y + WEATHER_H + _GAP   # 288
ROW2_H = (_CY + _CH) - ROW2_Y          # 184

INDOOR_X, INDOOR_Y = _CX, ROW2_Y       # 8, 288
INDOOR_W, INDOOR_H = 90, ROW2_H

AGENT1_X = INDOOR_X + INDOOR_W + _GAP  # 106
AGENT1_Y = ROW2_Y
AGENT1_W, AGENT1_H = 115, ROW2_H

USAGE_X = AGENT1_X + AGENT1_W + _GAP   # 229
USAGE_Y = ROW2_Y
USAGE_W = (_CX + _LEFT_W) - USAGE_X    # 259
USAGE_H = ROW2_H

# Weather card: height of date/time section (inner coords, not counting PAD)
_WX_TOP_H = 215

_WEEKDAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
_WEATHER_SEVERITY: dict[str, int] = {
    "Thunderstorm": 6, "Tornado": 6,
    "Snow": 5, "Sleet": 5,
    "Rain": 4, "Drizzle": 3,
    "Atmosphere": 2, "Mist": 2, "Fog": 2, "Haze": 2,
    "Clouds": 1, "Clear": 0,
}
_FONT_CACHE: dict[tuple[int, bool], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
_FONT_PATH = "assets/fonts/DejaVuSans.ttf"
_FONT_BOLD_PATH = "assets/fonts/DejaVuSans-Bold.ttf"
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


def _pick_daily_forecast(forecast_list: list[dict], count: int = 4) -> list[dict]:
    today = date.today()
    by_day: dict[date, list[dict]] = {}
    for entry in forecast_list:
        dt_txt = entry.get("dt_txt")
        if not isinstance(dt_txt, str):
            continue
        try:
            d = datetime.strptime(dt_txt[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if d == today:
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
            "dt_txt": noon["dt_txt"],
            "weather": [{"main": mode_main}],
            "main": {"temp": avg_temp},
            "pop": max_pop,
        })

    return result


def _weather_item(payload: dict) -> dict:
    return (payload.get("weather") or [{}])[0]


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


def render_dashboard(
    state: "AgentState", settings: "Settings", now: datetime | None = None
) -> Image.Image:
    img = Image.new("L", (DISPLAY_W, DISPLAY_H), BG)
    draw = ImageDraw.Draw(img)
    if now is None:
        now = datetime.now()

    _draw_card_weather(img, draw, state, now)
    _draw_card_image(img, draw, state)
    _draw_card_indoor(draw, state)
    _draw_card_agent1(draw, state)
    _draw_card_usage(draw, state)

    return img


def _draw_card_weather(
    img: Image.Image, draw: ImageDraw.ImageDraw, state: "AgentState", now: datetime
) -> None:
    draw.rectangle(
        [(WEATHER_X, WEATHER_Y), (WEATHER_X + WEATHER_W - 1, WEATHER_Y + WEATHER_H - 1)],
        outline=FG, width=1,
    )

    ix = WEATHER_X + PAD    # 16
    iy = WEATHER_Y + PAD    # 16
    inner_w = WEATHER_W - 2 * PAD   # 504

    # ── Date + Time (top section, vertically centred) ─────────────────────
    # Allocate: date=36px, gap=10, time=160px → content=206px in _WX_TOP_H=215
    dt_top = iy + (_WX_TOP_H - 206) // 2   # iy+4

    date_str = now.strftime("%Y/%m/%d %A")
    _cx_text(draw, date_str, ix, inner_w, dt_top, _font(36, bold=True))

    time_str = now.strftime("%H:%M")
    _cx_text(draw, time_str, ix, inner_w, dt_top + 46, _font(160, bold=True))

    # Divider between date/time and forecast
    div_y = WEATHER_Y + PAD + _WX_TOP_H    # 156
    draw.line([(WEATHER_X + 1, div_y), (WEATHER_X + WEATHER_W - 2, div_y)], fill=FG, width=1)

    # ── Forecast section: Now column + 4 daily columns ────────────────────
    # Layout: [Now=80px] [gap=12px] [4×daily, each=93px]
    now_w = 80
    fc_gap = 12    # separator gap between Now and daily
    daily_w = (inner_w - now_w - fc_gap) // 4   # 99

    fc_y0 = div_y + PAD + 4    # 168 — first row of forecast content

    # Row offsets (relative to fc_y0)
    LBL = 0    # weekday / "Now"
    ICO = 20   # icon
    TMP = 60   # temperature
    POP = 80   # pop% (daily only)

    # Now column
    now_x = ix  # 16
    wi = _weather_item(state.weather_current or {})
    now_main = wi.get("main", "")
    now_temp = (state.weather_current.get("main", {}).get("temp")
                if state.weather_current else None)

    _cx_text(draw, "Now", now_x, now_w, fc_y0 + LBL, _font(16, bold=True))

    icon_x = now_x + (now_w - 36) // 2
    if not _paste_icon(img, now_main, 36, icon_x, fc_y0 + ICO):
        _cx_text(draw, now_main[:4], now_x, now_w, fc_y0 + ICO + 10, _font(14, bold=True))

    now_temp_str = f"{now_temp:.0f}°" if isinstance(now_temp, (int, float)) else "--"
    _cx_text(draw, now_temp_str, now_x, now_w, fc_y0 + TMP, _font(18, bold=True))

    # Light dashed separator between Now and daily
    sep_x = ix + now_w + fc_gap // 2   # 16+96+6=118
    fc_bottom = WEATHER_Y + WEATHER_H - PAD   # 272
    y_sep = fc_y0
    while y_sep < fc_bottom:
        draw.point((sep_x, y_sep), fill=FG)
        y_sep += 3

    # Daily columns
    daily_x0 = ix + now_w + fc_gap   # 16+96+12=124
    fc_entries = _pick_daily_forecast(state.weather_forecast, 4)

    for i, entry in enumerate(fc_entries[:4]):
        col_x = daily_x0 + i * daily_w   # 124, 223, 322, 421

        dt_txt = entry.get("dt_txt", "")
        try:
            day_str = _WEEKDAYS[datetime.strptime(dt_txt[:10], "%Y-%m-%d").weekday()]
        except ValueError:
            day_str = "---"
        _cx_text(draw, day_str, col_x, daily_w, fc_y0 + LBL, _font(14, bold=True))

        fc_main = _weather_item(entry).get("main", "")
        icon_x = col_x + (daily_w - 36) // 2
        if not _paste_icon(img, fc_main, 36, icon_x, fc_y0 + ICO):
            _cx_text(draw, fc_main[:4], col_x, daily_w, fc_y0 + ICO + 10, _font(14, bold=True))

        fc_temp = entry.get("main", {}).get("temp")
        fc_temp_str = f"{fc_temp:.0f}°" if isinstance(fc_temp, (int, float)) else "--"
        _cx_text(draw, fc_temp_str, col_x, daily_w, fc_y0 + TMP, _font(18, bold=True))

        pop = entry.get("pop") or 0
        try:
            pop_str = f"{int(float(pop) * 100)}%"
        except (TypeError, ValueError):
            pop_str = "--%"
        _cx_text(draw, pop_str, col_x, daily_w, fc_y0 + POP, _font(16, bold=True))


def _draw_card_image(img: Image.Image, draw: ImageDraw.ImageDraw, state: "AgentState") -> None:
    draw.rectangle(
        [(IMAGE_X, IMAGE_Y), (IMAGE_X + IMAGE_W - 1, IMAGE_Y + IMAGE_H - 1)],
        outline=FG, width=1,
    )
    ix, iy = IMAGE_X + PAD, IMAGE_Y + PAD
    iw, ih = IMAGE_W - 2 * PAD, IMAGE_H - 2 * PAD

    if state.custom_image_path is None:
        placeholder = "[ No Image ]"
        bb = draw.textbbox((0, 0), placeholder, font=_font(16, bold=True))
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        draw.text((ix + (iw - tw) // 2, iy + (ih - th) // 2), placeholder, font=_font(16, bold=True), fill=FG)
        return

    try:
        with Image.open(state.custom_image_path) as custom:
            custom = custom.convert("L")
            custom.thumbnail((iw, ih), Image.LANCZOS)
            px = ix + (iw - custom.width) // 2
            py = iy + (ih - custom.height) // 2
            img.paste(custom, (px, py))
    except (OSError, IOError) as e:
        logger.warning("custom image load failed: %s", e)
        draw.text((ix + 4, iy + 4), "Image Error", font=_font(16, bold=True), fill=FG)


def _draw_card_indoor(draw: ImageDraw.ImageDraw, state: "AgentState") -> None:
    draw.rectangle(
        [(INDOOR_X, INDOOR_Y), (INDOOR_X + INDOOR_W - 1, INDOOR_Y + INDOOR_H - 1)],
        outline=FG, width=1,
    )
    ix, iy = INDOOR_X + PAD, INDOOR_Y + PAD
    iw = INDOOR_W - 2 * PAD   # 74
    ih = INDOOR_H - 2 * PAD   # 168

    temp_str = f"{state.temperature:.1f}°" if state.temperature is not None else "--°"
    hum_str = f"{state.humidity:.0f}%" if state.humidity is not None else "--%"
    light_str = "bright" if state.light_is_bright else "dim"

    # Vertically centre content in available inner height
    content_h = 14 + 5 + 17 + 5 + 17 + 5 + 12
    sy = iy + max(0, (ih - content_h) // 2)

    _cx_text(draw, "Indoor", ix, iw, sy, _font(14, bold=True))
    _cx_text(draw, temp_str, ix, iw, sy + 19, _font(17, bold=True))
    _cx_text(draw, hum_str, ix, iw, sy + 41, _font(17, bold=True))
    _cx_text(draw, light_str, ix, iw, sy + 63, _font(12, bold=True))


def _draw_card_agent1(draw: ImageDraw.ImageDraw, state: "AgentState") -> None:
    draw.rectangle(
        [(AGENT1_X, AGENT1_Y), (AGENT1_X + AGENT1_W - 1, AGENT1_Y + AGENT1_H - 1)],
        outline=FG, width=1,
    )
    ix, iy = AGENT1_X + PAD, AGENT1_Y + PAD
    iw = AGENT1_W - 2 * PAD   # 99
    ih = AGENT1_H - 2 * PAD   # 168

    door_st = (state.last_door_event.get("state", "?") if state.last_door_event else "N/A")[:10]
    face_id = ((state.last_face_event.get("identity") or "NO_FACE") if state.last_face_event else "N/A")[:10]
    alert_lvl = (
        (state.last_alert.get("level") or state.last_alert.get("type") or "?")
        if state.last_alert else "NONE"
    )[:8]
    mode_map = {"OCCUPIED": "HOME", "UNOCCUPIED": "AWAY", "UNKNOWN": "?"}
    mode_str = mode_map.get(state.presence, state.presence[:6])

    # Vertically centre content in available inner height
    line_h = 18
    content_h = 14 + 4 + 4 * line_h
    sy = iy + max(0, (ih - content_h) // 2)

    _cx_text(draw, "Agent 1", ix, iw, sy, _font(14, bold=True))
    _cx_text(draw, f"D {door_st}", ix, iw, sy + 20, _font(14, bold=True))
    _cx_text(draw, f"F {face_id}", ix, iw, sy + 20 + line_h, _font(14, bold=True))
    _cx_text(draw, f"A {alert_lvl}", ix, iw, sy + 20 + 2 * line_h, _font(14, bold=True))
    _cx_text(draw, f"M {mode_str}", ix, iw, sy + 20 + 3 * line_h, _font(14, bold=True))


def _draw_usage_row(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    pct: float | None,
    reset_text: str | None,
) -> None:
    _LW, _G, _PW, _BW, _BH = 52, 4, 52, 78, 11
    fnt = _font(13, bold=True)
    draw.text((x, y), label, font=fnt, fill=FG)
    pct_x = x + _LW + _G
    if pct is None:
        draw.text((pct_x, y), "N/A", font=fnt, fill=FG)
        return
    draw.text((pct_x, y), f"{min(100, max(0, int(pct * 100)))}% used", font=fnt, fill=FG)
    bar_x = pct_x + _PW + _G
    bar_y = y + (16 - _BH) // 2
    _draw_progress_bar(draw, bar_x, bar_y, _BW, _BH, pct)
    if reset_text:
        draw.text((bar_x + _BW + _G, y), reset_text, font=fnt, fill=FG)


def _draw_card_usage(draw: ImageDraw.ImageDraw, state: "AgentState") -> None:
    draw.rectangle(
        [(USAGE_X, USAGE_Y), (USAGE_X + USAGE_W - 1, USAGE_Y + USAGE_H - 1)],
        outline=FG, width=1,
    )
    ix, iy = USAGE_X + PAD, USAGE_Y + PAD
    iw = USAGE_W - 2 * PAD    # 243
    ih = USAGE_H - 2 * PAD    # 168

    content_h = 104
    sy = iy + max(0, (ih - content_h) // 2)

    _cx_text(draw, "Codex Usage", ix, iw, sy, _font(14, bold=True))
    _draw_usage_row(draw, ix, sy + 20, "5h",     state.codex_usage_5h,   state.codex_5h_reset)
    _draw_usage_row(draw, ix, sy + 40, "Weekly",  state.codex_usage_week, state.codex_weekly_reset)
    draw.line([(ix, sy + 60), (ix + iw - 1, sy + 60)], fill=FG, width=1)
    _cx_text(draw, "Claude Usage", ix, iw, sy + 68, _font(14, bold=True))
    _draw_usage_row(draw, ix, sy + 88, "5h", state.claude_usage_5h, state.claude_5h_reset)
