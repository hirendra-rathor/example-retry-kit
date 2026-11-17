"""Observe admission through the public API with controlled time."""

import math

import pytest

from retry_kit import RetryPolicy, retry
from retry_kit.budget import Budget


class Pending(Exception):
    pass


class Time:
    def __init__(self, origin=0.0, oversleep=0.0):
        self.now = origin
        self.oversleep = oversleep
        self.waits = []
        self.readings = []

    def clock(self):
        self.readings.append(self.now)
        return self.now

    def wait(self, delay):
        self.waits.append(delay)
        self.now += delay + self.oversleep


@pytest.mark.parametrize("value", [-1, math.inf, -math.inf, math.nan, 10**400])
def test_invalid_budget_durations(value):
    with pytest.raises(ValueError, match="time_budget"):
        RetryPolicy(time_budget=value)


@pytest.mark.parametrize("value", [True, "1", object()])
def test_invalid_budget_types(value):
    with pytest.raises(TypeError, match="time_budget"):
        RetryPolicy(time_budget=value)


@pytest.mark.parametrize("succeeds", [True, False])
def test_one_second_budget_retains_second_call_outcome(succeeds):
    time = Time()
    starts, failures = [], []
    result = object()

    def operation():
        starts.append(time.now)
        time.now += 0.4
        if succeeds and len(starts) == 2:
            return result
        error = Pending(f"read {len(starts)}")
        failures.append(error)
        raise error

    policy = RetryPolicy(5, [Pending], 0.3, 0.3, 1.0)
    if succeeds:
        assert retry(operation, policy=policy, wait=time.wait, clock=time.clock) is result
        assert time.readings == pytest.approx([0.0, 0.4, 0.7])
    else:
        with pytest.raises(Pending) as caught:
            retry(operation, policy=policy, wait=time.wait, clock=time.clock)
        assert caught.value is failures[1]
    assert starts == pytest.approx([0.0, 0.7])
    assert time.now == pytest.approx(1.1)
    assert time.waits == [0.3]


@pytest.mark.parametrize("work,allowed", [(0.25, True), (0.5, False), (0.75, False)])
def test_full_wait_must_end_strictly_before_deadline(work, allowed):
    time = Time()
    calls = []
    failure = Pending("first")

    def operation():
        calls.append(time.now)
        if len(calls) == 2:
            return "ready"
        time.now += work
        raise failure

    policy = RetryPolicy(3, [Pending], 0.5, 0.5, 1.0)
    if allowed:
        assert retry(operation, policy=policy, wait=time.wait, clock=time.clock) == "ready"
        assert calls == [0.0, 0.75]
        assert time.waits == [0.5]
    else:
        with pytest.raises(Pending) as caught:
            retry(operation, policy=policy, wait=time.wait, clock=time.clock)
        assert caught.value is failure
        assert calls == [0.0]
        assert time.waits == []


@pytest.mark.parametrize("oversleep", [0.5, 0.75])
def test_wait_reaching_or_crossing_deadline_denies_next_call(oversleep):
    time = Time(oversleep=oversleep)
    calls = []
    failure = Pending("first")

    def operation():
        calls.append(time.now)
        time.now += 0.25
        raise failure

    with pytest.raises(Pending) as caught:
        retry(operation, policy=RetryPolicy(3, [Pending], 0.25, 0.25, 1.0), wait=time.wait, clock=time.clock)
    assert caught.value is failure
    assert calls == [0.0]
    assert time.waits == [0.25]
    assert time.now >= 1.0


def test_zero_delay_still_rechecks_time_before_retry():
    readings = iter([0.0, 0.75, 1.0])
    calls, waits = [], []
    failure = Pending()

    def operation():
        calls.append(True)
        raise failure

    with pytest.raises(Pending) as caught:
        retry(operation, policy=RetryPolicy(3, [Pending], time_budget=1), wait=waits.append, clock=lambda: next(readings))
    assert caught.value is failure
    assert calls == [True]
    assert waits == []


@pytest.mark.parametrize("succeeds", [True, False])
def test_zero_budget_allows_only_initial_call_even_if_it_runs_late(succeeds):
    time = Time()
    calls = []
    failure = Pending()

    def operation():
        calls.append(True)
        time.now += 2
        if succeeds:
            return "late but valid"
        raise failure

    policy = RetryPolicy(4, [Pending], time_budget=0)
    if succeeds:
        assert retry(operation, policy=policy, wait=time.wait, clock=time.clock) == "late but valid"
    else:
        with pytest.raises(Pending) as caught:
            retry(operation, policy=policy, wait=time.wait, clock=time.clock)
        assert caught.value is failure
    assert calls == [True]
    assert time.waits == []


def test_disabled_budget_never_reads_clock():
    calls = []

    def clock():
        pytest.fail("disabled timing must not read this provider")

    def operation():
        calls.append(True)
        if len(calls) == 1:
            raise Pending()
        return 42

    assert retry(operation, policy=RetryPolicy(2, [Pending]), clock=clock) == 42
    assert len(calls) == 2


@pytest.mark.parametrize("unrelated", [True, False])
def test_terminal_failure_needs_no_additional_clock_read(unrelated):
    reads, calls = [], []
    error = PermissionError() if unrelated else Pending()

    def clock():
        reads.append(True)
        assert len(reads) == 1, "terminal failure must not consult time again"
        return 0

    def operation():
        calls.append(True)
        raise error

    with pytest.raises(type(error)) as caught:
        retry(operation, policy=RetryPolicy(5 if unrelated else 1, [Pending], time_budget=1), clock=clock)
    assert caught.value is error
    assert calls == reads == [True]


@pytest.mark.parametrize("failure_at", [0, 1, 2])
def test_clock_failure_is_not_retried_as_operation_failure(failure_at):
    reads, calls, waits = [], [], []
    failure = RuntimeError("clock failed")

    def clock():
        reads.append(True)
        if len(reads)-1 == failure_at:
            raise failure
        return 0

    def operation():
        calls.append(True)
        raise RuntimeError("operation failed")

    with pytest.raises(RuntimeError) as caught:
        retry(operation, policy=RetryPolicy(4, [Exception], 0.1, 0.1, 1.0), clock=clock, wait=waits.append)
    assert caught.value is failure
    assert len(calls) == (0 if failure_at == 0 else 1)
    assert waits == ([0.1] if failure_at == 2 else [])


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "0", 10**400])
@pytest.mark.parametrize("after_start", [False, True])
def test_invalid_clock_readings_escape(value, after_start):
    readings = iter([0, value] if after_start else [value])
    calls = []

    def operation():
        calls.append(True)
        raise Pending()

    with pytest.raises((ValueError, TypeError), match="clock"):
        retry(operation, policy=RetryPolicy(4, [Exception], time_budget=1), clock=lambda: next(readings))
    assert len(calls) == int(after_start)


def test_backwards_clock_is_rejected():
    readings = iter([2.0, 1.0])
    budget = Budget(3, lambda: next(readings))
    with pytest.raises(ValueError, match="nondecreasing"):
        budget.allows()


@pytest.mark.parametrize("origin", [-100.0, 0.0, 1e12])
def test_budget_uses_elapsed_time_and_policy_reuse_gets_a_fresh_start(origin):
    time = Time(origin)
    policy = RetryPolicy(3, [Pending], 0.25, 0.25, 1.0)
    for _ in range(2):
        calls = []

        def operation():
            calls.append(time.now)
            time.now += 0.25
            if len(calls) == 1:
                raise Pending()
            return "ready"

        assert retry(operation, policy=policy, clock=time.clock, wait=time.wait) == "ready"
        assert calls[1] - calls[0] == 0.5
        time.now += 100


def test_large_epoch_does_not_overflow_an_absolute_deadline():
    budget = Budget(1e308, lambda: 1e308)
    assert budget.allows(1.0)


def test_noncallable_clock_fails_only_when_timing_is_enabled():
    assert retry(lambda: 7, clock=None) == 7
    with pytest.raises(TypeError, match="clock"):
        retry(lambda: pytest.fail("must validate before callback"), policy=RetryPolicy(time_budget=1), clock=None)


def test_default_monotonic_provider_enforces_zero_budget_without_sleeping():
    calls = []
    error = Pending("real monotonic clock")

    def operation():
        calls.append(True)
        raise error

    with pytest.raises(Pending) as caught:
        retry(operation, policy=RetryPolicy(3, [Pending], time_budget=0))
    assert caught.value is error
    assert calls == [True]
