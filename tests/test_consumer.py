"""Run the installed package's report viewer example from another directory.

These subprocess checks exercise package discovery and the example's output
end to end, including the retries inside it. Retry behavior itself is tested
through the public API in test_retry.py.
"""

from pathlib import Path
import subprocess
import sys

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "read_report.py"


def run_example(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(EXAMPLE), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def test_report_consumer_runs_outside_the_checkout(tmp_path: Path) -> None:
    completed = run_example(tmp_path)

    assert completed.returncode == 0
    assert completed.stdout == "Report ready: 3 rows.\n"
    assert completed.stderr == ""


def test_viewer_with_two_attempts_receives_the_second_reads_exception(tmp_path: Path) -> None:
    completed = run_example(tmp_path, "--attempts", "2")

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr == (
        "Viewer received ReportNotReady after 2 read(s): report is still being prepared (read 2)\n"
    )


def test_viewer_receives_a_permission_error_after_one_read(tmp_path: Path) -> None:
    completed = run_example(tmp_path, "--deny-access")

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr == "Viewer received PermissionError after 1 read(s): report access denied (read 1)\n"
