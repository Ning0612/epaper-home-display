from app.state import AgentState


def test_default_values():
    s = AgentState()
    assert s.temperature is None
    assert s.humidity is None
    assert s.light_raw is None
    assert s.light_is_bright is False
    assert s.presence == "UNKNOWN"
    assert s.presence_score == 0.0
    assert s.weather_current is None
    assert s.weather_forecast == []
    assert s.weather_fetched_at is None
    assert s.last_door_event is None
    assert s.last_face_event is None
    assert s.last_alert is None
    assert s.security_status is None
    assert s.display_busy is False
    assert s.active_reminder is None
    assert s.started_at is not None


def test_fields_are_mutable():
    s = AgentState()
    s.temperature = 25.5
    s.presence = "OCCUPIED"
    assert s.temperature == 25.5
    assert s.presence == "OCCUPIED"


def test_stub_usage_fields_default_to_none():
    s = AgentState()
    assert s.custom_image_path is None
    assert s.claude_usage_5h is None
    assert s.claude_usage_week is None
    assert s.claude_5h_reset is None
    assert s.claude_7d_reset is None


def test_independent_instances_do_not_share_forecast():
    a = AgentState()
    b = AgentState()
    a.weather_forecast.append({"temp": 22})
    assert b.weather_forecast == []
