from app.logic.printer import format_remaining, parse_print_status


def test_parse_print_status_normal_complete_case():
    result = parse_print_status({
        "mc_percent": 42,
        "mc_remaining_time": 83,
        "subtask_name": "benchy_v2.3mf",
        "gcode_state": "running",
    })
    assert result is not None
    assert result.pct == 0.42
    assert result.remaining_min == 83
    assert result.task_name == "benchy_v2.3mf"
    assert result.gcode_state == "RUNNING"


def test_parse_print_status_empty_subtask_falls_back_to_gcode_file():
    result = parse_print_status({"subtask_name": "  ", "gcode_file": "fallback.3mf"})
    assert result is not None
    assert result.task_name == "fallback.3mf"


def test_parse_print_status_empty_task_names_return_none():
    result = parse_print_status({"subtask_name": "", "gcode_file": "  "})
    assert result is not None
    assert result.task_name is None


def test_parse_print_status_missing_field_does_not_drop_other_fields():
    result = parse_print_status({"mc_percent": 25, "gcode_state": "pause"})
    assert result is not None
    assert result.pct == 0.25
    assert result.remaining_min is None
    assert result.task_name is None
    assert result.gcode_state == "PAUSE"


def test_parse_print_status_rejects_bool_percent():
    result = parse_print_status({"mc_percent": True})
    assert result is not None
    assert result.pct is None


def test_parse_print_status_rejects_out_of_range_percent():
    assert parse_print_status({"mc_percent": -1}).pct is None
    assert parse_print_status({"mc_percent": 101}).pct is None


def test_parse_print_status_rejects_nan_and_infinite_percent():
    assert parse_print_status({"mc_percent": float("nan")}).pct is None
    assert parse_print_status({"mc_percent": float("inf")}).pct is None


def test_parse_print_status_rejects_huge_finite_percent():
    assert parse_print_status({"mc_percent": 1e308}).pct is None


def test_parse_print_status_rejects_negative_remaining_time():
    result = parse_print_status({"mc_remaining_time": -1})
    assert result is not None
    assert result.remaining_min is None


def test_parse_print_status_rejects_implausibly_large_remaining_time():
    result = parse_print_status({"mc_remaining_time": 10081})
    assert result is not None
    assert result.remaining_min is None


def test_parse_print_status_accepts_remaining_time_upper_bound():
    result = parse_print_status({"mc_remaining_time": 10080})
    assert result is not None
    assert result.remaining_min == 10080


def test_parse_print_status_rejects_too_long_task_name():
    result = parse_print_status({"subtask_name": "a" * 101, "gcode_file": "b" * 101})
    assert result is not None
    assert result.task_name is None


def test_parse_print_status_rejects_invalid_gcode_state_format():
    assert parse_print_status({"gcode_state": "RUNNING!"}).gcode_state is None
    assert parse_print_status({"gcode_state": "RUNNING123"}).gcode_state is None
    assert parse_print_status({"gcode_state": "A" * 33}).gcode_state is None
    assert parse_print_status({"gcode_state": 123}).gcode_state is None


def test_parse_print_status_accepts_unknown_valid_gcode_state():
    result = parse_print_status({"gcode_state": "new_future_state"})
    assert result is not None
    assert result.gcode_state == "NEW_FUTURE_STATE"


def test_parse_print_status_non_dict_returns_none():
    assert parse_print_status(None) is None
    assert parse_print_status([]) is None


def test_format_remaining_cases():
    assert format_remaining(0) == "0m"
    assert format_remaining(45) == "45m"
    assert format_remaining(60) == "1h00m"
    assert format_remaining(83) == "1h23m"
    assert format_remaining(125) == "2h05m"
    assert format_remaining(None) == "--"
    assert format_remaining(-1) == "--"
