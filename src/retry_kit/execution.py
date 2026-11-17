"""Invoke a caller-owned operation under a validated retry policy."""

from collections.abc import Callable
from time import monotonic, sleep
from typing import TypeVar

from .budget import Budget
from .policy import RetryPolicy
from .waiting import intervals

T = TypeVar("T")


def retry(
    operation: Callable[[], T],
    *,
    policy: RetryPolicy = RetryPolicy(),
    wait: Callable[[float], None] = sleep,
    clock: Callable[[], float] = monotonic,
) -> T:
    """Return the first success, or propagate an operation's original failure.

    Only failures selected by ``policy.retry_on`` can cause another call. The
    caller remains responsible for making repetition safe and bounding the
    duration of an individual call.

    An enabled time budget gates retries before and after their full wait. It
    never interrupts a running call or discards a successful result. Disabled
    budgets do not read the clock. Clock and waiting failures escape directly.
    """
    if not callable(operation):
        raise TypeError("operation must be callable")
    if not callable(wait):
        raise TypeError("wait must be callable")
    schedule = intervals(policy)
    budget = None if policy.time_budget is None else Budget(policy.time_budget, clock)
    for attempt in range(1, policy.attempts + 1):
        try:
            return operation()
        except policy.retry_on:
            if attempt == policy.attempts:
                raise
            delay = next(schedule)
            if budget is not None and not budget.allows(delay):
                raise
            if delay > 0:
                wait(delay)
            if budget is not None and not budget.allows():
                raise
    raise AssertionError("a validated policy always permits at least one attempt")
