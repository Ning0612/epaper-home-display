from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.timezone import elapsed_seconds

PresenceState = Literal["OCCUPIED", "UNOCCUPIED", "UNKNOWN"]


def compute_presence(light_is_bright: bool) -> tuple[float, PresenceState]:
    """Pure function — safe to unit-test without any hardware.

    The parameter retains the legacy name used by the state/API. With this
    sensor circuit, ``True`` means the ADC is at/above the threshold (actual
    dark light), which is the leave/UNOCCUPIED signal.
    """
    if not light_is_bright:
        return 1.0, "OCCUPIED"
    return 0.0, "UNOCCUPIED"


@dataclass
class PresenceDebouncer:
    """Turn a raw light state into a stable presence state after a hold time."""

    state: PresenceState = "UNKNOWN"
    _candidate_state: PresenceState | None = None
    _candidate_since: datetime | None = None

    def reset(self, stable_state: PresenceState) -> None:
        """Sync with an external state change, such as the dashboard button."""
        self.state = stable_state
        self._candidate_state = None
        self._candidate_since = None

    def update(
        self,
        threshold_exceeded: bool | None,
        now: datetime,
        *,
        observed_since: datetime | None = None,
        unoccupied_after_seconds: int = 180,
        occupied_after_seconds: int = 30,
    ) -> tuple[float, PresenceState]:
        """Apply one sensor observation and return the current stable result.

        ``observed_since`` lets the caller preserve the timestamp of the sensor
        transition even though the presence loop is sampled less frequently.
        """
        if threshold_exceeded is None:
            # A failed read cannot prove that the candidate state persisted.
            self._candidate_state = None
            self._candidate_since = None
            return self._result()

        _, observed_state = compute_presence(threshold_exceeded)
        if observed_state == self.state:
            self._candidate_state = None
            self._candidate_since = None
            return self._result()

        if observed_state != self._candidate_state:
            self._candidate_state = observed_state
            self._candidate_since = observed_since or now
        elif observed_since is not None:
            self._candidate_since = observed_since

        threshold = (
            occupied_after_seconds
            if observed_state == "OCCUPIED"
            else unoccupied_after_seconds
        )
        threshold = max(0, threshold)
        if self._candidate_since is not None and elapsed_seconds(self._candidate_since, now) >= threshold:
            self.state = observed_state
            self._candidate_state = None
            self._candidate_since = None

        return self._result()

    def seconds_until_transition(
        self,
        now: datetime,
        *,
        unoccupied_after_seconds: int = 180,
        occupied_after_seconds: int = 30,
    ) -> int | None:
        """Return remaining hold time, or ``None`` when no transition is pending."""
        if self._candidate_state is None or self._candidate_since is None:
            return None
        threshold = (
            occupied_after_seconds
            if self._candidate_state == "OCCUPIED"
            else unoccupied_after_seconds
        )
        return max(0, max(0, threshold) - elapsed_seconds(self._candidate_since, now))

    def _result(self) -> tuple[float, PresenceState]:
        return (1.0 if self.state == "OCCUPIED" else 0.0), self.state
