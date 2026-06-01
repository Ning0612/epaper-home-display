from __future__ import annotations

from datetime import datetime
from typing import Any

from PIL import Image, ImageDraw

from app.display.renderer_constants import BG, DISPLAY_H, DISPLAY_W, FG, PAD
from app.display.renderer_utils import _cx_text, _font

_W = DISPLAY_W   # 800
_H = DISPLAY_H   # 480
_MX = 48         # horizontal margin for content blocks


def render_ap_mode_page(state: Any, settings: Any, now: datetime | None = None) -> Image.Image:
    """Render 800×480 AP mode setup page (L-mode grayscale).

    Displays AP SSID, password, and WebUI URL so the user can connect
    and configure WiFi via the browser portal.
    """
    if now is None:
        now = datetime.now()

    img = Image.new("L", (_W, _H), BG)
    draw = ImageDraw.Draw(img)

    _draw_header(draw)
    _draw_wifi_info(draw, state, settings)
    _draw_url_panel(draw, state, settings)
    _draw_footer(draw, now)

    return img


def _draw_header(draw: ImageDraw.ImageDraw) -> None:
    # Title
    _cx_text(draw, "WiFi  設定模式", 0, _W, 18, _font(28, bold=True))
    # Separator
    y_sep = 62
    draw.line([(PAD * 4, y_sep), (_W - PAD * 4, y_sep)], fill=FG, width=1)
    # Subtitle
    _cx_text(draw, "請先將手機或電腦連接以下 WiFi 熱點", 0, _W, 74, _font(14))


def _draw_wifi_info(draw: ImageDraw.ImageDraw, state: Any, settings: Any) -> None:
    ssid = state.ap_ssid or settings.wifi.ap_ssid
    password = state.ap_password or settings.wifi.ap_password

    block_w = _W - _MX * 2
    label_w = 100

    # SSID block
    _draw_info_block(draw, "SSID", ssid, _MX, 102, block_w, 60, label_w)
    # Password block
    _draw_info_block(draw, "密碼", password, _MX, 174, block_w, 60, label_w)

    # Separator
    draw.line([(PAD * 4, 248), (_W - PAD * 4, 248)], fill=FG, width=1)


def _draw_info_block(
    draw: ImageDraw.ImageDraw,
    label: str,
    value: str,
    x: int, y: int, w: int, h: int,
    label_w: int,
) -> None:
    # Outer border
    draw.rectangle([(x, y), (x + w - 1, y + h - 1)], outline=FG, width=1)
    # Vertical divider after label area
    draw.line([(x + label_w, y + 1), (x + label_w, y + h - 2)], fill=FG, width=1)

    text_y = y + (h - 22) // 2
    # Label (left, 18pt)
    _cx_text(draw, label, x + 4, label_w - 8, text_y, _font(18, bold=False))
    # Value (right, 24pt bold)
    value_x = x + label_w + 8
    value_w = w - label_w - 12
    _cx_text(draw, value, value_x, value_w, text_y - 2, _font(24, bold=True))


def _draw_url_panel(draw: ImageDraw.ImageDraw, state: Any, settings: Any) -> None:
    ip = state.ap_ip or "10.42.0.1"
    port = settings.webui.port
    url = f"http://{ip}:{port}/wifi"

    # Instruction label
    _cx_text(draw, "連線後，在瀏覽器開啟以下網址：", 0, _W, 258, _font(14))

    # URL box
    box_x = _MX
    box_y = 282
    box_w = _W - _MX * 2
    box_h = 56
    draw.rectangle([(box_x, box_y), (box_x + box_w - 1, box_y + box_h - 1)], outline=FG, width=2)

    url_y = box_y + (box_h - 26) // 2
    _cx_text(draw, url, box_x + 4, box_w - 8, url_y, _font(22, bold=True))

    # Separator
    draw.line([(PAD * 4, 352), (_W - PAD * 4, 352)], fill=FG, width=1)


def _draw_footer(draw: ImageDraw.ImageDraw, now: datetime) -> None:
    _cx_text(
        draw,
        "連線 WiFi 後此畫面將自動消失，裝置回到正常儀表板模式",
        0, _W, 362, _font(13),
    )
    _cx_text(
        draw,
        f"更新時間：{now.strftime('%H:%M')}",
        0, _W, 390, _font(14),
    )
