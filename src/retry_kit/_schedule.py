"""The wait before each retry: start at the initial delay, double, then cap."""

from collections.abc import Iterator


def waits(initial: float, maximum: float) -> Iterator[float]:
    """Yield the wait before each retry, in order, without end.

    The first wait is ``initial``. Each later wait doubles the previous one
    and is capped at ``maximum``. Doubling a float is exact, so the waits for
    0.1 and 0.25 are exactly 0.1, 0.2, 0.25, 0.25, ...
    """
    wait = initial
    while True:
        yield wait
        wait = min(wait * 2, maximum)
