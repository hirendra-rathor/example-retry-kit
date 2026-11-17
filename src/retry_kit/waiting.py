"""Pure interval generation, independent of execution and sleeping."""

from collections.abc import Iterator

from .policy import RetryPolicy


def intervals(policy: RetryPolicy) -> Iterator[float]:
    """Yield capped doubling intervals from fresh invocation-local state."""
    delay = policy.initial_delay
    maximum = policy.max_delay if policy.max_delay is not None else 0.0
    while True:
        yield delay
        # A floating-point doubling may become infinity, but the finite cap
        # always bounds the yielded value. Zero remains zero even for tiny caps.
        delay = min(delay * 2, maximum)
