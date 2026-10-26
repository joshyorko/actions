# Claimed terminal receipt independent tests

Only new isolated source: action_server/tests/action_server_tests/test_robot_claimed_terminal_receipts_327.py. SHA256 b057c69d574a10c99c9fbea7e24c0ff879a4fbb21e8ac486ad2c9781cd0798a5. No production or existing test edits, active checkout mutations, commits, PostgreSQL or actual RCC Robot workloads.

Prepared RCC gateway executes isolated source with asserted runner/authority origins. Final SQLite result:10passed,10PostgreSQL parameters deselected (final.log/results.xml). Initial10passed too; final run uses actual opposite valid State.FAILED rather than an arbitrary invalid state. Lint initially identified pytest fixture-name F811; explicit standard fixture comment corrected it, final lint passed. Configured Ruff formatting and Isort completed. One known anyio assertion-rewrite warning retained.

Evidence covers four fresh Database connections reading persisted PASS/FAIL claimed and optional-no-claim receipts after publication. Completed claim deadline can expire without invalidating terminal provenance. Five independent mutations (claim epoch, queue name, payload inputs, opposite terminal state, nonempty claim owner) each reject through receipt validation after another fresh database connection. Fresh read helper authorizes Run metadata before invoking pure receipt validator, which deliberately receives registry=None. Separate case denies outsider output access, rejects expired output in normal validation, permits explicit private metadata-only acknowledgement and still denies expired artifact read to the authorized actor.

Scope: synthetic FAIL changes result status and is not real failed Robot XML/process proof. This closes review gap3 for SQL receipts/authorized metadata and output separation in SQLite only. It does not establish public HTTP/MCP transport convergence, PostgreSQL concurrency or actual installed RCC lifecycle.

Documentation improvement:
- Canonical file proposed: docs/skills/work-items.md.
- Exact addition: “Claimed Robot terminal provenance is validated after reopening the SQL database: item epoch, queue, payload, final state and cleared owner must still match the retained Run/Attempt receipt. Completed input lease expiry is allowed. Expired output may be acknowledged only through the explicit private metadata path; that acknowledgement neither grants another actor output access nor revives expired artifact reads. Optional no-claim terminal receipts retain their immutable declaration check without creating queue items.”
- Evidence:10SQLite cases in the new isolated test, final.log/results.xml; corruption rejected individually.
- Stale ambiguity removed: field inspection alone is not retained-read proof, and metadata acknowledgement is not output-read authorization.
- Remaining uncertainty:10PostgreSQL parameters deselected; real installed/transport/concurrent gates still separate.

Upstream disposition: none; draft-only, no external report.
