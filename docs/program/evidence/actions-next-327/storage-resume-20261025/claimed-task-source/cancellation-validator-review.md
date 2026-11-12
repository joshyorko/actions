# Claimed cancellation evidence implementation

Owned new files only in isolated claimed-task-worktree:

- `action_server/src/actions/server/run_outputs/claimed_task_state.py`
- `action_server/tests/action_server_tests/test_claimed_task_state.py`

API: `validate_claimed_cancellation(service, intent, run, pin, fence=None)` returns exactly `pending_cancelled` or `active_unconfirmed`, otherwise raises `FenceRejected`. Requires exact GenericWorkItemExecution, validated ClaimedTaskIntent and an already-open service DB transaction. Caller retains responsibility for Task identity/TTL and live Run/queue read or cancel authorization. The helper does not grant authority or return artifacts.

SQL evidence: current Run/Pin equality, immutable admission/fingerprint/canonical item Run key, original queue/workspace/policy/input digest, consumer Robot/no-output declaration, original claim epoch, cancelled FAILED queue with cleared owner/deadline and exact cancellation marker. Pending cancellation requires CANCELLED, no Attempt, epoch0 and no journal. Active cancellation requires exact RUNNING Attempt/fence/owner and canonical timestamps consistent with admission/lifecycle, closed claim-bound Robot journal and (if present) exact retained launch/selection. Expired Attempt leases are read-only historical facts; no live lease is acquired or renewed. Existing strict Robot execution validator remains unchanged.

Reused SQL metadata projection and Robot journal parsers. No provider/schema calls or live `_fence` invocation, no database writes. Tests prohibit those methods and assert before/after SQL rows unchanged. Launch tests include a valid retained launch and altered selection rejection; negatives cover ordinary failure, newer epoch, owner/queue/payload, cancellation pin, fence/journal/state/timestamp and forged launch. Pending/no-attempt and expired-lease reads are positive controls.

Prepared RCC gateway executes `validation/run.py`, explicitly asserting product module origins under the isolated worktree before pytest. SQLite-only selectors exclude PostgreSQL. Initial16PASS/16PGskip receipt retained; final17SQLite cases supersede it. No RCC environment materialization, business Robot execution, service, PG or shared checkout mutation. Full Task integration/public installed gates remain root-owned and unverified by these component tests.

Scoped static checks use existing package Ruff formatter/checker, Isort and mypy with isolated cwd/config and explicit namespace package bases. Initial attempted Black was unavailable; no installation/fallback package added. Initial scoped mypy namespace discovery and nullable queue findings were corrected in the invocation/explicit fail-closed queue guard respectively; final logs are authoritative.

Canonical guide supplement to parent-owned docs/skills/repository-operations.md:

> A cancelled claimed Task cannot be validated as live work: cancellation intentionally clears the Work Item owner and lease. Use a read-only retained-evidence check to distinguish proven no-Attempt cancellation from active outcome-unconfirmed state. Revalidate original queue/item/epoch/payload, pinned Run and Attempt, and any recorded launch selection; do not weaken the normal live-claim validator. Require caller authorization and an existing SQL transaction, and never turn these metadata facts into execution, lease renewal or output access rights.

Documentation-improvement receipt: exact delta above backed by module/read-only SQL regression evidence; shared guides left to root. Upstream disposition: none; owned integration, no external mutation/report authorized or performed.
