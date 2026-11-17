"""Elapsed-time admission, independent of callback execution and waiting."""

from collections.abc import Callable
import math


class Budget:
    """Observe one invocation using a finite, nondecreasing seconds clock."""

    def __init__(self, limit: float, clock: Callable[[], float]) -> None:
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._clock = clock
        self._limit = limit
        self._started = self._read()
        self._last = self._started

    def _read(self) -> float:
        value = self._clock()
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("clock must return numeric seconds")
        try:
            reading = float(value)
        except OverflowError as error:
            raise ValueError("clock reading must be finite") from error
        if not math.isfinite(reading):
            raise ValueError("clock reading must be finite")
        return reading

    def allows(self, delay: float = 0.0) -> bool:
        """Admit only a start strictly inside the elapsed limit.

        The caller passes the entire proposed wait, or zero for the check just
        before invoking a retry. Subtracting the origin avoids constructing an
        absolute deadline that could overflow or lose a small budget.
        """
        now = self._read()
        if now < self._last:
            raise ValueError("clock readings must be nondecreasing")
        self._last = now
        return now - self._started + delay < self._limit
