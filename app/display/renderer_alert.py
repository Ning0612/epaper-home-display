from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from PIL import Image, ImageDraw

from app.display.renderer_constants import BG, DISPLAY_H, DISPLAY_W, FG, PAD
from app.display.renderer_utils import _cx_text, _font, fmt_door, fmt_face, fmt_alarm

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
    _draw_info_panel(draw, state, now)
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


def _draw_info_panel(draw: ImageDraw.ImageDraw, state: Any, now: datetime) -> None:
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

    # Vertical divider between panels
    draw.line([(_INFO_X, 0), (_INFO_X, DISPLAY_H - 1)], fill=FG, width=1)
