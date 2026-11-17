"""Smoke-test the installed package and report consumer from another directory.

This subprocess check exercises package discovery and the example's output.
The real consumer exercises success, exhaustion, and an unrelated failure.
"""

from pathlib import Path
import subprocess
import sys


def test_report_consumer_runs_outside_the_checkout(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "read_report.py"

    completed = subprocess.run(
        [sys.executable, "-I", str(example)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        "Recovery: Report ready: 3 rows. Calls: 3.\n"
        "Exhaustion: ReportNotReady: Report not ready on read 2. Calls: 2.\n"
        "Permission: PermissionError: Report access denied. Calls: 1.\n"
    )
    assert completed.stderr == ""
