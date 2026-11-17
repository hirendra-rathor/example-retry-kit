"""Run a local report viewer that retries a report still being prepared.

The viewer allows four reads and waits 0.1 s, then 0.2 s, then 0.25 s
between them. With no options the report is ready on the third read. Use
``--not-ready-reads 3`` or ``4`` to try the other outcomes, ``--show-waits``
to print each wait, ``--attempts 2`` to receive the second read's
ReportNotReady, or ``--deny-access`` to see a PermissionError arrive at once.
"""

import argparse
import sys
import time

from retry_kit import RetryPolicy, retry


class ReportNotReady(Exception):
    """The report is still being prepared; reading it again later is safe."""


class PreparingReport:
    """Supply an example report without an external service.

    The first ``not_ready_reads`` reads raise ReportNotReady; later reads
    return the report. With ``deny_access`` every read raises PermissionError.
    """

    def __init__(self, not_ready_reads: int, *, deny_access: bool = False) -> None:
        self.not_ready_reads = not_ready_reads
        self.deny_access = deny_access
        self.reads = 0

    def load_report(self) -> str:
        self.reads += 1
        if self.deny_access:
            raise PermissionError(f"report access denied (read {self.reads})")
        if self.reads <= self.not_ready_reads:
            raise ReportNotReady(f"report is still being prepared (read {self.reads})")
        return "Report ready: 3 rows."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--attempts", type=int, default=4, help="reads to allow (default: 4)")
    parser.add_argument(
        "--not-ready-reads", type=int, default=2, help="reads that raise ReportNotReady (default: 2)"
    )
    parser.add_argument("--deny-access", action="store_true", help="make every read raise PermissionError")
    parser.add_argument("--show-waits", action="store_true", help="print each wait to stderr")
    args = parser.parse_args(argv)

    report = PreparingReport(not_ready_reads=args.not_ready_reads, deny_access=args.deny_access)
    policy = RetryPolicy(
        retry_on=[ReportNotReady], max_attempts=args.attempts, initial_delay=0.1, max_delay=0.25
    )

    def sleep(seconds: float) -> None:
        if args.show_waits:
            print(f"Waiting {seconds} s before read {report.reads + 1}", file=sys.stderr)
        time.sleep(seconds)

    try:
        print(retry(report.load_report, policy=policy, sleep=sleep))
    except (ReportNotReady, PermissionError) as error:
        print(
            f"Viewer received {type(error).__name__} after {report.reads} read(s): {error}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
