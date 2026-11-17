# Retry Kit

> **Disclaimer:** This repository is a runnable educational example for showcasing the methodology
> of using Continuous Assurance skills. The retry library is for educational use only.
> The code, build prompts, and recorded walkthrough are provided
> to demonstrate the methodology and support learning.

The [Continuous Assurance repository](https://github.com/hirendra-rathor/continuous-assurance) provides two skills for applying a design methodology with a coding assistant. The skills use six design perspectives to connect what a user expects with the parts of the system responsible for that behavior and the tests that show whether it works.

- **Design Proposal** helps you compare a requested change with current behavior, review the design decisions, and agree on how to verify the result before implementation.
- **Explore Design** helps you understand how the system works today by tracing a question through its code, tests, and documentation.

For an introduction to the methodology behind these skills, read [Enforcing Design Methodology with Coding Assistants](https://hirendra-rathor.github.io/articles/enforcing-design-methodology-with-coding-assistants/).

Retry Kit uses a report viewer waiting for a report to be ready as an example scenario for applying Continuous Assurance skills to software design, implementation, and verification. The [Retry Kit walkthrough](https://hirendra-rathor.github.io/examples/retry-kit/) follows the implementation on the `claude` branch. It shows the prompts we gave Claude Code, the proposals and diagrams it produced with the Design Proposal skill, and the report viewer’s terminal output at each milestone.

![A report viewer calls Retry Kit with its load_report function and a retry policy. The library calls that function and returns its result or raises its exception.](docs/assets/retry-kit-brief.svg)

The `codex` branch contains the [implementation built with Codex](https://github.com/hirendra-rathor/example-retry-kit/tree/codex), and the `claude` branch contains the [implementation built with Claude Code](https://github.com/hirendra-rathor/example-retry-kit/tree/claude). In a clone, run `git switch claude` and open `docs/claude-code-build/README.md` to read the three recorded milestones.

## Work through the example

Install the skills by following the instructions in the [Continuous Assurance repository](https://github.com/hirendra-rathor/continuous-assurance).

From a fresh clone of `main`, use the [three build prompts](docs/build-prompts.md) to work through the Retry Kit example one milestone at a time. First, retry a caller’s operation after selected exceptions. Then let callers choose how long to wait between attempts. Finally, add a time budget for starting another attempt.

Give your coding assistant one prompt at a time. Review the proposal, ask for any changes you want, and then have the assistant implement the agreed design. Try the behavior yourself and run the tests before moving to the next prompt.

## License

The library and tutorial materials are available under the [MIT License](LICENSE).
