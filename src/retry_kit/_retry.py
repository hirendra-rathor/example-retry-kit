"""The attempt loop: call the operation again while the policy allows it."""

import time
from collections.abc import Callable

from ._policy import RetryPolicy
from ._schedule import waits


def retry[T](
    operation: Callable[[], T],
    *,
    policy: RetryPolicy,
    sleep: Callable[[float], object] = time.sleep,
) -> T:
    """Call ``operation`` until it returns or the policy says to stop.

    Each call happens inline in the caller's thread, the first one at once.
    When a call returns, its value is returned unchanged. When a call raises
    an exception that matches ``policy.retry_on`` and fewer than
    ``policy.max_attempts`` calls have been made, the operation is called
    again, after ``sleep(seconds)`` if the policy sets a delay. Otherwise the
    exception propagates as the same object, without a wait: an unlisted
    exception from the call that raised it, or a listed one from the last
    allowed call.

    ``sleep`` is ``time.sleep`` unless the caller supplies another function,
    such as a recorder in a test.
    """
    if not callable(operation):
        raise TypeError(f"operation must be callable; got {operation!r}")
    if not isinstance(policy, RetryPolicy):
        raise TypeError(f"policy must be a RetryPolicy; got {policy!r}")
    if not callable(sleep):
        raise TypeError(f"sleep must be callable; got {sleep!r}")

    schedule = (
        waits(policy.initial_delay, policy.max_delay)
        if policy.initial_delay is not None and policy.max_delay is not None
        else None
    )
    attempt = 1
    while True:
        try:
            return operation()
        except policy.retry_on:
            if attempt >= policy.max_attempts:
                raise
        # Wait outside the except block so the failed attempt's exception
        # is not held, or chained to anything raised, during the wait.
        if schedule is not None:
            sleep(next(schedule))
        attempt += 1
