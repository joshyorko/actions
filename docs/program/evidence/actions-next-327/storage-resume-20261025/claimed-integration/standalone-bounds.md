# Standalone Robot escaped-input bound — RED, awaiting integrator fix

Only new isolated source file changed: action_server/tests/action_server_tests/test_robot_standalone_input_bounds_327.py under /workspace/recovery327/claimed-robot-source. No production edits; claimed-public harness unchanged.

Demonstrated with the existing real admitted standalone Robot Package/Deployment fixture:

| Input | UTF-8 JSON bytes, unescaped | Robot canonical escaped bytes | Committed before rejection |
| --- | ---: | ---: | --- |
| ASCII string, 65536 characters | 65548 | 65548 | 1 Run, 1 RunPin, 1 Attempt |
| 12000 `é` characters | 24012 | 72012 | 1 Run, 1 RunPin, 1 Attempt |

StandaloneActionExecution.dispatch_standalone returned a ticket in both cases. The subsequent PinnedRobotRunner.execute raised ValueError “bounded immutable JSON bytes required” during RobotSelection preparation; no adapter was started. The committed admission rows remained. Diagnostic proof: late-rejection-proof.py plus late-rejection.log/XML, 2 passed/2 PostgreSQL parameters deselected.

The allocated new source test now asserts the intended contract: reject before base.admit is invoked, with zero Run/RunPin/Attempt count change. Both SQLite cases are RED: rejected=False, base_admit_calls=1, each row delta=1. Evidence: pre-admission-red.log/XML, 2 failed/2 PostgreSQL parameters deselected. The tests are not xfailed or weakened. Root will implement the shared pure encoder and SQL-projection precheck; this lane holds.

Execution used the prepared RCC package-command gateway with explicit isolated Runtime source-origin assertions. This invokes Python tests only, not an actual Robot/RCC execution or environment publication. No PostgreSQL container or production source mutation. Formatting/import validation corrected fixture imports to explicit re-exports; static result in format-final.log.

Documentation improvement:
- Canonical file proposed: docs/skills/work-items.md.
- Exact delta: “Apply the Robot input limit before admitting either standalone or claimed Runs. Measure the same canonical JSON byte representation consumed by RobotSelection, including object syntax and Unicode escaping; character count or unescaped UTF-8 length is insufficient. A 12000-character accented string can occupy 24012 unescaped JSON bytes but 72012 escaped bytes. Late selection rejection after dispatch can leave committed Run/Attempt state, so test that oversized inputs never call admission and create no Run/RunPin/Attempt rows.”
- Durable learning captured: encoding-consistent limits must guard standalone admission as well as Work Item admission.
- Evidence: two retained diagnostic cases and the red no-side-effects regressions.
- Stale or ambiguous guidance removed: treating sub-65536 UTF-8 payload size or a late runner rejection as safe admission validation.
- Remaining uncertainty: root fix and green qualification pending; no installed or PostgreSQL claim.

Upstream disposition: none. Confirmed local integration defect; no external target or mutation.

## Integrator fix verification

Root subsequently added the SQL-only Robot kind projection and shared encode_robot_inputs check after trusted-worker validation and before register/base.admit in standalone_execution.py. The new pre-admission tests are GREEN: 19 SQLite tests passed (2 boundary regressions plus 17 existing standalone runner regressions), 19 PostgreSQL parameters deselected, in 7.79 seconds. The earlier RED and late-rejection evidence remain unchanged. Targeted standalone_execution.py Ruff format/check, Isort check and mypy all passed; this lane made no production edits. Logs: green.log/XML and production-check.log. Isolated source fix is now verified; installed/PostgreSQL qualification remains separate.
