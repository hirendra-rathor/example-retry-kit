"""Invoke a caller-owned operation under a validated retry policy."""

from collections.abc import Callable
from typing import TypeVar

from .policy import RetryPolicy

T = TypeVar("T")


def retry(operation: Callable[[], T], *, policy: RetryPolicy = RetryPolicy()) -> T:
    """Return the first success, or propagate an operation's original failure.

    Only failures selected by ``policy.retry_on`` can cause another call. The
    caller remains responsible for making repetition safe and bounding the
    duration of an individual call.
    """
    if not callable(operation):
        raise TypeError("operation must be callable")
    for attempt in range(1, policy.attempts + 1):
        try:
            return operation()
        except policy.retry_on:
            if attempt == policy.attempts:
                raise
    raise AssertionError("a validated policy always permits at least one attempt")
