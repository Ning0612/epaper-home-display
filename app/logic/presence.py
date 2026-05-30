from __future__ import annotations

from typing import Literal

PresenceState = Literal["OCCUPIED", "UNOCCUPIED", "UNKNOWN"]


def compute_presence(light_is_bright: bool) -> tuple[float, PresenceState]:
    """Pure function — safe to unit-test without any hardware.

    Strategy: desk/office use — light on means someone is home.
    """
    if light_is_bright:
        return 1.0, "OCCUPIED"
    return 0.0, "UNOCCUPIED"
