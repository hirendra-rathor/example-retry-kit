"""The attempt loop: call the operation again while the policy allows it."""

import time
from collections.abc import Callable

from ._deadline import Deadline
from ._policy import RetryPolicy
from ._schedule import waits


def retry[T](
    operation: Callable[[], T],
    *,
    policy: RetryPolicy,
    sleep: Callable[[float], object] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> T:
    """Call ``operation`` until it returns or the policy says to stop.

    Each call happens inline in the caller's thread, the first one at once.
    When a call returns, its value is returned unchanged, even if it finishes
    after the policy's deadline. When a call raises an exception that matches
    ``policy.retry_on`` and fewer than ``policy.max_attempts`` calls have been
    made, the operation is called again, after ``sleep(seconds)`` if the
    policy sets a delay.

    With a ``policy.time_budget``, the deadline is the ``clock()`` reading
    just before the first call plus the budget. A retry is not started if
    the full wait would bring it to or past the deadline, or if, after the
    wait, the deadline has been reached.

    Whenever the loop stops after a listed exception, that exception
    propagates as the same object, without a further wait. An unlisted
    exception propagates from the call that raised it.

    ``sleep`` and ``clock`` are ``time.sleep`` and ``time.monotonic`` unless
    the caller supplies others, such as a controlled clock in a test.
    """
    if not callable(operation):
        raise TypeError(f"operation must be callable; got {operation!r}")
    if not isinstance(policy, RetryPolicy):
        raise TypeError(f"policy must be a RetryPolicy; got {policy!r}")
    if not callable(sleep):
        raise TypeError(f"sleep must be callable; got {sleep!r}")
    if not callable(clock):
        raise TypeError(f"clock must be callable; got {clock!r}")

    schedule = (
        waits(policy.initial_delay, policy.max_delay)
        if policy.initial_delay is not None and policy.max_delay is not None
        else None
    )
    deadline = Deadline(policy.time_budget, clock)
    attempt = 1
    while True:
        try:
            return operation()
        except policy.retry_on as error:
            if attempt >= policy.max_attempts:
                raise
            failure: BaseException | None = error
        # Decide outside the except block, so nothing raised during the wait
        # is chained to the failed attempt. The failure is kept through the
        # wait in case time runs out, then released before the next call.
        wait = next(schedule) if schedule is not None else 0.0
        try:
            if not deadline.allows_wait(wait):
                raise failure
            if schedule is not None:
                sleep(wait)
                if not deadline.allows_start():
                    raise failure
        finally:
            failure = None
        attempt += 1
