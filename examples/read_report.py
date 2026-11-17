"""Run a local report reader; the first milestone will add retries."""

from importlib import import_module


def load_report() -> str:
    """Supply an example result without an external service."""
    return "Report ready: 3 rows."


def main() -> None:
    # Check the installed package before running the starter's consumer.
    import_module("retry_kit")
    print(load_report())


if __name__ == "__main__":
    main()
