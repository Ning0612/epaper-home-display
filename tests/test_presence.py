from app.logic.presence import compute_presence


def test_light_dark_is_occupied():
    score, state = compute_presence(False)
    assert state == "OCCUPIED"
    assert score == 1.0


def test_light_bright_is_unoccupied():
    score, state = compute_presence(True)
    assert state == "UNOCCUPIED"
    assert score == 0.0
