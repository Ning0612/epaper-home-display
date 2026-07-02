from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

from app.display.renderer_constants import (
    FG, PAD,
    WEATHER_X, WEATHER_Y, WEATHER_W, WEATHER_H,
    IMAGE_X, IMAGE_Y, IMAGE_W, IMAGE_H,
    INDOOR_X, INDOOR_Y, INDOOR_W, INDOOR_H,
    USAGE_X, USAGE_Y, USAGE_W, USAGE_H,
    HYDRA_X, HYDRA_Y, HYDRA_W, HYDRA_H,
    _WX_TOP_H, _WEEKDAYS,
)
from app.display.renderer_utils import (
    _font, _cx_text, _paste_icon, _draw_progress_bar,
    _pick_daily_forecast, _weather_item, _temp_color, _usage_color,
)

if TYPE_CHECKING:
    from app.config import Settings
    from app.state import AgentState

logger = logging.getLogger(__name__)

_STALE_FILL = (160, 160, 160)


def _draw_card_weather(
    img: Image.Image, draw: ImageDraw.ImageDraw, state: "AgentState", now: datetime,
    *, color: bool = True,
) -> None:
    draw.rectangle(
        [(WEATHER_X, WEATHER_Y), (WEATHER_X + WEATHER_W - 1, WEATHER_Y + WEATHER_H - 1)],
        outline=FG, width=1,
    )

    ix = WEATHER_X + PAD
    iy = WEATHER_Y + PAD
    inner_w = WEATHER_W - 2 * PAD

    dt_top = iy + (_WX_TOP_H - 206) // 2

    date_str = now.strftime("%Y/%m/%d %A")
    _cx_text(draw, date_str, ix, inner_w, dt_top, _font(36, bold=True))

    time_str = now.strftime("%H:%M")
    _cx_text(draw, time_str, ix, inner_w, dt_top + 46, _font(160, bold=True))

    div_y = WEATHER_Y + PAD + _WX_TOP_H
    draw.line([(WEATHER_X + 1, div_y), (WEATHER_X + WEATHER_W - 2, div_y)], fill=FG, width=1)

    now_w = 80
    fc_gap = 12
    daily_w = (inner_w - now_w - fc_gap) // 4

    fc_y0 = div_y + PAD + 4

    LBL = 0
    ICO = 20
    TMP = 60
    POP = 80

    now_x = ix
    wi = _weather_item(state.weather_current or {})
    now_main = wi.get("main", "")
    now_temp = (state.weather_current.get("main", {}).get("temp")
                if state.weather_current else None)

    _cx_text(draw, "Now", now_x, now_w, fc_y0 + LBL, _font(16, bold=True))

    icon_x = now_x + (now_w - 36) // 2
    if not _paste_icon(img, now_main, 36, icon_x, fc_y0 + ICO):
        _cx_text(draw, now_main[:4], now_x, now_w, fc_y0 + ICO + 10, _font(14, bold=True))

    now_temp_str = f"{now_temp:.0f}°" if isinstance(now_temp, (int, float)) else "--"
    _cx_text(draw, now_temp_str, now_x, now_w, fc_y0 + TMP, _font(18, bold=True), fill=_temp_color(now_temp, color))

    sep_x = ix + now_w + fc_gap // 2
    fc_bottom = WEATHER_Y + WEATHER_H - PAD
    y_sep = fc_y0
    while y_sep < fc_bottom:
        draw.point((sep_x, y_sep), fill=FG)
        y_sep += 3

    daily_x0 = ix + now_w + fc_gap
    fc_entries = _pick_daily_forecast(state.weather_forecast, 4)

    for i, entry in enumerate(fc_entries[:4]):
        col_x = daily_x0 + i * daily_w

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
        _cx_text(draw, fc_temp_str, col_x, daily_w, fc_y0 + TMP, _font(18, bold=True), fill=_temp_color(fc_temp, color))

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
            if custom.size == (iw, ih) and custom.mode == "RGB":
                # Pre-processed display PNG (280×448 RGB) — paste directly
                img.paste(custom, (ix, iy))
            else:
                # Legacy path: arbitrary image — convert and thumbnail
                custom = custom.convert("RGB")
                custom.thumbnail((iw, ih), Image.Resampling.LANCZOS)
                px = ix + (iw - custom.width) // 2
                py = iy + (ih - custom.height) // 2
                img.paste(custom, (px, py))
    except (OSError, IOError) as e:
        logger.warning("custom image load failed: %s", e)
        draw.text((ix + 4, iy + 4), "Image Error", font=_font(16, bold=True), fill=FG)


def _draw_card_indoor(draw: ImageDraw.ImageDraw, state: "AgentState", *, color: bool = True) -> None:
    draw.rectangle(
        [(INDOOR_X, INDOOR_Y), (INDOOR_X + INDOOR_W - 1, INDOOR_Y + INDOOR_H - 1)],
        outline=FG, width=1,
    )
    ix, iy = INDOOR_X + PAD, INDOOR_Y + PAD
    iw = INDOOR_W - 2 * PAD
    ih = INDOOR_H - 2 * PAD

    temp_str = f"{state.temperature:.1f}°" if state.temperature is not None else "--°"
    hum_str = f"{state.humidity:.0f}%" if state.humidity is not None else "--%"
    mode_map = {"OCCUPIED": "HOME", "UNOCCUPIED": "AWAY", "UNKNOWN": "?"}
    mode_str = mode_map.get(state.presence, state.presence[:6])

    content_h = 14 + 5 + 17 + 5 + 17 + 5 + 14
    sy = iy + max(0, (ih - content_h) // 2)

    _cx_text(draw, "Indoor", ix, iw, sy, _font(14, bold=True))
    _cx_text(draw, temp_str, ix, iw, sy + 19, _font(17, bold=True), fill=_temp_color(state.temperature, color))
    _cx_text(draw, hum_str, ix, iw, sy + 41, _font(17, bold=True))
    _cx_text(draw, mode_str, ix, iw, sy + 63, _font(14, bold=True))


def _draw_usage_row(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    pct: float | None,
    reset_text: str | None,
    row_w: int = 190,
    fixed_reset_w: int | None = None,
    *,
    color: bool = True,
) -> None:
    _G, _PW, _BH = 4, 36, 11
    fnt = _font(13, bold=True)
    _bb = draw.textbbox((0, 0), label, font=fnt)
    _LW = _bb[2] - _bb[0]
    bar_color = _usage_color(pct, color)
    draw.text((x, y), label, font=fnt, fill=FG)
    pct_x = x + _LW + _G
    if pct is None:
        draw.text((pct_x, y), "N/A", font=fnt, fill=FG)
        return
    draw.text((pct_x, y), f"{min(100, max(0, int(pct * 100)))}%", font=fnt, fill=FG)
    bar_x = pct_x + _PW + _G
    bar_y = y + (16 - _BH) // 2
    if fixed_reset_w is not None:
        _RW = fixed_reset_w
    elif reset_text:
        _rb = draw.textbbox((0, 0), reset_text, font=fnt)
        _RW = _rb[2] - _rb[0] + _G
    else:
        _RW = 0
    _BW = max(10, row_w - (_LW + _G + _PW + _G) - _RW)
    _draw_progress_bar(draw, bar_x, bar_y, _BW, _BH, pct, fill=bar_color)
    if reset_text:
        draw.text((bar_x + _BW + _G, y), reset_text, font=fnt, fill=FG)


def _draw_card_usage(draw: ImageDraw.ImageDraw, state: "AgentState", *, color: bool = True) -> None:
    draw.rectangle(
        [(USAGE_X, USAGE_Y), (USAGE_X + USAGE_W - 1, USAGE_Y + USAGE_H - 1)],
        outline=FG, width=1,
    )
    ix, iy = USAGE_X + PAD, USAGE_Y + PAD
    iw = USAGE_W - 2 * PAD
    ih = USAGE_H - 2 * PAD

    # Claude section (y+0..y+47) + separator + Codex section (y+52..y+83)
    content_h = 99
    sy = iy + max(0, (ih - content_h) // 2)

    # Pre-compute widest reset text so all four bars share the same length
    _fnt = _font(13, bold=True)
    _gap = 4
    _all_resets = [
        state.claude_5h_reset or "--:--",
        state.claude_7d_reset or "--:--",
        state.codex_5h_reset  or "--:--",
        state.codex_7d_reset  or "--:--",
    ]
    _max_rw = max(
        draw.textbbox((0, 0), t, font=_fnt)[2] - draw.textbbox((0, 0), t, font=_fnt)[0]
        for t in _all_resets
    ) + _gap

    _cx_text(draw, "Claude", ix, iw, sy, _font(13, bold=True))
    _draw_usage_row(draw, ix, sy + 16, "5h", state.claude_usage_5h, state.claude_5h_reset, iw, _max_rw, color=color)
    _draw_usage_row(draw, ix, sy + 32, "7d", state.claude_usage_week, state.claude_7d_reset, iw, _max_rw, color=color)

    sep_y = sy + 49
    draw.line([(ix, sep_y), (ix + iw - 1, sep_y)], fill=FG, width=1)

    _cx_text(draw, "Codex", ix, iw, sep_y + 3, _font(13, bold=True))
    _draw_usage_row(draw, ix, sep_y + 19, "5h", state.codex_usage_5h, state.codex_5h_reset, iw, _max_rw, color=color)
    _draw_usage_row(draw, ix, sep_y + 35, "7d", state.codex_usage_week, state.codex_7d_reset, iw, _max_rw, color=color)


def _draw_card_hydra(
    draw: ImageDraw.ImageDraw,
    state: "AgentState",
    settings: "Settings",
    *,
    color: bool = True,
) -> None:
    draw.rectangle(
        [(HYDRA_X, HYDRA_Y), (HYDRA_X + HYDRA_W - 1, HYDRA_Y + HYDRA_H - 1)],
        outline=FG, width=1,
    )
    ix, iy = HYDRA_X + PAD, HYDRA_Y + PAD
    iw = HYDRA_W - 2 * PAD
    ih = HYDRA_H - 2 * PAD

    updated_at = state.hydra_updated_at
    is_stale = False
    if updated_at is not None:
        now = datetime.now(updated_at.tzinfo) if updated_at.tzinfo is not None else datetime.now()
        is_stale = (now - updated_at).total_seconds() > settings.mqtt.heartbeat_timeout_sec
    muted = is_stale or not state.hydra_device_online or state.hydra_current_ml is None
    fill = _STALE_FILL if muted else FG
    bar_fill = _STALE_FILL if muted else (0, 0, 255) if color else FG

    if state.hydra_current_ml is None or state.hydra_goal_ml is None:
        amount_str = "--/--ml"
    else:
        amount_str = f"{state.hydra_current_ml}/{state.hydra_goal_ml}ml"
    pct = state.hydra_pct
    pct_str = "--%" if pct is None else f"{max(0, min(100, int(round(pct * 100))))}%"

    content_h = 14 + 5 + 16 + 5 + 20 + 7 + 12
    sy = iy + max(0, (ih - content_h) // 2)

    _cx_text(draw, "Water", ix, iw, sy, _font(14, bold=True), fill=fill)
    _cx_text(draw, amount_str, ix, iw, sy + 19, _font(16, bold=True), fill=fill)
    _cx_text(draw, pct_str, ix, iw, sy + 40, _font(20, bold=True), fill=fill)
    _draw_progress_bar(draw, ix + 4, sy + 67, iw - 8, 12, pct or 0.0, fill=bar_fill)
