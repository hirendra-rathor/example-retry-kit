"""Publish the Codex milestone chapters from their saved prompts, responses, and captures."""

import json
from pathlib import Path
import re

MILESTONES = Path(__file__).resolve().parents[2] / "docs" / "milestones"

# The link text describes what the reader can inspect in each chapter.
READING = {
    "01-bounded-retries": "Proposal, implementation, and report viewer output",
    "02-capped-backoff": "Capped waits, recovery, and exhaustion",
    "03-elapsed-budget": "Late success, deadline denial, and oversleep",
}


def render_chapter(checkpoint, baseline, neighbors):
    number = checkpoint["number"]
    slug = checkpoint["slug"]
    prefix = f"assets/{slug}"
    assets = MILESTONES / prefix
    prompt = (assets / "prompt.txt").read_text().strip()
    proposal = (assets / "proposal.md").read_text().strip()
    proposal = re.sub(
        r"\]\((overview|collaboration)\.png\)",
        lambda match: f"]({prefix}/{match[1]}.svg)",
        proposal,
    )
    report = (assets / "implementation.md").read_text().strip()
    # Split the report at the figure that starts the Working result section.
    figure = re.search(r"^!\[.*?\]\(application\.jpg\)$", report, re.MULTILINE)
    if figure is None:
        raise ValueError(f"Missing application capture in {slug}")
    working_result = report[figure.start():].replace("](application.jpg)", f"]({prefix}/application.jpg)")
    execution = json.loads((assets / "execution.json").read_text())
    if execution["milestone"] != number or execution["stdout"] != (assets / "output.txt").read_text():
        raise ValueError(f"Capture and checkpoint disagree in {slug}")
    sections = [
        f"# {number:02d} · {checkpoint['title']}",
        "## Prompt", f"```text\n{prompt}\n```",
        "## Recorded proposal", proposal,
        "## Recorded implementation report", report[:figure.start()].rstrip(),
        "## Working result", working_result,
        f"[Captured output]({prefix}/output.txt) · [Command and exit status]({prefix}/execution.json)",
        "## Repeat the checks",
        f"The proposal started from {baseline}. The build session recorded **{checkpoint['tests']} passing tests**. To repeat the checks at this milestone, check out `{checkpoint['subject']}` from the history of the `codex` branch and run these commands.",
        f"```sh\n{execution['command']}\nuv run --locked python -m pytest -q\n```",
        f"[Original prompt]({prefix}/prompt.txt) · [Saved proposal]({prefix}/proposal.md) · [Saved implementation report]({prefix}/implementation.md)",
        " · ".join(["[Recording index](README.md)", *neighbors]),
    ]
    (MILESTONES / f"{slug}.md").write_text("\n\n".join(sections) + "\n")


def main():
    checkpoints = json.loads((MILESTONES / "assets/checkpoints.json").read_text())
    rows = ["| Milestone | Reading and evidence |", "| --- | --- |"]
    for i, checkpoint in enumerate(checkpoints):
        neighbors = []
        baseline = "the shared starter"
        if i:
            previous = checkpoints[i-1]
            baseline = f"[milestone {previous['number']}]({previous['slug']}.md)"
            neighbors.append(f"[Previous milestone]({previous['slug']}.md)")
        if i + 1 < len(checkpoints):
            neighbors.append(f"[Next milestone]({checkpoints[i+1]['slug']}.md)")
        render_chapter(checkpoint, baseline, neighbors)
        slug = checkpoint["slug"]
        rows.append(f"| {checkpoint['number']} · {checkpoint['title']} | [{READING[slug]}]({slug}.md) |")

    index = [
        "# Retry Kit · the Codex build",
        "Three prompts develop the shared starter into a Python retry library. Each chapter records a fresh proposal, its implementation report, and observed checks. The proposals use the installed Design Proposal skill and the user’s [standing authorization to implement](assets/authorization.md).",
        "Recorded checks describe the build session. Descriptions and navigation have been edited for publication. Use the milestone chapters to follow the build.",
        "\n".join(rows),
        "Run `git log --oneline --reverse starter..HEAD` on the `codex` branch to see the milestones in order. Each commit includes the implementation and its recording. To run an earlier milestone, use `git switch --detach` with the commit ID shown for its subject, then `git switch codex` to return to the completed build.",
        "[Build prompts](../build-prompts.md) · [Milestone commit subjects](assets/checkpoints.json) · [Skill provenance](assets/skill-provenance.json)",
    ]
    (MILESTONES / "README.md").write_text("\n\n".join(index) + "\n")


if __name__ == "__main__":
    main()
