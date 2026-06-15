from app.logic.alarm_decision import compute_alarm_decision


def test_no_alert_returns_cancel():
    decision, reason = compute_alarm_decision("UNKNOWN", 0.0, None, None)
    assert decision == "CANCEL_ALARM"
    assert reason


def test_unoccupied_unknown_face_triggers_alarm():
    decision, reason = compute_alarm_decision(
        "UNOCCUPIED", 0.0, {"alert_type": "motion"}, None
    )
    assert decision == "TRIGGER_ALARM"
    assert "unoccupied" in reason.lower() or "unexpected" in reason.lower()


def test_unoccupied_with_known_face_no_action():
    decision, _ = compute_alarm_decision(
        "UNOCCUPIED", 0.0,
        {"alert_type": "face_detected"},
        {"identity": "lance", "known": True},
    )
    assert decision == "NO_ACTION"


def test_occupied_known_face_returns_cancel():
    decision, _ = compute_alarm_decision(
        "OCCUPIED", 3.0,
        {"alert_type": "door_open"},
        {"identity": "lance", "known": True},
    )
    assert decision == "CANCEL_ALARM"


def test_unknown_presence_triggers_alarm():
    decision, _ = compute_alarm_decision(
        "UNKNOWN", 1.0,
        {"alert_type": "sensor_trigger"},
        None,
    )
    assert decision == "TRIGGER_ALARM"  # UNKNOWN + no known face → treat as UNOCCUPIED path


def test_occupied_no_known_face_no_action():
    decision, _ = compute_alarm_decision(
        "OCCUPIED", 2.0,
        {"alert_type": "motion"},
        None,
    )
    assert decision == "NO_ACTION"
