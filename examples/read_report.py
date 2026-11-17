"""Rehearse recovery, exhaustion, and an unrelated failure through the public API."""

from retry_kit import RetryPolicy, retry


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


def main() -> None:
    demonstrate("Recovery", 3)
    demonstrate("Exhaustion", 2)
    demonstrate("Permission", 3, forbidden=True)


if __name__ == "__main__":
    main()
