from __future__ import annotations

import math

from app.logic.reminder import RAIN_CODES

_HIGH_RAIN_POP = 0.6
_COLD_FEELS_LIKE = 15.0
_HOT_TEMP = 30.0
_TEMP_DROP_THRESHOLD = 5.0
_FORECAST_WINDOW = 4   # 4 × 3 h ≈ next 12 hours


def _to_float(value: object) -> float | None:
    """Safely convert a value to float; return None on failure."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _condition_zh(weather_id: int) -> str:
    """Map an OWM weather condition ID to a short Chinese label."""
    if weather_id == 800:
        return "晴天"
    if 801 <= weather_id <= 802:
        return "少雲"
    if 803 <= weather_id <= 804:
        return "陰天"
    if 200 <= weather_id <= 232:
        return "雷雨"
    if 300 <= weather_id <= 321:
        return "毛毛雨"
    if 500 <= weather_id <= 531:
        return "下雨"
    if 600 <= weather_id <= 622:
        return "下雪"
    if 700 <= weather_id <= 781:
        return "霧霾"
    return ""


def _format_weather_brief(weather_current: dict | None) -> str | None:
    """Return a short summary like '現在 22度，晴天', or None if data is missing."""
    if not weather_current:
        return None
    main = weather_current.get("main", {})
    temp = _to_float(main.get("temp"))
    if temp is None:
        return None
    weather_list = weather_current.get("weather") or []
    w_id = weather_list[0].get("id") if weather_list else None
    condition = _condition_zh(int(w_id)) if w_id is not None else ""
    temp_str = f"現在 {math.floor(temp + 0.5)}度"  # half-up rounding
    return f"{temp_str}，{condition}" if condition else temp_str


def generate_door_exit_text(
    weather_current: dict | None,
    weather_forecast: list[dict],
) -> str | None:
    """Return a Chinese TTS string for someone about to leave, or None if no data.

    Pure function — no I/O, no state.
    Format: '[現在 X度，天氣][，warning1][，warning2]'
    At most 2 weather warnings; brief is always prepended when current data is available.
    Returns None only when weather_current is missing or has no temperature.
    """
    reminders: list[str] = []
    window = weather_forecast[:_FORECAST_WINDOW]

    # Priority 1: rain expected in next ~12 h
    rain_expected = any(
        entry.get("weather", [{}])[0].get("id", 0) in RAIN_CODES
        or (_to_float(entry.get("pop", 0)) or 0.0) >= _HIGH_RAIN_POP
        for entry in window
    )
    if rain_expected:
        reminders.append("記得帶雨傘")

    main = (weather_current or {}).get("main", {})
    current_temp = _to_float(main.get("temp"))
    feels_like = _to_float(main.get("feels_like"))

    # Priority 2: cold (feels_like < 15 °C)
    if feels_like is not None and feels_like < _COLD_FEELS_LIKE:
        reminders.append("今天比較冷，記得穿外套")
    # Priority 3: hot (temp > 30 °C)
    elif current_temp is not None and current_temp > _HOT_TEMP:
        reminders.append("外面很熱，注意防曬")
    # Priority 4: significant temperature drop coming
    elif current_temp is not None and window:
        future_temps = [
            v for e in window
            if (v := _to_float((e.get("main") or {}).get("temp"))) is not None
        ]
        if future_temps and current_temp - min(future_temps) > _TEMP_DROP_THRESHOLD:
            reminders.append("稍後溫度會下降，帶件外套")

    brief = _format_weather_brief(weather_current)
    if not brief and not reminders:
        return None  # no usable data; caller uses fallback text

    parts = ([brief] if brief else []) + reminders[:2]
    return "，".join(parts)
