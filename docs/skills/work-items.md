# Work Items

## Current Boundary

`actions-work-items` exposes `actions.work_items`, `actions.workitems`, and `actions_work_items`. Preserve import identity and the producer-consumer lifecycle: reserve input, create parent-linked output, then release done or failed.

The community Action Server management API currently owns SQLite storage under its datadir. Do not imply that its UI/API manages Redis, DocumentDB, or arbitrary custom adapters unless code and integration tests establish that behavior.

SQLite is the release-critical local/server backend. FileAdapter is intended for local, single-process workflows. Redis and DocumentDB exist as optional backends but lack sufficient service-backed reliability coverage on this branch; describe them as experimental until those gates land.

## Safety Invariants

- Attachment names are one safe filename component: reject empty/dot names, absolute paths, either path separator, quotes, and C0 controls. Resolve roots and candidates before containment checks so symlink escapes fail.
- Treat item IDs and persisted SQLite file paths as untrusted. Item directories must resolve to strict descendants of the files root; equality with the root is invalid, so reject IDs such as `""` and `"."`. A persisted path must equal the resolved expected `<files_root>/<item_id>/<name>` before read, unlink, or recursive item deletion; verify item existence before deriving or removing its directory.
- SQLite reservation must claim one pending item once across competing processes.
- Queue and output queue names remain explicit across producer, consumer, scheduler, trigger, and preloaded-action boundaries.
- Python adapters preserve JSON values; the current Action Server REST model may impose a narrower object-or-null boundary.
- `State.COMPLETED` compatibility and public aliases are migration-sensitive.
- FileAdapter's legacy numbered attachment layout requires pre-mutation migration before index-changing deletion; never derive legacy ownership from a post-deletion index.

## Local Verification

From the repository root when Poetry is unavailable:

```bash
PYTHONPATH=work-items/src uv run --no-project --with pytest --with pytest-asyncio pytest work-items/tests -q
uvx ruff check work-items/src work-items/tests
```

The package release gate remains Poetry-based and must include `poetry check`, tests, Ruff, build, and clean-wheel alias imports on supported Python versions. Redis/DocumentDB production claims additionally require service-backed tests; deterministic fakes alone are insufficient.

## Required Regression Areas

- Filesystem traversal, malicious IDs, symlinks, persisted escaped paths, duplicate/missing attachments, and HTTP status/header behavior.
- Multiprocess SQLite reservation and rollback.
- Exact JSON payload round trips and lifecycle exception mapping.
- FileAdapter queue/state filtering, restart behavior, stable attachment ownership, and legacy migration.
- Action Server datadir/queue isolation, triggers, scheduler, process environment clearing, and absent-package behavior.

For HTTP attachments, map invalid names to 400, missing item/file to 404, and duplicate upload to 409. Construct `Content-Disposition` only from a validated filename.

## Evidence

The current hardening plan is `docs/superpowers/plans/2026-08-05-work-items-hardening.md`. It records approved target behavior, not delivered behavior. Update this guide only when the corresponding implementation and verification evidence exists.
