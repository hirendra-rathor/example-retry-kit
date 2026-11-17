"""Caller-visible guarantees, using only the public Retry Kit interface."""

import pytest

from retry_kit import RetryPolicy, retry


class Pending(Exception):
    pass


def test_two_failures_then_success_returns_original_object():
    result = object()
    calls = []

    def operation():
        calls.append(len(calls) + 1)
        if len(calls) < 3:
            raise Pending(str(len(calls)))
        return result

    assert retry(operation, policy=RetryPolicy(3, [Pending])) is result
    assert calls == [1, 2, 3]


def test_exhaustion_preserves_the_second_failure():
    failures = [Pending("first"), Pending("second")]
    calls = []

    def operation():
        calls.append(len(calls))
        raise failures[calls[-1]]

    with pytest.raises(Pending) as caught:
        retry(operation, policy=RetryPolicy(2, [Pending]))
    assert caught.value is failures[1]
    assert len(calls) == 2


@pytest.mark.parametrize("error,eligible", [(PermissionError("denied"), [Pending]), (Pending("no retries"), []), (KeyboardInterrupt(), [Exception]), (SystemExit(2), [Exception])])
def test_unselected_failures_and_control_signals_escape_once(error, eligible):
    calls = []

    def operation():
        calls.append(True)
        raise error

    with pytest.raises(type(error)) as caught:
        retry(operation, policy=RetryPolicy(5, eligible))
    assert caught.value is error
    assert calls == [True]


def test_subclasses_qualify_and_reused_policy_has_independent_progress():
    class ChildPending(Pending):
        pass

    policy = RetryPolicy(2, [Pending])
    counts = []
    for expected in [object(), object()]:
        calls = []

        def operation():
            calls.append(True)
            if len(calls) == 1:
                raise ChildPending()
            return expected

        assert retry(operation, policy=policy) is expected
        counts.append(len(calls))
    assert counts == [2, 2]


@pytest.mark.parametrize("result", [None, False, 0, "", []])
def test_success_returns_immediately_even_for_falsey_values(result):
    calls = []

    def operation():
        calls.append(True)
        return result

    assert retry(operation, policy=RetryPolicy(4, [Exception])) is result
    assert calls == [True]


def test_single_attempt_preserves_failure():
    error = Pending("initial call")
    calls = []

    def operation():
        calls.append(True)
        raise error

    with pytest.raises(Pending) as caught:
        retry(operation, policy=RetryPolicy(1, [Pending]))
    assert caught.value is error
    assert len(calls) == 1


def test_noncallable_is_rejected_before_retry_classification():
    with pytest.raises(TypeError, match="operation must be callable"):
        retry(None, policy=RetryPolicy(3, [TypeError]))
