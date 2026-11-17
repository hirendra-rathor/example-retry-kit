"""The caller's retry choices, validated once and then fixed."""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True, init=False)
class RetryPolicy:
    """Which exceptions justify another call, how many calls to allow, and when to wait or stop.

    ``retry_on`` names the exception types that make it safe to call the
    operation again. A raised exception matches a listed type or any of its
    subclasses, as in an ``except`` clause. ``max_attempts`` counts every
    call, the first one included.

    ``initial_delay`` and ``max_delay`` are in seconds and are set together
    or not at all. When set, the wait before the first retry is
    ``initial_delay`` and each later wait doubles, capped at ``max_delay``.
    When unset, retries happen immediately.

    ``time_budget`` is in seconds and limits when retries may start: each
    retry() call's deadline is the clock reading at its first call plus the
    budget. When unset, there is no deadline.

    A policy holds no per-call state, so one instance can be shared across
    calls and threads.
    """

    retry_on: tuple[type[Exception], ...]
    max_attempts: int
    initial_delay: float | None
    max_delay: float | None
    time_budget: float | None

    def __init__(
        self,
        *,
        retry_on: Iterable[type[Exception]],
        max_attempts: int,
        initial_delay: float | None = None,
        max_delay: float | None = None,
        time_budget: float | None = None,
    ) -> None:
        object.__setattr__(self, "retry_on", _exception_types(retry_on))
        object.__setattr__(self, "max_attempts", _attempt_limit(max_attempts))
        initial, maximum = _delays(initial_delay, max_delay)
        object.__setattr__(self, "initial_delay", initial)
        object.__setattr__(self, "max_delay", maximum)
        object.__setattr__(self, "time_budget", _budget(time_budget))


def _exception_types(retry_on: Iterable[type[Exception]]) -> tuple[type[Exception], ...]:
    if isinstance(retry_on, (type, str, bytes)):
        raise TypeError(
            "retry_on must be a collection of exception types, such as [ReportNotReady]; "
            f"got {retry_on!r}"
        )
    try:
        types = tuple(retry_on)
    except TypeError:
        raise TypeError(
            f"retry_on must be a collection of exception types; got {retry_on!r}"
        ) from None
    if not types:
        raise ValueError("retry_on must name at least one exception type")
    for entry in types:
        if not (isinstance(entry, type) and issubclass(entry, Exception)):
            raise TypeError(f"retry_on entries must be Exception subclasses; got {entry!r}")
    return types


def _attempt_limit(max_attempts: int) -> int:
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        raise TypeError(f"max_attempts must be an int; got {max_attempts!r}")
    if max_attempts < 1:
        raise ValueError(
            f"max_attempts must be at least 1 because the first call counts; got {max_attempts}"
        )
    return max_attempts


def _delays(
    initial_delay: float | None, max_delay: float | None
) -> tuple[float | None, float | None]:
    if initial_delay is None and max_delay is None:
        return None, None
    if initial_delay is None:
        raise ValueError(
            "max_delay has no effect without initial_delay; "
            "set both, or leave both unset for immediate retries"
        )
    if max_delay is None:
        raise ValueError("initial_delay needs a max_delay to cap the doubling waits")
    initial = _seconds("initial_delay", initial_delay)
    maximum = _seconds("max_delay", max_delay)
    if initial <= 0:
        raise ValueError(
            f"initial_delay must be greater than 0; got {initial_delay!r} "
            "(leave it unset for immediate retries)"
        )
    if maximum < initial:
        raise ValueError(
            f"max_delay must be at least initial_delay; got {max_delay!r} < {initial_delay!r}"
        )
    return initial, maximum


def _budget(time_budget: float | None) -> float | None:
    if time_budget is None:
        return None
    seconds = _seconds("time_budget", time_budget)
    if seconds <= 0:
        raise ValueError(
            f"time_budget must be greater than 0; got {time_budget!r} (leave it unset for no deadline)"
        )
    return seconds


def _seconds(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a number of seconds; got {value!r}")
    seconds = float(value)
    if not math.isfinite(seconds):
        raise ValueError(f"{name} must be finite; got {value!r}")
    return seconds
