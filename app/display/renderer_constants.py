from __future__ import annotations

DISPLAY_W, DISPLAY_H = 800, 480
BG = (255, 255, 255)
FG = (0, 0, 0)
COLOR_RED    = (255, 0,   0)
COLOR_ORANGE = (255, 128, 0)   # dithered approximation (red+yellow) — not a native e-paper color
COLOR_YELLOW = (255, 255, 0)
COLOR_GREEN  = (0,   255, 0)
COLOR_BLUE   = (0,   0,   255)
PAD = 8
MARGIN = 8

_CX = MARGIN
_CY = MARGIN
_CW = DISPLAY_W - 2 * MARGIN
_CH = DISPLAY_H - 2 * MARGIN
_GAP = 8

_LEFT_W = 480

WEATHER_X, WEATHER_Y = _CX, _CY
WEATHER_W, WEATHER_H = _LEFT_W, 340

IMAGE_X = _CX + _LEFT_W + _GAP
IMAGE_Y = _CY
IMAGE_W = (_CX + _CW) - IMAGE_X
IMAGE_H = _CH

ROW2_Y = WEATHER_Y + WEATHER_H + _GAP
ROW2_H = (_CY + _CH) - ROW2_Y

INDOOR_X, INDOOR_Y = _CX, ROW2_Y
INDOOR_W, INDOOR_H = 140, ROW2_H

USAGE_X = INDOOR_X + INDOOR_W + _GAP
USAGE_Y = ROW2_Y
USAGE_W = (_CX + _LEFT_W) - USAGE_X
USAGE_H = ROW2_H

_WX_TOP_H = 215

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_WEATHER_SEVERITY: dict[str, int] = {
    "Thunderstorm": 6, "Tornado": 6,
    "Snow": 5, "Sleet": 5,
    "Rain": 4, "Drizzle": 3,
    "Atmosphere": 2, "Mist": 2, "Fog": 2, "Haze": 2,
    "Clouds": 1, "Clear": 0,
}
