from datetime import datetime, timedelta, timezone

from app.logic.presence import PresenceDebouncer, compute_presence
from app.sensors.light_sensor import MockLightSensor


def test_bright_sensor_reading_is_occupied():
    score, state = compute_presence(False)
    assert state == "OCCUPIED"
    assert score == 1.0


def test_dark_sensor_reading_is_unoccupied():
    score, state = compute_presence(True)
    assert state == "UNOCCUPIED"
    assert score == 0.0


def test_threshold_equality_uses_existing_dark_side():
    sensor = MockLightSensor(raw=500)

    assert sensor.is_bright(500) is True
    assert compute_presence(sensor.is_bright(500))[1] == "UNOCCUPIED"


def test_dark_sensor_reading_requires_unoccupied_duration():
    debouncer = PresenceDebouncer()
    start = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)

    assert debouncer.update(True, start)[1] == "UNKNOWN"
    assert debouncer.update(True, start + timedelta(seconds=179))[1] == "UNKNOWN"
    assert debouncer.update(True, start + timedelta(seconds=180))[1] == "UNOCCUPIED"


def test_bright_sensor_reading_requires_occupied_duration():
    debouncer = PresenceDebouncer(state="UNOCCUPIED")
    start = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)

    assert debouncer.update(False, start)[1] == "UNOCCUPIED"
    assert debouncer.update(False, start + timedelta(seconds=29))[1] == "UNOCCUPIED"
    assert debouncer.update(False, start + timedelta(seconds=30))[1] == "OCCUPIED"


def test_presence_candidate_reversal_resets_timer():
    debouncer = PresenceDebouncer(state="OCCUPIED")
    start = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)

    assert debouncer.update(True, start)[1] == "OCCUPIED"
    assert debouncer.update(False, start + timedelta(seconds=120))[1] == "OCCUPIED"
    assert debouncer.update(True, start + timedelta(seconds=121))[1] == "OCCUPIED"
    assert debouncer.update(True, start + timedelta(seconds=301))[1] == "UNOCCUPIED"


def test_presence_duration_settings_override_defaults():
    debouncer = PresenceDebouncer(state="OCCUPIED")
    start = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)

    assert debouncer.update(True, start, unoccupied_after_seconds=10)[1] == "OCCUPIED"
    assert debouncer.update(True, start + timedelta(seconds=10), unoccupied_after_seconds=10)[1] == "UNOCCUPIED"


def test_observed_sensor_transition_time_is_used_for_debounce():
    debouncer = PresenceDebouncer(state="OCCUPIED")
    sensor_changed_at = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)

    assert debouncer.update(True, sensor_changed_at + timedelta(seconds=60), observed_since=sensor_changed_at)[1] == "OCCUPIED"
    assert debouncer.update(True, sensor_changed_at + timedelta(seconds=180), observed_since=sensor_changed_at)[1] == "UNOCCUPIED"


def test_missing_sensor_reading_does_not_create_presence():
    debouncer = PresenceDebouncer(state="OCCUPIED")
    now = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)

    assert debouncer.update(True, now)[1] == "OCCUPIED"
    assert debouncer.update(None, now + timedelta(seconds=60))[1] == "OCCUPIED"
    assert debouncer.update(True, now + timedelta(seconds=180))[1] == "OCCUPIED"
