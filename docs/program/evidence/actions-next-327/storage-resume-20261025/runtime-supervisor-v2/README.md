# Runtime applicable-suite supervisor v2

Prepared only; this lane has not launched PostgreSQL, RCC or the real Runtime suite. Root launches only after independent review and installed workloads finish. Active product checkout is unchanged.

```sh
python /workspace/recovery327/runtime-supervisor-v2/supervise.py \
  --execute --source /workspace/actions \
  --source-sha EXACT_REVIEWED_40_CHARACTER_HEAD \
  --output /workspace/recovery327/runtime-applicable-a47-v2
```

Output must be new and its parent must exist. This uses the existing RCC developer/package-command gateway; it does not install dependencies or alter source/PYTHONPATH. The prepared package interpreter loads the plugin explicitly by file, without inserting plugin directories into the product import path. Metadata/module/pyproject versions must agree, Runtime origin must be the selected source tree, and git HEAD must match the requested SHA before the one owned PostgreSQL container is created. The check repeats in the actual test interpreter and records a source/test fingerprint.

Both preflight layers reject a dirty worktree. After the suite, HEAD, clean-worktree state and the exact source/test fingerprint must equal the initial snapshot. PASS additionally requires an incremental pytest session_finish record with exitstatus zero; an exit-zero gateway without that marker is not a passed suite. SIGTERM and SIGINT route through the bounded cleanup path, with repeated signals prevented from interrupting the database cleanup finally block.

Admission requires 13 GiB free. During execution a sampled 10 GiB floor, 7200-second suite deadline and combined 50 MiB .log cap trigger an ABORTED receipt, separately from test FAILED. No concurrent build is part of this recipe. Browser-origin acceptance and native_artifact_test remain explicitly excluded gates. Pytest uses --maxfail=5. The one owned PostgreSQL container uses the previously pinned image, 768 MiB memory and 512 MiB tmpfs; only its cidfile-recorded ID is stopped and removed, including create-timeout recovery.

The dedicated Linux subreaper sends SIGINT, waits 45 seconds for pytest/JUnit finalization, then TERM/10 seconds and KILL/5 seconds if needed. It also signals and reaps owned descendants in separate sessions. Completed processes with no children receive no duplicate signal. During shutdown, remaining output is drained to avoid blocking pytest; incremental JSONL and JUnit remain independent of that console drain. Failure to clean up is explicitly reported.

Receipts:
- preflight.json and test-preflight.json: source SHA, source origin, package/module/metadata versions and source/test fingerprint.
- progress.jsonl: fsynced setup/call/teardown outcomes and durations, plus collection failures/session finish. Parameter values in node IDs become hashes; no traceback, exception string, fixture value, or environment is serialized.
- pytest.process.json: return code, abort reason, shutdown stages and console log size.
- session.json: terminal status, phase counts, pytest session-finish marker and owned-container cleanup result. Incomplete runs remain incomplete even if many call reports passed.
- junit.xml: normal pytest output when graceful shutdown permits it. JSONL is retained even if JUnit cannot finish.

Console logs redact the generated PostgreSQL password/URL and standard credential-bearing URL/header forms across chunk boundaries. Logs are local evidence, not a guarantee that arbitrary third-party test output contains no other sensitive text; inspect before sharing. Receipts deliberately omit arbitrary test report text.

Local verification command (dummy processes only):
`python /workspace/recovery327/runtime-supervisor-v2/test_supervisor.py`

Canonical documentation proposal: “Before a broad Runtime qualification, compare the selected source version, imported module version and installed distribution metadata in the exact package interpreter. Persist phase outcomes incrementally with parameter values redacted. Resource aborts and cleanup failures are not test passes or test failures; preserve them separately. Give pytest a bounded SIGINT interval to write final reports before escalating, and reap all task-owned sessions under a dedicated subreaper. Stop only the exact database container created by that session.”

Review correction to that proposal: “Reject dirty preflight sources and recheck HEAD, worktree cleanliness and source/test bytes after execution. Require an explicit successful pytest session-finish receipt before PASS. Route external termination through the same bounded cleanup path.”

Documentation-improvement receipt: exact canonical proposal supplied to root; repository docs untouched. Upstream disposition: none. Prior metadata mismatch and lost JUnit were local qualification orchestration concerns.
