"""The attempt loop: call the operation again while the policy allows it."""

from collections.abc import Callable

from ._policy import RetryPolicy


def retry[T](operation: Callable[[], T], *, policy: RetryPolicy) -> T:
    """Call ``operation`` until it returns or the policy says to stop.

    Each call happens inline in the caller's thread. When a call returns, its
    value is returned unchanged. When a call raises an exception that matches
    ``policy.retry_on`` and fewer than ``policy.max_attempts`` calls have been
    made, the operation is called again. Otherwise the exception propagates
    as the same object: an unlisted exception from the call that raised it,
    or a listed one from the last allowed call.
    """
    if not callable(operation):
        raise TypeError(f"operation must be callable; got {operation!r}")
    if not isinstance(policy, RetryPolicy):
        raise TypeError(f"policy must be a RetryPolicy; got {policy!r}")

    attempt = 1
    while True:
        try:
            return operation()
        except policy.retry_on:
            if attempt >= policy.max_attempts:
                raise
        attempt += 1
