from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from PIL import Image, ImageDraw

from app.display.renderer_constants import BG, DISPLAY_H, DISPLAY_W, FG, PAD
from app.display.renderer_utils import (
    _cx_text, _font, _paste_icon, _weather_item,
    fmt_door, fmt_face, fmt_alarm, _temp_color,
)

logger = logging.getLogger(__name__)

_SNAP_W = 640    # left panel width (QVGA 320×240 scaled 2×)
_SNAP_H = 480    # left panel height (= DISPLAY_H)
_INFO_X = 640    # right panel start X
_INFO_W = 160    # right panel width (= DISPLAY_W - _SNAP_W)


def render_alert_page(state: Any, settings: Any, now: datetime | None = None) -> Image.Image:
    """Render 800×480 alert page (RGB).

    Left 640px: camera snapshot scaled from QVGA, or a placeholder when no image is available.
    Right 160px: date, large clock, door/face/alert status.
    """
    if now is None:
        now = datetime.now()

    img = Image.new("RGB", (DISPLAY_W, DISPLAY_H), BG)
    draw = ImageDraw.Draw(img)
    _draw_snapshot_panel(img, draw, state)
    _draw_info_panel(img, draw, state, now)
    return img


def _draw_snapshot_panel(
    img: Image.Image, draw: ImageDraw.ImageDraw, state: Any
) -> None:
    snap: Any = state.last_snapshot_image
    if snap is not None:
        try:
            resized = snap.convert("RGB").resize((_SNAP_W, _SNAP_H), Image.Resampling.LANCZOS)
            img.paste(resized, (0, 0))
            return
        except Exception as exc:
            logger.warning("Alert snapshot render failed: %s", exc)

    # Placeholder when no image is available
    draw.rectangle([(0, 0), (_SNAP_W - 1, _SNAP_H - 1)], outline=FG, width=2)
    _cx_text(draw, "No Camera Feed", 0, _SNAP_W, (_SNAP_H - 28) // 2, _font(20, bold=True))


def _draw_info_panel(
    img: Image.Image, draw: ImageDraw.ImageDraw, state: Any, now: datetime
) -> None:
    ix = _INFO_X + PAD
    iw = _INFO_W - 2 * PAD
    y = PAD + 4

    # Date (small)
    _cx_text(draw, now.strftime("%m/%d"), ix, iw, y, _font(18, bold=True))
    y += 28

    # Time (large) — 44pt fits "HH:MM" (~120px) within 144px available
    _cx_text(draw, now.strftime("%H:%M"), ix, iw, y, _font(44, bold=True))
    y += 60

    # Separator
    draw.line([(ix, y), (ix + iw, y)], fill=FG, width=1)
    y += PAD + 2

    # Security state rows
    door = fmt_door(state.last_door_event)
    face = fmt_face(getattr(state, "alert_face_event", None))
    alarm = fmt_alarm(getattr(state, "last_alarm_decision", None))

    for label, val in [("D", door), ("F", face), ("A", alarm)]:
        _cx_text(draw, f"{label}:{val}", ix, iw, y, _font(14, bold=True))
        y += 24

    # Separator
    draw.line([(ix, y), (ix + iw, y)], fill=FG, width=1)
    y += PAD + 2

    _cx_text(draw, "!ALERT!", ix, iw, y, _font(16, bold=True))
    y += 24

    # --- Indoor ---
    draw.line([(ix, y), (ix + iw, y)], fill=FG, width=1)
    y += PAD + 2

    temp_str = f"{state.temperature:.1f}°" if state.temperature is not None else "--°"
    hum_str = f"{state.humidity:.0f}%" if state.humidity is not None else "--%"

    _cx_text(draw, "Indoor", ix, iw, y, _font(13, bold=True))
    y += 18
    _cx_text(draw, temp_str, ix, iw, y, _font(17, bold=True), fill=_temp_color(state.temperature))
    y += 24
    _cx_text(draw, hum_str, ix, iw, y, _font(14, bold=True))
    y += 20

    # --- Outdoor ---
    draw.line([(ix, y), (ix + iw, y)], fill=FG, width=1)
    y += PAD + 2

    wx = state.weather_current
    out_temp: float | None = None
    if wx:
        out_temp = wx.get("main", {}).get("temp")
        out_str = f"{out_temp:.0f}°" if out_temp is not None else "--°"
        wx_main = _weather_item(wx).get("main", "")
    else:
        out_str = "--°"
        wx_main = ""

    _cx_text(draw, "Outdoor", ix, iw, y, _font(13, bold=True))
    y += 18

    _ICON_SIZE = 36
    icon_x = ix + (iw - _ICON_SIZE) // 2
    if not _paste_icon(img, wx_main, _ICON_SIZE, icon_x, y):
        _cx_text(draw, wx_main[:5] or "--", ix, iw, y + 10, _font(13, bold=True))
    y += _ICON_SIZE + 4

    _cx_text(draw, out_str, ix, iw, y, _font(17, bold=True), fill=_temp_color(out_temp))

    # Vertical divider between panels
    draw.line([(_INFO_X, 0), (_INFO_X, DISPLAY_H - 1)], fill=FG, width=1)
