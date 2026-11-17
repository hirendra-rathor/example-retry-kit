"""The caller's time budget for starting retries, fixed at the first call."""

from collections.abc import Callable


class Deadline:
    """Answer whether there is still time to wait for, and start, a retry.

    The deadline is the clock reading taken when the Deadline is created,
    just before the first call, plus the budget. It never moves. A retry may
    start only strictly before it. Without a budget every answer is yes and
    the clock is never read.
    """

    __slots__ = ("_clock", "_at")

    def __init__(self, budget: float | None, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._at = None if budget is None else clock() + budget

    def allows_wait(self, seconds: float) -> bool:
        """Whether a retry after a full wait of ``seconds`` would start before the deadline."""
        return self._at is None or self._clock() + seconds < self._at

    def allows_start(self) -> bool:
        """Whether a retry starting now would start before the deadline."""
        return self._at is None or self._clock() < self._at
