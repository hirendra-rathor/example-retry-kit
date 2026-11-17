# Authorization and recording method

The user instructed this run:

> I authorize you to proceed from each completed proposal to implementation without
> asking me for a separate approval. Record this as standing authorization from this
> instruction; do not invent a separate user approval message.

The user subsequently requested that the interrupted proposal work be disregarded
and restarted with more detail in the six-perspective diagrams. These recordings
begin with that restarted process. No abandoned proposal or implementation is
presented as part of this run.

Each proposal and implementation report was saved when presented in chat. The
reports keep the original build-session commit subjects. Each chapter’s “Repeat
the checks” section gives the subject of the corresponding implementation on
`codex`. Prompts are extracted verbatim from
`docs/build-prompts.md`. No hidden reasoning or tool-execution transcript is included.

The installed `ca-design-proposal` instructions and reference guides govern the
proposals. Their file hashes and the observed runtime qualification limitation are
in [skill-provenance.json](skill-provenance.json). The source-evidence workflow
requires no Design Graph, and no historical `.assurance/` records are included.

Explanatory diagrams are authored for the new proposals. Application screenshots
capture a browser harness executing the newly implemented Python report examples.
Native terminal capture was unavailable. These are labelled application-output
captures, separately from the diagrams. Captured CLI output is also provided as
accessible text.

The [capture harness](../../../tools/recordings/capture_app.py) finds each implementation
in the `codex` branch history by its [commit subject](checkpoints.json). The library, examples, and tests at each milestone match the versions used for its original capture. The published
screenshots replay the same commands and reproduce the saved output and exit statuses.
The [diagram renderer](../../../tools/recordings/render_diagrams.py) renders the saved figures,
and the [Markdown publisher](../../../tools/recordings/render_recordings.py) assembles the chapters.
