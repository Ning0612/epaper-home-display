from __future__ import annotations

RAIN_CODES = frozenset({
    200, 201, 202, 210, 211, 212, 221, 230, 231, 232,
    300, 301, 302, 310, 311, 312, 313, 314, 321,
    500, 501, 502, 503, 504, 511, 520, 521, 522, 531,
})
_RAIN_CODES = RAIN_CODES  # backwards-compat alias


def generate_reminder(
    weather_current: dict | None,
    weather_forecast: list[dict],
    temperature: float | None,
    humidity: float | None,
) -> str | None:
    """Return a reminder string, or None if nothing notable.

    Pure function — no I/O, no state.
    """
    reminders: list[str] = []

    # Rain in next ~8 h
    for entry in weather_forecast[:4]:
        code = entry.get("weather", [{}])[0].get("id", 0)
        if code in _RAIN_CODES:
            reminders.append("Rain expected — bring umbrella")
            break

    # Significant temperature drop
    current_temp = (weather_current or {}).get("main", {}).get("temp")
    if current_temp is not None and weather_forecast:
        future_temps = [
            e["main"]["temp"]
            for e in weather_forecast[:4]
            if isinstance(e.get("main", {}).get("temp"), (int, float))
        ]
        if future_temps and current_temp - min(future_temps) > 5:
            reminders.append("Temperature dropping — bring a jacket")

    # Indoor conditions
    if humidity is not None and humidity > 80:
        reminders.append("High indoor humidity — consider dehumidifier")
    if temperature is not None and temperature > 30:
        reminders.append("High indoor temperature — consider cooling")

    return "  |  ".join(reminders) if reminders else None
