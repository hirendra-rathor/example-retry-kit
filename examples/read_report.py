"""Run a local report viewer that retries a report still being prepared.

The viewer allows four reads and waits 0.1 s, then 0.2 s, then 0.25 s
between them. With no options the report is ready on the third read. Use
``--not-ready-reads 3`` or ``4`` to try the other outcomes, ``--show-waits``
to print each wait, ``--attempts 2`` to receive the second read's
ReportNotReady, or ``--deny-access`` to see a PermissionError arrive at once.

To try a deadline, give each read a duration and set a time budget, for
example ``--read-seconds 0.4 --delay 0.3 --time-budget 1 --show-timeline``.
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
    Each read takes ``read_seconds`` and reports its start and end to
    ``log``, if given.
    """

    def __init__(
        self,
        not_ready_reads: int,
        *,
        deny_access: bool = False,
        read_seconds: float = 0.0,
        log=None,
    ) -> None:
        self.not_ready_reads = not_ready_reads
        self.deny_access = deny_access
        self.read_seconds = read_seconds
        self.log = log or (lambda event: None)
        self.reads = 0

    def load_report(self) -> str:
        self.reads += 1
        read = self.reads
        self.log(f"read {read} starts")
        if self.read_seconds:
            time.sleep(self.read_seconds)
        if self.deny_access:
            self.log(f"read {read} raises PermissionError")
            raise PermissionError(f"report access denied (read {read})")
        if read <= self.not_ready_reads:
            self.log(f"read {read} raises ReportNotReady")
            raise ReportNotReady(f"report is still being prepared (read {read})")
        self.log(f"read {read} returns the report")
        return "Report ready: 3 rows."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--attempts", type=int, default=4, help="reads to allow (default: 4)")
    parser.add_argument(
        "--not-ready-reads", type=int, default=2, help="reads that raise ReportNotReady (default: 2)"
    )
    parser.add_argument("--deny-access", action="store_true", help="make every read raise PermissionError")
    parser.add_argument("--show-waits", action="store_true", help="print each wait to stderr")
    parser.add_argument(
        "--delay", type=float, help="wait this many seconds before every retry (default: 0.1 s doubling to 0.25 s)"
    )
    parser.add_argument("--read-seconds", type=float, default=0.0, help="how long each read takes (default: 0)")
    parser.add_argument("--time-budget", type=float, help="seconds within which retries may start (default: none)")
    parser.add_argument(
        "--show-timeline", action="store_true", help="print each read and wait with its elapsed time to stderr"
    )
    args = parser.parse_args(argv)

    started = time.monotonic()

    def log(event: str) -> None:
        if args.show_timeline:
            print(f"{time.monotonic() - started:5.2f} s  {event}", file=sys.stderr)

    report = PreparingReport(
        not_ready_reads=args.not_ready_reads,
        deny_access=args.deny_access,
        read_seconds=args.read_seconds,
        log=log,
    )
    initial_delay, max_delay = (args.delay, args.delay) if args.delay is not None else (0.1, 0.25)
    policy = RetryPolicy(
        retry_on=[ReportNotReady],
        max_attempts=args.attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
        time_budget=args.time_budget,
    )

    def sleep(seconds: float) -> None:
        if args.show_waits:
            print(f"Waiting {seconds} s before read {report.reads + 1}", file=sys.stderr)
        log(f"waits {seconds} s")
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
