"""Demonstrate elapsed admission with a controlled clock and no real sleeping."""

from retry_kit import RetryPolicy, retry


class ReportNotReady(Exception):
    """The report read is safe to repeat when time and attempts allow."""


class Timeline:
    """Simulation dependency: operation and waiting explicitly advance time."""

    def __init__(self, oversleep: float = 0.0) -> None:
        self.now = 0.0
        self.oversleep = oversleep
        self.waits: list[float] = []

    def clock(self) -> float:
        return self.now

    def wait(self, delay: float) -> None:
        self.waits.append(delay)
        self.now += delay + self.oversleep


def demonstrate(label: str, *, succeeds: bool, work: float = 0.4,
                delay: float = 0.3, oversleep: float = 0.0) -> None:
    timeline = Timeline(oversleep)
    starts = []

    def load_report() -> str:
        starts.append(timeline.now)
        timeline.now += work
        if succeeds and len(starts) == 2:
            return "Report ready: 3 rows."
        raise ReportNotReady(f"Report not ready on read {len(starts)}.")

    policy = RetryPolicy(5, [ReportNotReady], delay, delay, time_budget=1.0)
    try:
        outcome = retry(load_report, policy=policy, wait=timeline.wait, clock=timeline.clock)
    except ReportNotReady as error:
        outcome = f"ReportNotReady: {error}"
    print(f"{label}: {outcome}")
    print(f"  Starts: {[round(t, 2) for t in starts]}; waits: {timeline.waits}; elapsed: {timeline.now:.1f}s.")


def main() -> None:
    demonstrate("Late success", succeeds=True)
    demonstrate("Late failure", succeeds=False)
    demonstrate("Exact deadline", succeeds=False, work=0.5, delay=0.5)
    demonstrate("Oversleep", succeeds=True, oversleep=0.4)


if __name__ == "__main__":
    main()
