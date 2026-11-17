# Retry Kit — Codex implementation

Codex built this Python retry library from three prompts using the Continuous Assurance Design Proposal skill. A caller chooses which exceptions to retry, how many attempts to allow, and how long to wait between attempts. A time budget limits when another attempt can start. A report read that starts in time can still return its result after the deadline.

The library is in [`src/retry_kit/`](src/retry_kit/) and its tests are in [`tests/`](tests/). Run `uv run --locked python examples/read_report.py` to try the report viewer and `uv run --locked python -m pytest -q` to run the checks. The [three recorded milestones](docs/milestones/README.md) document the Codex build. The [Retry Kit walkthrough](https://hirendra-rathor.github.io/examples/retry-kit/) follows the `claude` branch.

For the methodology behind this educational example, read [Enforcing Design Methodology with Coding Assistants](https://hirendra-rathor.github.io/articles/enforcing-design-methodology-with-coding-assistants/).

The library and tutorial materials are available under the [MIT License](LICENSE).
