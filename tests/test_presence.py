from datetime import datetime, timedelta

import pytest

from app.config import PresenceConfig
from app.logic.presence import compute_presence


@pytest.fixture
def cfg() -> PresenceConfig:
    return PresenceConfig()


def test_no_inputs_is_unoccupied(cfg):
    score, state = compute_presence(False, [], [], False, cfg)
    assert state == "UNOCCUPIED"
    assert score == 0.0


def test_light_alone_adds_score(cfg):
    score, _ = compute_presence(True, [], [], False, cfg)
    assert score == cfg.light_weight


def test_score_below_threshold_is_unoccupied(cfg):
    score, state = compute_presence(True, [], [], False, cfg)
    assert score < cfg.threshold
    assert state == "UNOCCUPIED"


def test_all_signals_occupied(cfg):
    now = datetime.now()
    doors = [{"timestamp": now.isoformat(), "state": "open"}]
    faces = [{"timestamp": now.isoformat(), "identity": "lance", "known": True}]
    score, state = compute_presence(True, doors, faces, False, cfg, now=now)
    assert state == "OCCUPIED"
    assert score >= cfg.threshold


def test_button_override_forces_occupied_regardless_of_score(cfg):
    _, state = compute_presence(False, [], [], True, cfg)
    assert state == "OCCUPIED"


def test_stale_door_event_ignored(cfg):
    stale_ts = (datetime.now() - timedelta(seconds=cfg.door_window_seconds + 60)).isoformat()
    doors = [{"timestamp": stale_ts, "state": "open"}]
    score, _ = compute_presence(False, doors, [], False, cfg)
    assert score == 0.0


def test_unknown_face_not_counted(cfg):
    now = datetime.now()
    faces = [{"timestamp": now.isoformat(), "identity": "stranger", "known": False}]
    score, _ = compute_presence(False, [], faces, False, cfg, now=now)
    assert score == 0.0


def test_known_face_adds_face_weight(cfg):
    now = datetime.now()
    faces = [{"timestamp": now.isoformat(), "identity": "lance", "known": True}]
    score, _ = compute_presence(False, [], faces, False, cfg, now=now)
    assert score == cfg.face_weight


def test_malformed_timestamp_treated_as_old(cfg):
    doors = [{"timestamp": "not-a-date", "state": "open"}]
    score, _ = compute_presence(False, doors, [], False, cfg)
    assert score == 0.0
