# Generic public enqueue replay marker repair

Isolated patch READY FOR ROOT REVIEW; active checkout unchanged. Actual a46 installed claimed-Robot attempt remains FAILED. This candidate is not installed qualification evidence.

Cause: GenericWorkItemExecution already atomically validates existing FoundryRequest, retained envelope and matching FoundryAudit, then returns only item ID. GenericManagedWorkItemsService creates ItemResult without replay and inherits false. The result therefore identifies the correct retained item but misreports exact retries as fresh admissions.

repair.patch touches only foundry/generic_work_item_execution.py, managed_work_items/generic_service.py and new tests/action_server_tests/test_generic_enqueue_replay_327.py. SHA256 a9cf74cb870c7a62ee0db6d54bfa1417fdd608daea561ee7fd458d0ad052a68d. Baseline and candidate hashes are in source-hashes.json. git apply --check succeeds against current checkout; root must recheck after concurrent changes.

The domain adds frozen private _EnqueueResult(item_id,replay) and _enqueue_result. The existing public enqueue method still returns str, delegating to that helper. True is produced only by the existing validated retained-request/audit branch inside the existing transaction/workspace lock; false only after inserting the existing item/request/audit. Public generic service forwards the marker. There is no preflight query, second request owner, schema change, replacement idempotency identity, or extra write. Existing item and server_time_ms calculation are unchanged.

RED: public boundary test reproduces replay=false on exact repeated enqueue (1 failed,1PostgreSQL case deselected; red.log). GREEN: process-local two-module overlay plus new public boundary and both complete affected generic service/domain files:43passed,3skipped,45deselected in20.90s (green.log/XML). The three skips are explicitly owned prepared RCC execution cases for consumer/producer/optional; they are NOT passes.45PostgreSQL cases deselected. Existing authority revocation, changed-input rejection, audit corruption, atomic rollback and terminal replay tests are included. New test also proves one item/request/audit, preserved item serialization and public enqueue->str compatibility. Ruff check and new-test formatting pass. No PG/RCC materialization/server launched; package commands used the prepared RCC developer gateway.

run-tests.py installs only these two candidate modules into its own Python process before pytest import. Original files remain byte-identical to baseline; no active full-suite imports were modified. An initial overlay-generation indentation error was corrected before successful test collection; this was an isolated harness setup error, not an installed product result. Initial test discovery setup was likewise corrected by loading existing fixture plugins.

Next exact gate: root reviews/applies this focused patch after concurrent source qualification is safe, reruns relevant PG contracts serially, and includes it in a later clean-installed candidate. Re-execute the claimed Robot public path, retaining a46's failure separately. Passing SQLite does not clear installed claimed Robot acceptance.

Documentation improvement:
- Proposed canonical file: docs/skills/work-items.md, generic managed admission/idempotency guidance.
- Exact addition: “Generic items.enqueue reports replay from the existing transactional enqueue request/audit decision. Preserve enqueue's item-ID return compatibility by delegating to a typed internal result; never infer replay through a transport-side preflight read or another idempotency writer. Public boundary tests must assert first=false/retry=true, identical item identity and exactly one retained item/request/audit while preserving changed-input and revoked-authority rejection.”
- Evidence: red public marker failure, green43SQLite contract cases and exact minimal diff.
- Ambiguity removed: returning the same ID alone does not prove a correct public replay marker.
- Remaining uncertainty: PostgreSQL and later installed claimed Robot execution pending root gates.

Upstream disposition: none. Owned Runtime defect; no external issue target or mutation.
