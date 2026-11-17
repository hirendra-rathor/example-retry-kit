"""Smoke-test the installed package and report consumer from another directory.

This subprocess check exercises package discovery and the example's output.
Retry behavior will receive its own tests in the first implementation milestone.
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

    assert completed.stdout == "Report ready: 3 rows.\n"
    assert completed.stderr == ""
