"""Validated, reusable settings for synchronous retry calls."""

from collections.abc import Iterable
from dataclasses import dataclass
import math


def seconds(value: float, name: str) -> float:
    """Normalize a finite, nonnegative int/float duration, excluding bool."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number of seconds")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} must be finite") from error
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return result


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Limit total calls and select the exceptions that permit another call.

    ``attempts`` includes the first call. The supplied exception collection is
    copied, so later mutation by its owner cannot change this policy.
    """

    attempts: int = 1
    retry_on: Iterable[type[Exception]] = ()
    initial_delay: float = 0.0
    max_delay: float | None = None

    def __post_init__(self) -> None:
        if isinstance(self.attempts, bool) or not isinstance(self.attempts, int):
            raise TypeError("attempts must be an integer")
        if self.attempts < 1:
            raise ValueError("attempts must be at least one")
        try:
            exceptions = tuple(self.retry_on)
        except TypeError as error:
            raise TypeError("retry_on must be a collection of Exception classes") from error
        if any(not isinstance(cls, type) or not issubclass(cls, Exception) for cls in exceptions):
            raise TypeError("retry_on entries must be Exception classes")
        object.__setattr__(self, "retry_on", exceptions)
        initial = seconds(self.initial_delay, "initial_delay")
        maximum = None if self.max_delay is None else seconds(self.max_delay, "max_delay")
        if initial > 0 and maximum is None:
            raise ValueError("max_delay is required for a positive initial_delay")
        if maximum is not None and initial > maximum:
            raise ValueError("max_delay must be at least initial_delay")
        object.__setattr__(self, "initial_delay", initial)
        object.__setattr__(self, "max_delay", maximum)
