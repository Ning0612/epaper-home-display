from app.logic.reminder import generate_reminder


def test_no_data_returns_none():
    assert generate_reminder(None, [], None, None) is None


def test_rain_code_triggers_umbrella():
    forecast = [{"weather": [{"id": 500}], "main": {"temp": 22.0}}]
    result = generate_reminder({}, forecast, 25.0, 50.0)
    assert result is not None
    assert "umbrella" in result.lower()


def test_non_rain_code_no_umbrella():
    forecast = [{"weather": [{"id": 800}], "main": {"temp": 22.0}}]
    result = generate_reminder({"main": {"temp": 22.0}}, forecast, 25.0, 50.0)
    assert result is None


def test_temperature_drop_triggers_jacket():
    current = {"main": {"temp": 25.0}}
    forecast = [{"weather": [{"id": 800}], "main": {"temp": 15.0}}]
    result = generate_reminder(current, forecast, 25.0, 50.0)
    assert result is not None
    assert "jacket" in result.lower()


def test_small_temperature_drop_no_reminder():
    current = {"main": {"temp": 25.0}}
    forecast = [{"weather": [{"id": 800}], "main": {"temp": 22.0}}]
    result = generate_reminder(current, forecast, 25.0, 50.0)
    assert result is None


def test_high_indoor_humidity_triggers_reminder():
    result = generate_reminder({}, [], 26.0, 85.0)
    assert result is not None
    assert "humid" in result.lower()


def test_normal_humidity_no_reminder():
    result = generate_reminder({}, [], 26.0, 60.0)
    assert result is None


def test_high_indoor_temp_triggers_reminder():
    result = generate_reminder({}, [], 32.0, 50.0)
    assert result is not None


def test_multiple_conditions_joined():
    forecast = [{"weather": [{"id": 500}], "main": {"temp": 22.0}}]
    result = generate_reminder({}, forecast, 32.0, 85.0)
    assert result is not None
    assert "|" in result
