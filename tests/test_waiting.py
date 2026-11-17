"""Separate interval mathematics from public call/wait ordering."""

from itertools import islice
import math

import pytest

from retry_kit import RetryPolicy, retry
from retry_kit.waiting import intervals


@pytest.mark.parametrize("field", ["initial_delay", "max_delay"])
@pytest.mark.parametrize("value", [-1, math.inf, -math.inf, math.nan, 10**400])
def test_durations_must_be_finite_and_nonnegative(field, value):
    with pytest.raises(ValueError, match=field):
        RetryPolicy(**{field: value})


@pytest.mark.parametrize("field", ["initial_delay", "max_delay"])
@pytest.mark.parametrize("value", [True, "0.1", object()])
def test_durations_reject_other_types(field, value):
    with pytest.raises(TypeError, match=field):
        RetryPolicy(**{field: value})


@pytest.mark.parametrize("settings", [{"initial_delay": 0.1}, {"initial_delay": 0.5, "max_delay": 0.25}])
def test_positive_initial_delay_requires_a_compatible_cap(settings):
    with pytest.raises(ValueError, match="max_delay"):
        RetryPolicy(**settings)


@pytest.mark.parametrize("initial,cap,expected", [(0.1, 0.25, [0.1, 0.2, 0.25, 0.25, 0.25]), (0.0, None, [0.0]*5), (0.0, 1.0, [0.0]*5), (0.0, 5e-324, [0.0]*5), (1e308, 1.7e308, [1e308, 1.7e308, 1.7e308, 1.7e308, 1.7e308])])
def test_intervals_double_and_saturate(initial, cap, expected):
    assert list(islice(intervals(RetryPolicy(initial_delay=initial, max_delay=cap)), 5)) == expected


@pytest.mark.parametrize("succeed", [True, False])
def test_public_call_and_wait_order_for_four_attempts(succeed):
    events = []
    failures = [ValueError(str(i)) for i in range(1, 5)]
    result = object()
    calls = 0

    def operation():
        nonlocal calls
        calls += 1
        events.append(("call", calls))
        if succeed and calls == 4:
            return result
        raise failures[calls-1]

    def wait(delay):
        events.append(("wait", delay))

    policy = RetryPolicy(4, [ValueError], 0.1, 0.25)
    if succeed:
        assert retry(operation, policy=policy, wait=wait) is result
    else:
        with pytest.raises(ValueError) as caught:
            retry(operation, policy=policy, wait=wait)
        assert caught.value is failures[3]
    assert events == [("call", 1), ("wait", 0.1), ("call", 2), ("wait", 0.2), ("call", 3), ("wait", 0.25), ("call", 4)]


@pytest.mark.parametrize("outcome,attempts", [("success", 4), ("unrelated", 4), ("exhausted", 1)])
def test_stopping_outcomes_have_no_wait(outcome, attempts):
    calls, waits = [], []

    def operation():
        calls.append(True)
        if outcome == "unrelated":
            raise PermissionError()
        if outcome == "exhausted":
            raise ValueError()
        return "ok"

    policy = RetryPolicy(attempts, [ValueError], 0.1, 0.25)
    if outcome == "success":
        assert retry(operation, policy=policy, wait=waits.append) == "ok"
    else:
        with pytest.raises(PermissionError if outcome == "unrelated" else ValueError):
            retry(operation, policy=policy, wait=waits.append)
    assert calls == [True]
    assert waits == []


def test_immediate_retries_do_not_invoke_wait():
    calls, waits = [], []

    def operation():
        calls.append(True)
        raise ValueError()

    with pytest.raises(ValueError):
        retry(operation, policy=RetryPolicy(3, [ValueError]), wait=waits.append)
    assert len(calls) == 3
    assert waits == []


def test_wait_failure_is_not_a_retryable_operation_failure():
    failure = ValueError("waiting failed")
    calls, waits = [], []

    def operation():
        calls.append(True)
        raise ValueError("operation failed")

    def wait(delay):
        waits.append(delay)
        raise failure

    with pytest.raises(ValueError) as caught:
        retry(operation, policy=RetryPolicy(4, [ValueError], 0.1, 0.25), wait=wait)
    assert caught.value is failure
    assert calls == [True]
    assert waits == [0.1]


def test_reusing_a_policy_restarts_the_schedule():
    policy = RetryPolicy(3, [ValueError], 0.1, 0.25)
    for _ in range(2):
        waits = []

        def operation():
            raise ValueError()

        with pytest.raises(ValueError):
            retry(operation, policy=policy, wait=waits.append)
        assert waits == [0.1, 0.2]


def test_invalid_wait_is_rejected_before_operation_runs():
    calls = []
    with pytest.raises(TypeError, match="wait"):
        retry(lambda: calls.append(True), wait=None)
    assert calls == []
