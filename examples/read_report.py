"""Rehearse recovery, exhaustion, and an unrelated failure through the public API."""

from retry_kit import RetryPolicy, retry
from time import sleep


class ReportNotReady(Exception):
    """The caller knows that a report read can safely be repeated."""


def demonstrate(label: str, attempts: int, *, forbidden: bool = False) -> None:
    reads = 0

    def load_report() -> str:
        nonlocal reads
        reads += 1
        if forbidden:
            raise PermissionError("Report access denied.")
        if reads < 3:
            raise ReportNotReady(f"Report not ready on read {reads}.")
        return "Report ready: 3 rows."

    policy = RetryPolicy(attempts=attempts, retry_on=[ReportNotReady])
    try:
        outcome = retry(load_report, policy=policy)
    except (ReportNotReady, PermissionError) as error:
        outcome = f"{type(error).__name__}: {error}"
    print(f"{label}: {outcome} Calls: {reads}.")


def demonstrate_waits(*, never_ready: bool = False) -> None:
    reads = 0
    requested = []

    def load_report() -> str:
        nonlocal reads
        reads += 1
        if never_ready or reads < 4:
            raise ReportNotReady(f"Report not ready on read {reads}.")
        return "Report ready: 3 rows."

    def observed_sleep(delay: float) -> None:
        requested.append(delay)
        sleep(delay)

    policy = RetryPolicy(4, [ReportNotReady], initial_delay=0.1, max_delay=0.25)
    try:
        outcome = retry(load_report, policy=policy, wait=observed_sleep)
    except ReportNotReady as error:
        outcome = f"ReportNotReady: {error}"
    label = "Delayed exhaustion" if never_ready else "Delayed recovery"
    print(f"{label}: {outcome} Calls: {reads}. Waits: {requested}.")


def main() -> None:
    demonstrate("Recovery", 3)
    demonstrate("Exhaustion", 2)
    demonstrate("Permission", 3, forbidden=True)
    demonstrate_waits()
    demonstrate_waits(never_ready=True)


if __name__ == "__main__":
    main()
