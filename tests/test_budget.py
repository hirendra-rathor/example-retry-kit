"""Check the time budget for starting retries with a controlled clock.

FakeClock stands in for time.monotonic. TimedReport stands in for the
viewer's load_report: each read advances the clock by its duration and
raises the scripted exceptions in order. Its sleep advances the clock by the
requested wait plus an optional overrun, so no real time passes. The real
attempt loop, wait schedule, deadline and policy run unchanged.

Boundary tests use values that are exact in binary floating point (0.25,
0.5, 0.75, 0.875, 1.0) so equality with the deadline is exact.
"""

import math

import pytest

from retry_kit import RetryPolicy, retry
from retry_kit._deadline import Deadline

REPORT = "Report ready: 3 rows."


class ReportNotReady(Exception):
    pass


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start
        self.readings = 0

    def __call__(self) -> float:
        self.readings += 1
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TimedReport:
    def __init__(self, clock: FakeClock, read_seconds: float, *failures: BaseException, overrun: float = 0.0) -> None:
        self.clock = clock
        self.read_seconds = read_seconds
        self.overrun = overrun
        self._failures = list(failures)
        self.raised: list[BaseException] = []
        self.starts: list[float] = []
        self.waits: list[tuple[float, float]] = []  # (clock when the wait began, requested seconds)

    @property
    def reads(self) -> int:
        return len(self.starts)

    def load_report(self) -> str:
        self.starts.append(self.clock.now)
        self.clock.advance(self.read_seconds)
        if self._failures:
            error = self._failures.pop(0)
            self.raised.append(error)
            raise error
        return REPORT

    def sleep(self, seconds: float) -> None:
        self.waits.append((self.clock.now, seconds))
        self.clock.advance(seconds + self.overrun)


def not_ready(n: int) -> list[ReportNotReady]:
    return [ReportNotReady(f"read {i}") for i in range(1, n + 1)]


def viewer_policy(wait: float = 0.3, budget: float = 1.0, max_attempts: int = 5) -> RetryPolicy:
    return RetryPolicy(
        retry_on=[ReportNotReady], max_attempts=max_attempts, initial_delay=wait, max_delay=wait, time_budget=budget
    )


def failing_clock() -> float:
    raise AssertionError("the clock should not have been read")


# The viewer's one-second budget [component]


def test_report_ready_at_1_1_seconds_is_returned_after_the_deadline() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.4, *not_ready(1))

    report = retry(source.load_report, policy=viewer_policy(), sleep=source.sleep, clock=clock)

    assert report == REPORT
    assert source.starts == pytest.approx([0.0, 0.7])
    assert source.waits == [(pytest.approx(0.4), 0.3)]
    assert clock.now == pytest.approx(1.1)


def test_report_still_preparing_at_1_1_seconds_raises_read_twos_exception_without_waiting() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.4, *not_ready(5))

    with pytest.raises(ReportNotReady) as raised:
        retry(source.load_report, policy=viewer_policy(max_attempts=5), sleep=source.sleep, clock=clock)

    assert raised.value is source.raised[1]
    assert source.reads == 2  # three of five attempts unused
    assert len(source.waits) == 1
    assert clock.now == pytest.approx(1.1)


# Boundary and overrun [component]


def test_a_retry_planned_before_the_deadline_waits_and_starts() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.5, *not_ready(1))

    assert retry(source.load_report, policy=viewer_policy(wait=0.25), sleep=source.sleep, clock=clock) == REPORT
    assert source.waits == [(0.5, 0.25)]
    assert source.starts == [0.0, 0.75]


def test_a_retry_planned_exactly_at_the_deadline_raises_without_waiting() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.75, *not_ready(1))

    with pytest.raises(ReportNotReady) as raised:
        retry(source.load_report, policy=viewer_policy(wait=0.25), sleep=source.sleep, clock=clock)

    assert raised.value is source.raised[0]
    assert source.waits == []
    assert source.reads == 1


def test_a_retry_planned_past_the_deadline_raises_without_waiting() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.875, *not_ready(1))

    with pytest.raises(ReportNotReady):
        retry(source.load_report, policy=viewer_policy(wait=0.25), sleep=source.sleep, clock=clock)
    assert source.waits == []


def test_a_wait_that_overruns_to_the_deadline_stops_the_retry() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.5, *not_ready(1), overrun=0.25)

    with pytest.raises(ReportNotReady) as raised:
        retry(source.load_report, policy=viewer_policy(wait=0.25), sleep=source.sleep, clock=clock)

    assert raised.value is source.raised[0]
    assert source.waits == [(0.5, 0.25)]
    assert clock.now == 1.0
    assert source.reads == 1


def test_a_wait_that_overruns_but_ends_before_the_deadline_still_retries() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.5, *not_ready(1), overrun=0.125)

    assert retry(source.load_report, policy=viewer_policy(wait=0.25), sleep=source.sleep, clock=clock) == REPORT
    assert source.starts == [0.0, 0.875]


# Budget without delays and other details [component]


def test_a_budget_without_delays_retries_at_once_while_time_remains() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.375, *not_ready(9))
    policy = RetryPolicy(retry_on=[ReportNotReady], max_attempts=10, time_budget=1.0)

    with pytest.raises(ReportNotReady) as raised:
        retry(source.load_report, policy=policy, sleep=source.sleep, clock=clock)

    assert source.starts == [0.0, 0.375, 0.75]
    assert raised.value is source.raised[2]
    assert clock.now == 1.125
    assert source.waits == []


def test_the_deadline_is_relative_to_the_clock_reading_at_the_first_call() -> None:
    clock = FakeClock(start=1000.0)
    source = TimedReport(clock, 0.4, *not_ready(1))

    assert retry(source.load_report, policy=viewer_policy(), sleep=source.sleep, clock=clock) == REPORT
    assert source.starts == pytest.approx([1000.0, 1000.7])


def test_each_retry_call_gets_its_own_budget() -> None:
    clock = FakeClock()
    policy = viewer_policy()
    first = TimedReport(clock, 0.4, *not_ready(1))
    second = TimedReport(clock, 0.4, *not_ready(1))

    retry(first.load_report, policy=policy, sleep=first.sleep, clock=clock)
    assert retry(second.load_report, policy=policy, sleep=second.sleep, clock=clock) == REPORT

    assert second.starts == pytest.approx([1.1, 1.8])


def test_the_clock_is_read_at_the_first_call_and_around_each_wait() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.4, *not_ready(1))

    retry(source.load_report, policy=viewer_policy(), sleep=source.sleep, clock=clock)

    assert clock.readings == 3  # first call, before the wait, after the wait


def test_an_unlisted_error_propagates_at_once_with_a_budget() -> None:
    clock = FakeClock()
    denied = PermissionError("read 1")
    source = TimedReport(clock, 0.4, denied)

    with pytest.raises(PermissionError) as raised:
        retry(source.load_report, policy=viewer_policy(), sleep=source.sleep, clock=clock)

    assert raised.value is denied
    assert clock.readings == 1
    assert source.waits == []


def test_the_out_of_time_exception_is_not_chained() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.75, *not_ready(1))

    with pytest.raises(ReportNotReady) as raised:
        retry(source.load_report, policy=viewer_policy(wait=0.25), sleep=source.sleep, clock=clock)

    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None


# No budget [component]


def test_without_a_budget_the_clock_is_never_read() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.4, *not_ready(3))
    policy = RetryPolicy(retry_on=[ReportNotReady], max_attempts=4, initial_delay=0.3, max_delay=0.3)

    assert retry(source.load_report, policy=policy, sleep=source.sleep, clock=failing_clock) == REPORT
    assert source.reads == 4


def test_without_a_budget_or_delays_the_clock_is_never_read() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.4, *not_ready(2))
    policy = RetryPolicy(retry_on=[ReportNotReady], max_attempts=3)

    assert retry(source.load_report, policy=policy, sleep=source.sleep, clock=failing_clock) == REPORT


def test_retry_rejects_a_clock_that_is_not_callable() -> None:
    clock = FakeClock()
    source = TimedReport(clock, 0.4)

    with pytest.raises(TypeError, match="clock must be callable"):
        retry(source.load_report, policy=viewer_policy(), sleep=source.sleep, clock=0.0)  # type: ignore[arg-type]
    assert source.reads == 0


# Deadline [unit]


def test_deadline_allows_only_starts_strictly_before_it() -> None:
    clock = FakeClock()
    deadline = Deadline(1.0, clock)
    clock.now = 0.75

    assert deadline.allows_wait(0.125) is True
    assert deadline.allows_wait(0.25) is False
    assert deadline.allows_start() is True
    clock.now = 1.0
    assert deadline.allows_start() is False


def test_deadline_without_a_budget_never_reads_the_clock() -> None:
    deadline = Deadline(None, failing_clock)

    assert deadline.allows_wait(1e9) is True
    assert deadline.allows_start() is True


# Budget validation [unit]


def test_time_budget_defaults_to_unset_and_is_stored_as_float() -> None:
    assert RetryPolicy(retry_on=[ReportNotReady], max_attempts=2).time_budget is None
    assert RetryPolicy(retry_on=[ReportNotReady], max_attempts=2, time_budget=1).time_budget == 1.0


@pytest.mark.parametrize(
    ("time_budget", "error", "message"),
    [
        (0, ValueError, "greater than 0"),
        (-1.0, ValueError, "greater than 0"),
        (math.nan, ValueError, "finite"),
        (math.inf, ValueError, "finite"),
        (True, TypeError, "number of seconds"),
        ("1", TypeError, "number of seconds"),
    ],
)
def test_invalid_time_budget_is_rejected(time_budget: object, error: type[Exception], message: str) -> None:
    with pytest.raises(error, match=message):
        RetryPolicy(retry_on=[ReportNotReady], max_attempts=3, time_budget=time_budget)  # type: ignore[arg-type]
