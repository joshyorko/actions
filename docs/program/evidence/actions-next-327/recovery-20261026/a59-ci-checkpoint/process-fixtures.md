# Windows process and Robot fixture lane

Scope: the three assigned tests in `action_server/tests/contract_tests/` only:
`test_generated_failure_cleanup.py`, `test_robot_cleanup_race_327.py`, and
`test_robot_runtime_profile.py`. No production code or other test file was
changed. The source call paths and platform guards were read before changing
fixture admission, along with the repository guide and the prior Windows scope
audit at `windows-scope-current-luna.md`.

## Changes

- The six real child/pipe/process-group receipt cases now skip at the test
  boundary on non-POSIX systems, before `child()` launches a subprocess. The
  same six receipt and cleanup decisions run in a platform-neutral test using
  a controlled cleanup result, so valid, missing, wrong-artifact, wrong-exit,
  invalid-trust, and uncertain-cleanup outcomes remain covered on Windows.
- The two synthetic Robot cleanup race tests that invoke POSIX group syscalls
  are marked POSIX-only. The non-owned-group test remains cross-platform: on
  Windows its mock syscall attributes can be absent, and the existing
  production guard must refuse cleanup without signaling.
- The exact Robot runtime profile test now uses absolute paths under `tmp_path`.
  This preserves the host-path contract on Windows, where POSIX-root strings
  such as `/owned/python` are not necessarily absolute Windows paths.
- Existing Linux subreaper, POSIX process-group reuse, cleanup ownership,
  receipt matching, and production refusal assertions remain. No whole-module
  skip or weakened PID/group identity check was introduced.

The production guards support these test boundaries. `RobotExecution` rejects
host supervision outside Linux x86_64 and its `_cleanup` requires a POSIX owned
session (`foundry/robot_execution.py:359-360,739-740`). `_OwnedProcessCapture`
only owns sessions on POSIX and uses process-group capture before receipt
decisions (`foundry/rcc_execution.py:87-120`). The Windows cleanup failure
occurred when the real-pipe capture reached `select()` on Windows pipe handles;
the regression formerly spawned that child before any platform admission.
The receipt validator itself can be exercised with a controlled ownership
result and remains covered separately.

## Verification

Focused command, run from `action_server/`:

```text
./.venv/bin/pytest tests/contract_tests/test_generated_failure_cleanup.py tests/contract_tests/test_robot_cleanup_race_327.py tests/contract_tests/test_robot_runtime_profile.py -q
27 passed in 10.16s
```

There were **0 skips on the POSIX verification host**. The focused Ruff lint,
Ruff format check, isort check, and `git diff --check` for the three owned files
all passed. I did not run a Windows interpreter. With current test collection,
the Windows markers are expected to skip 11 cases: six real POSIX
pipe/group-capture cases, two existing Linux subreaper cases, one existing
POSIX-group reuse case, and two POSIX Robot group-race cases. The six portable
receipt-decision cases and the cross-platform non-owned/refusal, profile, and
other platform-neutral tests remain enabled. This is an expected marker count,
not an observed Windows run.

RCC verification could not run in this environment: `poetry` is absent from
PATH, and `/usr/bin/rcc` is the Qt resource compiler rather than Robocorp RCC.
The package-local `.venv` supplied the focused pytest and lint tools, so the
results are diagnostic package-environment evidence rather than a fresh RCC
toolkit receipt. Native Windows behavior remains unverified.

## Canonical documentation proposal

No canonical guide was edited in this bounded test lane. Extend the existing
platform-fixture guidance in
[`docs/skills/repository-operations.md`](../actions/docs/skills/repository-operations.md)
after “Shared Linux-only fixtures check their own platform because module-level
pytest marks do not travel with an imported fixture.” with:

> A test that captures POSIX subprocess pipes or owns a POSIX process group must check that capability before spawning the child. Keep receipt parsing, artifact/exit-code matching, and cleanup-result decisions in a separate platform-neutral test when those contracts do not require the POSIX process. Keep assertions for production unsupported-platform guards enabled on Windows. For host-path configuration fixtures, build absolute paths from `tmp_path` instead of POSIX-root literals. Treat these host-run results as focused fixture evidence; only a native platform run establishes Windows behavior.

Evidence: current selector/process-group use and `os.name` guards in
`foundry/rcc_execution.py:87-120`, `foundry/robot_execution.py:359-360,739-740`;
the original Windows report's `WinError 10038` at pipe selection; the new
portable receipt-decision test; and the absolute path requirement in
`foundry/robot_runtime_profile.py:31-47`. The wording records the distinction
between POSIX lifecycle evidence and portable receipt decisions without
claiming native Windows process cleanup support. No stale guide statement needs
removal.

Upstream disposition: none. The issues are Actions test-fixture admission and
host-specific path data; no upstream defect was found and no external target was
authorized.

Documentation improvement:
- Canonical file changed or proposed: exact paragraph proposed for `actions/docs/skills/repository-operations.md` after the shared Linux-only fixture guidance.
- Durable learning captured: gate POSIX pipe/group setup before child spawn; preserve receipt decisions in portable tests; assert production refusals on Windows; use native absolute test paths.
- Evidence: source guards/callsites, observed Windows `WinError 10038`, focused tests, and host path validation code listed above.
- Stale or ambiguous guidance removed: none identified; the proposal makes the fixture capability boundary and portable contract boundary explicit.
- Remaining uncertainty: no native Windows host was available for this run; the projected Windows skip count is not a Windows execution result.
