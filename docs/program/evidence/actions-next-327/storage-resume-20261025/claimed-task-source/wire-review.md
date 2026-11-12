# Claimed Task wire tests

Owned NEW test file only: `/workspace/recovery327/claimed-task-worktree/action_server/tests/action_server_tests/test_claimed_task_wire.py`. Production wire/adapter files were read, not modified.

Prepared gateway result:18SQLite-backed cases passed;18PostgreSQL cases deselected,2.14seconds (`wire.log`, `wire.xml`). No services, worker launches, PG or RCC environment materialization. The runner asserts the adapter import belongs to the isolated worktree. Ruff format/Isort/check completed successfully.

Coverage:

- `detached-claimed` parses into ClaimedDetachedInvocation with exact typed frozen ClaimRef and snapshot, and JSON roundtrips.
- Caller inputs, idempotencyKey, worker/profile and extras reject; invalid/non-strict epochs, invalid item/owner UUID, claim extras and internally inconsistent queue workspace/Deployment reject.
- Existing `detached` inputs/idempotency shape still parses and routes unchanged; mixed claim+standalone request rejects.
- Auth rejection precedes disclosure/validation and no service call occurs for unauthenticated/app callers or invalid mixed shapes.
- Real TaskMcpAdapter routes exactly four claimed arguments to create_claimed and five legacy arguments to create; the recording TaskService subclass is an explicit routing spy, not Task authority or execution proof.
- Discovery expands only the requested authenticated current-extension schema, preserves original tool schema and validates sync/legacy/claimed variants without accepting claimed idempotencyKey.

Scope boundary: ClaimRef internal workspace/Deployment consistency is tested at the wire. Claim queue vs invocation snapshot authority is delegated to real TaskService and is not simulated as a successful authority check here. Integrated SQL admission/cancellation and installed protocol remain root-owned gates.

Static result: final scoped mypy explicitly binds isolated `task_wire.py` and this new test: **PASS, no issues in2source files**. Root corrected the discovered missing DETACHED_INVOCATION TypeAdapter union annotation; this lane did not edit production. Final `wire-typecheck-final.log` is authoritative. An earlier insufficiently bound mypy invocation resolved the old installed wire (`wire-typecheck.log`); the final invocation fixes isolation. `wire-receipt.json` records exact final test, wire and adapter SHA256s.

Canonical guide delta for root-owned docs/skills/repository-operations.md:

> Keep claimed detached Task requests structurally distinct from standalone requests: claimed input comes from the queued envelope, with no second caller inputs or idempotency key. Test strict nested claim identity and scope, rejection before service routing, unchanged legacy routing, and request-scoped schema exposure. Adapter routing spies prove dispatch shape only; authorization, queue/snapshot matching and real worker execution require their separate service and installed gates. When typechecking an isolated namespace-package change, bind the local module explicitly so old installed code cannot masquerade as the candidate.

Documentation-improvement receipt: exact durable proposal backed by18wire/routing cases and the isolated-mypy discovery; shared canonical docs left to root.

Upstream disposition: none. Owned tests and one owned production type annotation finding; no external issue or mutation authorized/performed. External reporting remains draft-only absent target authority.
