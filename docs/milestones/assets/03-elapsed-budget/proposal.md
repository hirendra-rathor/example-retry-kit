Callers with deadlines need Retry Kit to stop admitting retries when time is spent while retaining a successful result from work already admitted.

![Six-perspective proposal for elapsed-time budgets. Green marks new admission rules, timing state, clock dependency, and checks; blue marks changes to retry control; gray marks retained outcomes and execution boundaries.](overview.png)

**Intentions and rules.** This proposal starts from the milestone 2 implementation on `codex`, with capped backoff and 63 passing tests. Today attempts and selected failures bound retry admission, but operation duration and oversleeping cannot stop another call. The new budget will cover both operation time and actual waiting. After an eligible failure with attempts remaining, the full next wait must put the prospective retry strictly before the deadline. Equality denies admission. A wait that does not fit will be skipped, never shortened.

The second intention is to preserve useful completed work. A call admitted before the deadline can finish afterward, and its successful result must still return. This is an admission budget, not a timeout that interrupts a running callback.

![Collaboration proposal for elapsed-time budgets. A per-invocation Budget reads a monotonic clock before waiting and before retrying; the second read starts at 0.7 seconds and its success at 1.1 seconds returns unchanged. Green marks additions, blue changes, and gray context.](collaboration.png)

**Architecture and decision order.** The executor retains control of attempt admission; a new internal `Budget` owns elapsed-time observation. Its clock defaults to `time.monotonic`, with a caller-supplied clock for controlled tests. After a selected failure, the executor checks the attempt limit first, asks whether the complete next interval fits, waits if that interval is positive, and then asks whether time remains immediately before retrying. The final check also runs for zero-delay retries. Only callback exceptions enter retry classification. Clock or waiting failures propagate as dependency failures even when their types appear in `retry_on`.

For the prompt’s case, the first read starts at `0.0` and fails at `0.4`. A `0.3` wait fits; the second read is admitted at `0.7`. A success at `1.1` returns unchanged. If that read instead fails, no further wait fits and its exception is re-raised. If the first wait overshoots to `1.0` or later, the second read never starts and the first exception is preserved.

**Subsystem Design.** The interval calculation remains unchanged; timing is a separate responsibility.

| Package or module | Components: existing → proposed responsibility |
| --- | --- |
| `policy.py` — changed | Validates attempts and waits → also normalizes an optional finite elapsed budget. |
| `budget.py` — new | No elapsed-time owner → `Budget` samples the start, validates clock readings, and makes strict admission comparisons. |
| `execution.py` — changed | Count check followed by waiting → count check, prospective-time gate, waiting, actual-time gate, then retry. |
| `waiting.py` — context | Keeps the existing capped interval sequence; budget denial cannot shorten an interval. |
| `examples/read_with_budget.py` — new | Adds deterministic late-success, late-failure, equality, and oversleep rehearsals using controlled time. |

**Subsystem Interfaces.** `RetryPolicy` gains `time_budget=None`; `retry` gains keyword-only `clock=time.monotonic`. `None` disables timing completely, including clock reads. Zero is valid and permits only the initial call: a success returns, while a failure cannot be retried. Negative, nonfinite, boolean, or nonnumeric durations are rejected before operation execution. A clock returns finite, nondecreasing numeric seconds from an arbitrary epoch. A noncallable clock or invalid reading fails when timing is enabled; disabled timing does not depend on that provider. Existing calls and real-wait examples retain their behavior.

**State Management.** Each enabled invocation samples a fresh baseline immediately before its initial operation. The budget retains that baseline and its last observed reading; the policy holds only the immutable duration. Comparisons use `now - started + delay < limit`, avoiding an absolute deadline sum at a potentially large clock epoch. The post-wait check uses zero delay. A backwards or nonfinite clock reading raises a dependency error rather than silently admitting work. The original eligible exception remains active through both gates for bare re-raising. No check after a successful return can discard that value.

**Verification.** Run `uv run --locked python -m pytest -q` for the complete suite. Budget checks use a controlled clock and recorded waits; the retained consumer smoke still exercises real sleeping.

| Tests and layer | Expected observation |
| --- | --- |
| Policy / budget unit checks | Accept `None` and zero; reject invalid durations; enforce strict comparison and reject invalid or decreasing readings. |
| Public acceptance integration | Both one-second scenarios make two calls and request one `0.3` wait; success returns at `1.1`, failure preserves the second exception. |
| Boundary integration | Exact `0.5 + 0.5 == 1.0` denies without waiting; an inside value admits; oversleeping and zero-delay expiry prevent another call. |
| Compatibility / dependency integration | Disabled timing reads no clock; limits still take precedence; policy reuse resets the baseline; clock and sleeper failures escape. |
| Installed consumers / wheel | Both example scripts run from an installed wheel; the new script prints four deterministic outcomes without sleeping. |

Binary-exact values establish equality boundaries; decimal scenario times will use appropriate approximate assertions. Clock precision and scheduling overhead limit actual start-time precision. The library cannot guarantee a hard wall-clock deadline or stop an operation already running; callers must supply any per-attempt timeout.

**Authorization.** I will implement this proposal using your standing authorization, verify it, and record the actual results before assembling the offline walkthrough.
