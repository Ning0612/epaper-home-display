from app.logic.door_reminder import generate_door_exit_text, _condition_zh, _format_weather_brief


def _make_forecast(weather_id: int = 800, temp: float = 22.0, pop: float = 0.0) -> dict:
    return {"weather": [{"id": weather_id}], "main": {"temp": temp}, "pop": pop}


def _make_current(temp: float = 22.0, feels_like: float | None = None, weather_id: int = 800) -> dict:
    return {
        "main": {"temp": temp, "feels_like": feels_like if feels_like is not None else temp},
        "weather": [{"id": weather_id}],
    }


# --- condition mapping ---

def test_condition_zh_clear():
    assert _condition_zh(800) == "晴天"

def test_condition_zh_few_clouds():
    assert _condition_zh(801) == "少雲"

def test_condition_zh_overcast():
    assert _condition_zh(804) == "陰天"

def test_condition_zh_rain():
    assert _condition_zh(500) == "下雨"

def test_condition_zh_thunderstorm():
    assert _condition_zh(211) == "雷雨"

def test_condition_zh_unknown_id():
    assert _condition_zh(999) == ""


# --- weather brief ---

def test_format_weather_brief_none_returns_none():
    assert _format_weather_brief(None) is None

def test_format_weather_brief_empty_dict_returns_none():
    assert _format_weather_brief({}) is None

def test_format_weather_brief_includes_temp_and_condition():
    result = _format_weather_brief(_make_current(22.0, weather_id=800))
    assert result is not None
    assert "22度" in result
    assert "晴天" in result

def test_format_weather_brief_rounds_temperature():
    result = _format_weather_brief(_make_current(22.7, weather_id=800))
    assert "23度" in result

def test_format_weather_brief_no_weather_field():
    result = _format_weather_brief({"main": {"temp": 25.0}})
    assert result is not None
    assert "25度" in result
    assert "晴天" not in result


# --- baseline ---

def test_no_data_returns_none():
    assert generate_door_exit_text(None, []) is None


def test_clear_weather_returns_brief():
    current = _make_current(22.0, weather_id=800)
    forecast = [_make_forecast(800, 22.0, 0.0)]
    result = generate_door_exit_text(current, forecast)
    assert result is not None
    assert "22度" in result
    assert "晴天" in result
    assert "雨傘" not in result


# --- rain ---

def test_rain_code_triggers_umbrella():
    forecast = [_make_forecast(500, 22.0)]
    result = generate_door_exit_text({}, forecast)
    assert result is not None
    assert "雨傘" in result


def test_high_pop_triggers_umbrella():
    forecast = [_make_forecast(800, 22.0, pop=0.8)]
    result = generate_door_exit_text({}, forecast)
    assert result is not None
    assert "雨傘" in result


def test_pop_at_threshold_triggers():
    forecast = [_make_forecast(800, 22.0, pop=0.6)]
    result = generate_door_exit_text({}, forecast)
    assert result is not None
    assert "雨傘" in result


def test_pop_below_threshold_no_umbrella():
    result = generate_door_exit_text(_make_current(22.0), [_make_forecast(800, 22.0, pop=0.5)])
    assert result is not None
    assert "雨傘" not in result
    assert "22度" in result  # brief is still included


# --- cold ---

def test_cold_feels_like_triggers_jacket():
    current = _make_current(temp=18.0, feels_like=12.0)
    result = generate_door_exit_text(current, [])
    assert result is not None
    assert "外套" in result
    assert "18度" in result


def test_warm_feels_like_no_jacket():
    current = _make_current(temp=20.0, feels_like=18.0)
    result = generate_door_exit_text(current, [])
    assert result is not None
    assert "外套" not in result
    assert "20度" in result


# --- hot ---

def test_hot_temp_triggers_sunscreen():
    current = _make_current(temp=33.0, feels_like=33.0)
    result = generate_door_exit_text(current, [])
    assert result is not None
    assert "防曬" in result
    assert "33度" in result


def test_borderline_hot_no_sunscreen():
    current = _make_current(temp=30.0, feels_like=30.0)
    result = generate_door_exit_text(current, [])
    assert result is not None
    assert "防曬" not in result
    assert "30度" in result


# --- temperature drop ---

def test_temp_drop_triggers_jacket():
    current = _make_current(temp=25.0, feels_like=25.0)
    forecast = [_make_forecast(800, temp=18.0)]
    result = generate_door_exit_text(current, forecast)
    assert result is not None
    assert "外套" in result
    assert "25度" in result


def test_small_temp_drop_no_reminder():
    current = _make_current(temp=25.0, feels_like=25.0)
    forecast = [_make_forecast(800, temp=22.0)]
    result = generate_door_exit_text(current, forecast)
    assert result is not None
    assert "外套" not in result
    assert "25度" in result


# --- combination ---

def test_rain_and_cold_combined():
    current = _make_current(temp=10.0, feels_like=8.0)
    forecast = [_make_forecast(500, temp=10.0)]
    result = generate_door_exit_text(current, forecast)
    assert result is not None
    assert "雨傘" in result
    assert "外套" in result
    assert "10度" in result


def test_max_two_conditions_output():
    """Rain + cold both triggered; temp-drop is bypassed by cold elif branch. Output has at most 2 warnings."""
    current = _make_current(temp=10.0, feels_like=8.0)
    forecast = [_make_forecast(500, temp=3.0, pop=0.9)]
    result = generate_door_exit_text(current, forecast)
    assert result is not None
    assert "雨傘" in result
    assert "外套" in result
    assert "防曬" not in result


# --- forecast window ---

def test_forecast_window_limited_to_4():
    """Rain only in slot index 5 (beyond window) must not trigger umbrella."""
    current = _make_current(22.0)
    forecast = [_make_forecast(800, 22.0)] * 5 + [_make_forecast(500, 22.0)]
    result = generate_door_exit_text(current, forecast)
    assert result is not None
    assert "雨傘" not in result
    assert "22度" in result


def test_rain_in_last_slot_of_window():
    current = _make_current(22.0)
    forecast = [_make_forecast(800, 22.0)] * 3 + [_make_forecast(500, 22.0)]
    result = generate_door_exit_text(current, forecast)
    assert result is not None
    assert "雨傘" in result
