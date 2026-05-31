from __future__ import annotations

from typing import Literal

PresenceState = Literal["OCCUPIED", "UNOCCUPIED", "UNKNOWN"]


def compute_presence(light_is_bright: bool) -> tuple[float, PresenceState]:
    """Pure function — safe to unit-test without any hardware.

    Strategy: desk/office use — ambient light below threshold means someone is home
    (room lamp creates low ambient reading; bright daylight means nobody is inside).
    """
    if not light_is_bright:
        return 1.0, "OCCUPIED"
    return 0.0, "UNOCCUPIED"
