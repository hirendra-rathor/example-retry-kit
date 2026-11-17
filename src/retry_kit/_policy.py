"""The caller's retry choices, validated once and then fixed."""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, init=False)
class RetryPolicy:
    """Which exceptions justify another call and how many calls to allow.

    ``retry_on`` names the exception types that make it safe to call the
    operation again. A raised exception matches a listed type or any of its
    subclasses, as in an ``except`` clause. ``max_attempts`` counts every
    call, the first one included.

    A policy holds no per-call state, so one instance can be shared across
    calls and threads.
    """

    retry_on: tuple[type[Exception], ...]
    max_attempts: int

    def __init__(self, *, retry_on: Iterable[type[Exception]], max_attempts: int) -> None:
        object.__setattr__(self, "retry_on", _exception_types(retry_on))
        object.__setattr__(self, "max_attempts", _attempt_limit(max_attempts))


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
