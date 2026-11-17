"""Check retry() through the public retry_kit interface.

ScriptedReport stands in for the viewer's load_report: it raises the scripted
exceptions in order, counts every read, and then returns the report. The real
attempt loop and policy run unchanged.
"""

from dataclasses import FrozenInstanceError

import pytest

from retry_kit import RetryPolicy, retry

REPORT = "Report ready: 3 rows."


class ReportNotReady(Exception):
    pass


class ReportStillRendering(ReportNotReady):
    pass


class ScriptedReport:
    def __init__(self, *failures: BaseException) -> None:
        self._failures = list(failures)
        self.raised: list[BaseException] = []
        self.reads = 0

    def load_report(self) -> str:
        self.reads += 1
        if self._failures:
            error = self._failures.pop(0)
            self.raised.append(error)
            raise error
        return REPORT


def not_ready_twice() -> ScriptedReport:
    return ScriptedReport(ReportNotReady("read 1"), ReportNotReady("read 2"))


# Report viewer acceptance [component]


def test_limit_three_gets_the_report_on_the_third_read() -> None:
    source = not_ready_twice()

    report = retry(source.load_report, policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=3))

    assert report == REPORT
    assert source.reads == 3


def test_limit_two_raises_the_exception_from_the_second_read() -> None:
    source = not_ready_twice()

    with pytest.raises(ReportNotReady) as raised:
        retry(source.load_report, policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=2))

    assert raised.value is source.raised[1]
    assert source.reads == 2


def test_permission_error_reaches_the_viewer_after_one_read() -> None:
    denied = PermissionError("report access denied")
    source = ScriptedReport(denied)

    with pytest.raises(PermissionError) as raised:
        retry(source.load_report, policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=3))

    assert raised.value is denied
    assert source.reads == 1


# Retry selection details [component]


def test_first_read_success_makes_one_call_and_returns_the_value_unchanged() -> None:
    value = object()
    calls = []

    def operation() -> object:
        calls.append(1)
        return value

    assert retry(operation, policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=3)) is value
    assert len(calls) == 1


def test_a_subclass_of_a_listed_type_is_retried() -> None:
    source = ScriptedReport(ReportStillRendering("read 1"))

    assert retry(source.load_report, policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=3)) == REPORT
    assert source.reads == 2


def test_a_base_class_of_a_listed_type_is_not_retried() -> None:
    source = ScriptedReport(ReportNotReady("read 1"))

    with pytest.raises(ReportNotReady):
        retry(source.load_report, policy=RetryPolicy(retry_on=[ReportStillRendering], max_attempts=3))
    assert source.reads == 1


def test_an_unlisted_error_after_a_retry_propagates_from_that_read() -> None:
    denied = PermissionError("read 2")
    source = ScriptedReport(ReportNotReady("read 1"), denied)

    with pytest.raises(PermissionError) as raised:
        retry(source.load_report, policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=5))

    assert raised.value is denied
    assert source.reads == 2


def test_a_limit_of_one_makes_a_single_call() -> None:
    source = not_ready_twice()

    with pytest.raises(ReportNotReady) as raised:
        retry(source.load_report, policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=1))

    assert raised.value is source.raised[0]
    assert source.reads == 1


def test_several_listed_types_are_each_retried() -> None:
    source = ScriptedReport(ReportNotReady("read 1"), ConnectionResetError("read 2"))
    policy = RetryPolicy(retry_on=[ReportNotReady, ConnectionError], max_attempts=3)

    assert retry(source.load_report, policy=policy) == REPORT
    assert source.reads == 3


def test_one_policy_gives_every_call_its_own_attempt_count() -> None:
    policy = RetryPolicy(retry_on=[ReportNotReady], max_attempts=3)
    first, second = not_ready_twice(), not_ready_twice()

    assert retry(first.load_report, policy=policy) == REPORT
    assert retry(second.load_report, policy=policy) == REPORT
    assert (first.reads, second.reads) == (3, 3)


def test_the_last_exception_is_not_chained_to_earlier_ones() -> None:
    source = not_ready_twice()

    with pytest.raises(ReportNotReady) as raised:
        retry(source.load_report, policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=2))

    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


# Policy validation [unit]


def test_retry_on_accepts_any_iterable_and_stores_a_tuple() -> None:
    policy = RetryPolicy(retry_on={ReportNotReady}, max_attempts=2)

    assert policy.retry_on == (ReportNotReady,)
    assert policy.max_attempts == 2


@pytest.mark.parametrize(
    ("max_attempts", "error"),
    [(0, ValueError), (-1, ValueError), (True, TypeError), (2.0, TypeError), ("3", TypeError), (None, TypeError)],
)
def test_invalid_max_attempts_is_rejected(max_attempts: object, error: type[Exception]) -> None:
    with pytest.raises(error, match="max_attempts"):
        RetryPolicy(retry_on=[ReportNotReady], max_attempts=max_attempts)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("retry_on", "error"),
    [
        ([], ValueError),
        (ReportNotReady, TypeError),
        ("ReportNotReady", TypeError),
        (None, TypeError),
        ([ReportNotReady, "ValueError"], TypeError),
        ([ReportNotReady("instance")], TypeError),
        ([KeyboardInterrupt], TypeError),
        ([int], TypeError),
    ],
)
def test_invalid_retry_on_is_rejected(retry_on: object, error: type[Exception]) -> None:
    with pytest.raises(error, match="retry_on"):
        RetryPolicy(retry_on=retry_on, max_attempts=3)  # type: ignore[arg-type]


def test_policy_arguments_are_keyword_only() -> None:
    with pytest.raises(TypeError):
        RetryPolicy([ReportNotReady], 3)  # type: ignore[misc]


def test_policy_is_frozen() -> None:
    policy = RetryPolicy(retry_on=[ReportNotReady], max_attempts=3)

    with pytest.raises(FrozenInstanceError):
        policy.max_attempts = 5  # type: ignore[misc]


def test_retry_rejects_a_non_callable_operation() -> None:
    with pytest.raises(TypeError, match="operation must be callable"):
        retry("load_report", policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=3))  # type: ignore[arg-type]


def test_retry_rejects_a_policy_of_the_wrong_type_without_calling() -> None:
    source = ScriptedReport()

    with pytest.raises(TypeError, match="policy must be a RetryPolicy"):
        retry(source.load_report, policy={"retry_on": [ReportNotReady], "max_attempts": 3})  # type: ignore[arg-type]
    assert source.reads == 0
