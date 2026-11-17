# Retry Kit — Claude Code implementation

At this milestone, a caller can also set an initial delay between attempts and cap how long each wait lasts.

The library is in [`src/retry_kit/`](src/retry_kit/) and its tests are in [`tests/`](tests/). Run `uv run --locked python examples/read_report.py` to try the report viewer and `uv run --locked python -m pytest -q` to run the checks. The [milestone recordings](docs/claude-code-build/README.md) on this `claude` branch are the source for the [Retry Kit walkthrough](https://hirendra-rathor.github.io/examples/retry-kit/).

For the methodology behind this educational example, read [Enforcing Design Methodology with Coding Assistants](https://hirendra-rathor.github.io/articles/enforcing-design-methodology-with-coding-assistants/).

The library and tutorial materials are available under the [MIT License](LICENSE).
