from __future__ import annotations

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


def generate_door_exit_text(
    weather_current: dict | None,
    weather_forecast: list[dict],
) -> str | None:
    """Return a Chinese TTS reminder string for someone about to leave, or None.

    Pure function — no I/O, no state.
    Combines at most 2 reminders in priority order.
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

    if not reminders:
        return None

    # Cap at 2 reminders and join
    return "，".join(reminders[:2])
