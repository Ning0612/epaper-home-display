from __future__ import annotations

from typing import Literal

AlarmDecision = Literal["TRIGGER_ALARM", "NO_ACTION", "CANCEL_ALARM"]


def compute_alarm_decision(
    presence_state: Literal["OCCUPIED", "UNOCCUPIED", "UNKNOWN"],
    presence_score: float,
    alert_payload: dict | None,
    last_known_face: dict | None,
) -> tuple[AlarmDecision, str]:
    """Return (decision, reason) for an incoming security alert.

    Values match the FaceGuard home/home_state/alarm_decision protocol:
      TRIGGER_ALARM  — unknown/unoccupied, trigger immediately
      CANCEL_ALARM   — known user confirmed, safe to dismiss
      NO_ACTION      — uncertain; let FaceGuard's 30s timeout decide

    Pure function — safe to unit-test without hardware or network.
    """
    if alert_payload is None:
        return "CANCEL_ALARM", "No alert payload"

    alert_type = alert_payload.get("alert_type", "unknown")
    is_known = last_known_face is not None and bool(last_known_face.get("known"))

    if presence_state in ("UNOCCUPIED", "UNKNOWN") and not is_known:
        return "TRIGGER_ALARM", f"Unexpected activity ({presence_state}): {alert_type}"

    if presence_state == "OCCUPIED" and is_known:
        return "CANCEL_ALARM", f"Known user present during {alert_type}"

    return "NO_ACTION", f"Uncertain state ({presence_state}, known={is_known}): {alert_type}"
