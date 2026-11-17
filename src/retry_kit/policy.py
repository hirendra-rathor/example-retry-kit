"""Validated, reusable settings for synchronous retry calls."""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Limit total calls and select the exceptions that permit another call.

    ``attempts`` includes the first call. The supplied exception collection is
    copied, so later mutation by its owner cannot change this policy.
    """

    attempts: int = 1
    retry_on: Iterable[type[Exception]] = ()

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
