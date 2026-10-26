# Isolated claimed Robot runner delivery

Owned files only under `/workspace/recovery327/claimed-robot-source`:
- action_server/src/actions/server/foundry/robot_runtime_runner.py
- action_server/tests/action_server_tests/test_robot_claimed_work_items_327.py

No active checkout source edits. Root owns immutable declaration, issued Robot Work Item authority, generic binding, SQL receipts and release integration. Hashes are in claimed-runner-hashes.json; focused runner patch in claimed-runner.patch. Producer and child Work Item outputs remain unsupported. No subprocess/RCC execution or PostgreSQL qualification is claimed.

The runner prepares the root-owned issued authority outside SQL, binds it for execution, and composes the existing generic adapter's exact claim check and joint queue/Attempt heartbeat. It retains standalone checks and the pure final host-stop callback. Robot receipts carry the ticket's mode and exact claim identity. Publication holds the generic service transaction, requires COMPLETE on a claimed input, performs base Run/Attempt/sealed-output publication, then finishes that exact claim with no child outputs. A queue-finish exception rolls back terminal state and output finalization. Existing retained launch intent still requires reconciliation; no retry, admission or second queue was added.

Tests use real admitted Robot packages, Deployment authorization, queues, Run/Attempt and provider seals with a synthetic adapter. They cover independent claim epoch 2/Attempt epoch 1; consumer/required-input/optional claimed and optional no-claim PASS/FAIL; actual heartbeat deadline renewal; no provider opens inside SQL or after adapter starts; queue-finish rollback; final stop; COMPLETE denial; stolen/expired claim; READ/CLAIM denial before adapter; and unissued/cross-owner/wrong-ticket/source-pin/nested authority binding rejection. Root declaration tests cover unsupported producer/output admission.

Earlier outcomes remain traceable: first run failed claimed dispatch before runner while root receipt extension was incomplete (2 pass/11 fail); second had two incorrect required-input fixture mappings (11 pass/2 fail); third had one wrong expected SQLRecordPin exception (19 pass/1 fail). Corrections changed test expectations/fixtures, not authority guards. Formatter/isort/Ruff passed after correcting absent isolated config path and an unused test variable. Final combined new + standalone regression result is in claimed-runner-final.log/XML.

Documentation improvement:
- Canonical file proposed: docs/skills/work-items.md.
- Exact delta: “Claimed Robot execution binds host-issued immutable Work Item authority before entering lifecycle checks. The authority is prepared outside SQL and tied to the exact service, caller and ticket; package metadata pins and current queue/Attempt authority are rechecked in SQL. Use the existing generic adapter to renew both leases. Publish Robot Run/Attempt/output state and finish the exact input claim in one transaction after COMPLETE authorization; queue-finish failure must leave the Run running and outputs provisional. Keep claim epoch separate from Attempt epoch. Optional no-claim execution is allowed only by its immutable declaration. Producer and child Work Item outputs require a separate result contract and remain unsupported by this bounded join.”
- Durable learning captured: safe issued-authority composition and atomic claim completion without Python receipt validation or provider IO in SQL.
- Evidence: isolated implementation, claimed-runner-first/second/third/final logs, final XML, test provider barriers and rollback assertions, root-owned authority/binding.
- Stale or ambiguous guidance removed: supersedes the earlier HOLD proposal only for isolated source implementation; does not claim installed or PostgreSQL acceptance.
- Remaining uncertainty: root integration/review, installed actual RCC execution, public Work Item transport convergence, PostgreSQL, and producer/child output scope remain separate gates.

Upstream disposition: none. Local integration only; no external mutation or confirmed upstream defect.

Final verification: **37 passed, 37 PostgreSQL parameters deselected**, one pre-existing pytest anyio rewrite warning, in 42.89 seconds. This comprises 20 new claimed/authority SQLite cases and 17 existing standalone runner SQLite regressions. RCC toolkit gateway succeeded; this gateway runs Python tests and is not real Robot RCC execution proof. Both owned files passed configured Ruff formatting/check and Isort. Source origins explicitly asserted inside isolated checkout. No owned process or database workload remains running.
