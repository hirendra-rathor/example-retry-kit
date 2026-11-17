"""Check the waits between attempts without sleeping.

ScriptedReport stands in for the viewer's load_report and its sleep method
stands in for time.sleep. Both append to one event log, so a test can see
which waits were requested and where they fall between reads. The real
attempt loop, wait schedule and policy run unchanged.
"""

import math
from fractions import Fraction
from itertools import islice

import pytest

from retry_kit import RetryPolicy, retry
from retry_kit._schedule import waits

REPORT = "Report ready: 3 rows."


class ReportNotReady(Exception):
    pass


class WaitInterrupted(Exception):
    pass


class ScriptedReport:
    def __init__(self, *failures: BaseException) -> None:
        self._failures = list(failures)
        self.raised: list[BaseException] = []
        self.events: list[str] = []
        self.waits: list[float] = []
        self.reads = 0

    def load_report(self) -> str:
        self.reads += 1
        self.events.append(f"read {self.reads}")
        if self._failures:
            error = self._failures.pop(0)
            self.raised.append(error)
            raise error
        return REPORT

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.events.append(f"wait {seconds}")


def not_ready(reads: int) -> ScriptedReport:
    return ScriptedReport(*(ReportNotReady(f"read {n}") for n in range(1, reads + 1)))


def viewer_policy(max_attempts: int = 4) -> RetryPolicy:
    return RetryPolicy(retry_on=[ReportNotReady], max_attempts=max_attempts, initial_delay=0.1, max_delay=0.25)


def never_sleep(seconds: float) -> None:
    raise AssertionError(f"sleep({seconds}) should not have been called")


# Viewer waits [component]


def test_viewer_waits_before_reads_two_three_and_four() -> None:
    source = not_ready(3)

    report = retry(source.load_report, policy=viewer_policy(), sleep=source.sleep)

    assert report == REPORT
    assert source.waits == [0.1, 0.2, 0.25]
    assert source.events == ["read 1", "wait 0.1", "read 2", "wait 0.2", "read 3", "wait 0.25", "read 4"]


def test_viewer_gets_the_report_as_soon_as_a_read_succeeds() -> None:
    source = not_ready(1)

    assert retry(source.load_report, policy=viewer_policy(), sleep=source.sleep) == REPORT
    assert source.events == ["read 1", "wait 0.1", "read 2"]


def test_first_read_starts_at_once_and_success_needs_no_wait() -> None:
    source = not_ready(0)

    assert retry(source.load_report, policy=viewer_policy(), sleep=source.sleep) == REPORT
    assert source.events == ["read 1"]


# All four fail [component]


def test_all_four_reads_failing_raise_the_fourth_exception_without_another_wait() -> None:
    source = not_ready(4)

    with pytest.raises(ReportNotReady) as raised:
        retry(source.load_report, policy=viewer_policy(), sleep=source.sleep)

    assert raised.value is source.raised[3]
    assert source.events[-1] == "read 4"
    assert source.waits == [0.1, 0.2, 0.25]


# Unset delay and unlisted errors [component]


def test_unset_delay_never_sleeps() -> None:
    source = not_ready(3)

    report = retry(source.load_report, policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=4), sleep=never_sleep)

    assert report == REPORT
    assert source.reads == 4


def test_an_unlisted_error_on_the_first_read_does_not_wait() -> None:
    source = ScriptedReport(PermissionError("read 1"))

    with pytest.raises(PermissionError):
        retry(source.load_report, policy=viewer_policy(), sleep=never_sleep)
    assert source.reads == 1


def test_an_unlisted_error_after_a_retry_propagates_without_another_wait() -> None:
    source = ScriptedReport(ReportNotReady("read 1"), PermissionError("read 2"))

    with pytest.raises(PermissionError):
        retry(source.load_report, policy=viewer_policy(), sleep=source.sleep)
    assert source.events == ["read 1", "wait 0.1", "read 2"]


# Wait schedule details [component]


def test_waits_stay_at_the_maximum_once_reached() -> None:
    source = not_ready(5)

    retry(source.load_report, policy=viewer_policy(max_attempts=6), sleep=source.sleep)

    assert source.waits == [0.1, 0.2, 0.25, 0.25, 0.25]


def test_each_retry_call_starts_its_waits_afresh() -> None:
    policy = viewer_policy()
    first, second = not_ready(2), not_ready(2)

    retry(first.load_report, policy=policy, sleep=first.sleep)
    retry(second.load_report, policy=policy, sleep=second.sleep)

    assert first.waits == second.waits == [0.1, 0.2]


def test_whole_second_settings_are_slept_as_floats() -> None:
    source = not_ready(3)

    retry(
        source.load_report,
        policy=RetryPolicy(retry_on=[ReportNotReady], max_attempts=4, initial_delay=1, max_delay=4),
        sleep=source.sleep,
    )

    assert source.waits == [1.0, 2.0, 4.0]
    assert all(type(wait) is float for wait in source.waits)


def test_an_exception_from_sleep_propagates_and_stops_the_retries() -> None:
    source = not_ready(3)

    def interrupted(seconds: float) -> None:
        raise WaitInterrupted

    with pytest.raises(WaitInterrupted) as raised:
        retry(source.load_report, policy=viewer_policy(), sleep=interrupted)

    assert source.reads == 1
    assert raised.value.__context__ is None


def test_retry_rejects_a_sleep_that_is_not_callable() -> None:
    source = not_ready(0)

    with pytest.raises(TypeError, match="sleep must be callable"):
        retry(source.load_report, policy=viewer_policy(), sleep=0.1)  # type: ignore[arg-type]
    assert source.reads == 0


# Wait schedule [unit]


def test_schedule_doubles_from_the_initial_delay_and_caps_at_the_maximum() -> None:
    assert list(islice(waits(0.1, 0.25), 4)) == [0.1, 0.2, 0.25, 0.25]


def test_schedule_with_equal_delays_is_constant() -> None:
    assert list(islice(waits(0.5, 0.5), 3)) == [0.5, 0.5, 0.5]


# Delay validation [unit]


def test_delays_default_to_unset() -> None:
    policy = RetryPolicy(retry_on=[ReportNotReady], max_attempts=3)

    assert (policy.initial_delay, policy.max_delay) == (None, None)


def test_delays_are_stored_as_float_seconds() -> None:
    policy = RetryPolicy(retry_on=[ReportNotReady], max_attempts=3, initial_delay=Fraction(1, 4), max_delay=1)

    assert (policy.initial_delay, policy.max_delay) == (0.25, 1.0)


@pytest.mark.parametrize(
    ("initial_delay", "max_delay", "error", "message"),
    [
        (0.1, None, ValueError, "needs a max_delay"),
        (None, 0.25, ValueError, "no effect without initial_delay"),
        (0.3, 0.25, ValueError, "at least initial_delay"),
        (0, 0.25, ValueError, "greater than 0"),
        (-0.1, 0.25, ValueError, "greater than 0"),
        (math.nan, 0.25, ValueError, "finite"),
        (0.1, math.inf, ValueError, "finite"),
        (True, 2, TypeError, "number of seconds"),
        ("0.1", 0.25, TypeError, "number of seconds"),
        (0.1, "0.25", TypeError, "number of seconds"),
    ],
)
def test_invalid_delays_are_rejected(initial_delay: object, max_delay: object, error: type[Exception], message: str) -> None:
    with pytest.raises(error, match=message):
        RetryPolicy(retry_on=[ReportNotReady], max_attempts=3, initial_delay=initial_delay, max_delay=max_delay)  # type: ignore[arg-type]
