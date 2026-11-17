# Retry Kit: Claude Code build

This folder records the independent **Claude Code** implementation of the Retry Kit milestones in the [build guide](../build-prompts.md). Each chapter keeps the prompt, the design proposal and its diagrams, the authorization to implement, the implementation report, and terminal captures of the working library.

## Milestones

| Milestone | Recording |
| --- | --- |
| 1. Retry a caller’s operation | [Milestone 1 chapter](milestone-1-retry-a-callers-operation.md) |
| 2. Let callers choose how long to wait | [Milestone 2 chapter](milestone-2-let-callers-choose-how-long-to-wait.md) |

The recordings in this folder supply source material for the [Retry Kit walkthrough](https://hirendra-rathor.github.io/examples/retry-kit/).

## Starting point

The `claude` and `codex` branches start at the same commit, “Create the Retry Kit starter”. The `starter` tag marks that point. Claude Code worked from the starter and its prompts.

Each milestone commit includes the implementation, its tests, and the recording in this folder. On the `claude` branch, run `git log --oneline --reverse starter..HEAD` to see them in order.

## How these recordings were made

- **Recorded and editorial text.** Quoted blocks are the Claude Code responses saved when they were presented. Each chapter identifies the milestone commit by its subject on `claude`.
- **Diagrams and terminal captures.** The `diagrams/` folder contains the proposal figures as SVG and PNG. The `screenshots/` folder holds rendered terminal output from the report viewer and tests, alongside the plain-text transcripts.
- **Prompts and authorization.** The published prompts use `/ca-design-proposal`, the command invoked in Claude Code. This branch’s build guide contains the recorded prompts. Run `git show starter:docs/build-prompts.md` for the practice guide. The build instruction gave standing authorization to implement each completed proposal.

## Build environment

The build session recorded the following environment.

| Item | Value | How it was checked |
| --- | --- | --- |
| Coding assistant | Claude Code 2.1.325, Claude desktop app | Build session record |
| Model | Claude Opus 5.5 (`claude-opus-5-5`) | Build session record |
| Design Proposal skill | `ca-design-proposal` | Installed skill marker `ca-design-proposal:v1` |
| Python, pytest, uv | 3.12.13, 9.2.0, 0.11.16 | Toolchain recorded during the build |
