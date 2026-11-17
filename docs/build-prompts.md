# Retry Kit prompts used by Codex

## 1. Retry a caller’s operation

```text
I'd like to build Retry Kit, a small Python library for developers who need to
retry a synchronous operation. For example, a report viewer might retry a read
while a report is still being prepared. A client fetching a record might try
again after a connection drops. I'd like the library to be used for such cases.

Each caller knows the exceptions that determine when it's safe to repeat the
operation and provides a list of such exceptions to the library. The caller
should also choose how many attempts to allow, counting the first call. The
library should retry the operation only if the called function raises one of
those exceptions.

Take the report viewer as an example. Its read function may raise ReportNotReady
if the report is still being prepared. Depending on the time taken to prepare
the report, sometimes the first read succeeds, and sometimes it takes a few
tries. Say the report becomes available between the second and third retries.
With a limit of three attempts, the viewer should get the report eventually.
With a limit of two, it should get the ReportNotReady exception from its
second read. A permission error should reach the viewer immediately.

Give me a design proposal [use $ca-design-proposal].
```

## 2. Let callers choose how long to wait

```text
I'd like callers to be able to choose how long Retry Kit waits between
attempts. A client fetching a record might give a busy service time to
recover. The first call should still start right away. If a caller chooses
an initial delay, each successive wait should double up to a maximum the
caller sets. Callers who leave the delay unset should still get immediate
retries.

Take the report viewer as an example. It allows four reads and chooses an
initial delay of 0.1 seconds and a maximum of 0.25 seconds. If the first
three reads raise ReportNotReady, I'd expect the viewer to wait 0.1, 0.2,
and 0.25 seconds before reads two, three, and four. As soon as a read
succeeds, the viewer should get the report. If all four reads fail, it
should get the fourth exception without another wait. I'd like to check
those waits without sleeping in a test.

Give me a design proposal [use $ca-design-proposal].
```

## 3. Decide whether there’s time for another attempt

```text
I'd like callers who have a deadline to be able to set a time budget for
starting retries. Both the operation and the waits use up that budget. If the
full wait would put the next retry at or past the deadline, the library should
raise the last exception without waiting, even if the caller has attempts
left. A wait can also take longer than requested, so the library should
check that there's still time just before starting a retry.

Take the report viewer as an example. It has a one-second budget and waits
0.3 seconds between reads. Suppose its first read takes 0.4 seconds and
raises ReportNotReady. The second read starts at 0.7 seconds and finishes
at 1.1 seconds. If the report is ready then, the viewer should get it. If
it's still being prepared, the viewer should get the ReportNotReady exception
from that second read without another wait. I'd like to check both outcomes
with a clock we can control.

Give me a design proposal [use $ca-design-proposal].
```
