from __future__ import annotations

from typing import Literal

AlarmDecision = Literal["ALARM", "INVESTIGATE", "IGNORE"]


def compute_alarm_decision(
    presence_state: Literal["OCCUPIED", "UNOCCUPIED", "UNKNOWN"],
    presence_score: float,
    alert_payload: dict | None,
    last_known_face: dict | None,
) -> tuple[AlarmDecision, str]:
    """Return (decision, reason) for an incoming security alert.

    Pure function — safe to unit-test without hardware or network.
    """
    if alert_payload is None:
        return "IGNORE", "No alert payload"

    alert_type = alert_payload.get("type", "unknown")
    is_known = last_known_face is not None and bool(last_known_face.get("known"))

    if presence_state in ("UNOCCUPIED", "UNKNOWN") and not is_known:
        return "ALARM", f"Unexpected activity ({presence_state}): {alert_type}"

    if presence_state == "OCCUPIED" and is_known:
        return "IGNORE", f"Known user present during {alert_type}"

    return "INVESTIGATE", f"Uncertain state ({presence_state}, known={is_known}): {alert_type}"
