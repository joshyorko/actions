# Frozen a35 portable run: interrupted failure

Source6cf0ee25eed23c1814a5b0589047545b57ca5e33. Full selection tests with
not-integration_test marker, tracing plugin disabled, stdout/XML retained.
At93% the PID/create-time guarded watcher sent SIGINT at795,176,960free bytes,
before exhaustion. Reported3327PASS/4FAIL/50SKIP/290DESELECT/41ERROR,1143.39s.
This is not complete acceptance. XML also has one unnamed interrupted testcase;
case-status marks it interrupted-unidentified, never passed. Remaining collected
cases are unexecuted and must be accounted for in the eventual full batch gate.

The4failures were stale migration table/help/Core-floor expectations, corrected
in a36 with focused evidence. The41errors report loss of the owned PostgreSQL
fixture (connection refused after an earlier COMMIT failure). Its root cause is
not established: the old driver removed the container without retaining logs.
No OOM event was found in the inspected owned-container event window; that does
not establish the cause. Future batches must retain health/state/logs before
cleanup and use a fresh owned bounded PostgreSQL fixture per batch.

Complete stdout/XML remain local. Fixture archive is local-only and contains
synthetic private fixture state: never publish its payload. Verification matched
file contents, directory/link modes, symlink targets, hard-link identities and
FIFO metadata before replacing originals. Summary records archive and private
manifest hashes. Initial special-file refusal and interrupted inefficient
random-access gzip verification changed no originals; final streaming verification
succeeded. Human-readable stdout/XML and earlier receipts remain unchanged.

Next full gate requires disjoint batches, collected-node union/uniqueness checks
and retained results for every case. Do not repeat a monolithic run on this budget.
Upstream disposition: none; Actions-owned expectation drift and fixture failure.
