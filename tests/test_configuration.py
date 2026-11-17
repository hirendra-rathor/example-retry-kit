"""Policy checks protect the boundary before caller work begins."""

from dataclasses import FrozenInstanceError

import pytest

from retry_kit import RetryPolicy


@pytest.mark.parametrize("attempts", [True, False, 1.5, "3", None])
def test_attempts_must_be_an_integer(attempts):
    with pytest.raises(TypeError, match="attempts"):
        RetryPolicy(attempts=attempts)


@pytest.mark.parametrize("attempts", [0, -1])
def test_attempts_must_allow_the_initial_call(attempts):
    with pytest.raises(ValueError, match="attempts"):
        RetryPolicy(attempts=attempts)


@pytest.mark.parametrize("exceptions", [None, ValueError, [ValueError()], [str], [BaseException], [KeyboardInterrupt], [SystemExit]])
def test_retry_on_contains_only_ordinary_exception_classes(exceptions):
    with pytest.raises(TypeError, match="retry_on"):
        RetryPolicy(retry_on=exceptions)


def test_policy_snapshots_the_collection_and_is_frozen():
    exceptions = [ValueError]
    policy = RetryPolicy(attempts=3, retry_on=exceptions)
    exceptions.append(PermissionError)
    assert policy.retry_on == (ValueError,)
    with pytest.raises(FrozenInstanceError):
        policy.attempts = 4


def test_defaults_do_not_repeat_work():
    assert RetryPolicy().attempts == 1
    assert RetryPolicy().retry_on == ()
