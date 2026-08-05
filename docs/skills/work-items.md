# Work Items

## Current Boundary

`actions-work-items` exposes `actions.work_items`, `actions.workitems`, and `actions_work_items`. Preserve import identity and the producer-consumer lifecycle: reserve input, create parent-linked output, then release done or failed.

The community Action Server management API currently owns SQLite storage under its datadir. Do not imply that its UI/API manages Redis, DocumentDB, or arbitrary custom adapters unless code and integration tests establish that behavior.

SQLite is the release-critical local/server backend. FileAdapter is intended for local, single-process workflows. Redis and DocumentDB exist as optional backends but lack sufficient service-backed reliability coverage on this branch; describe them as experimental until those gates land.

## Safety Invariants

- Attachment names are one safe filename component: reject empty/dot names, absolute paths, either path separator, quotes, and C0 controls. Resolve roots and candidates before containment checks so symlink escapes fail.
- Treat item IDs and persisted SQLite file paths as untrusted. Item directories must resolve to strict descendants of the files root; equality with the root is invalid, so reject IDs such as `""` and `"."`. A persisted path must equal the resolved expected `<files_root>/<item_id>/<name>` before read, unlink, or recursive item deletion; verify item existence before deriving or removing its directory.
- SQLite reservation must acquire `BEGIN IMMEDIATE` before FIFO selection, order by `created_at ASC, rowid ASC` so equal timestamps retain SQLite insertion order without a schema migration, conditionally update the selected `PENDING` row in that same transaction, and roll back on errors; this claims each pending item once across competing processes while retaining the adapter's 30-second SQLite lock timeout.
- Queue and output queue names remain explicit across producer, consumer, scheduler, trigger, and preloaded-action boundaries.
- Action Server REST, scheduler, and trigger paths load the installed Work Items distribution under a private module name so a project-root `actions.py` cannot shadow it; producers seed their datadir-owned SQLite adapter directly instead of mutating library-global context.
- SQLite payload reads preserve every JSON shape exactly and raise `ValueError` for malformed stored JSON; the current Action Server REST model imposes a narrower object-or-null boundary.
- `State.COMPLETED` compatibility and public aliases are migration-sensitive.
- FileAdapter's legacy numbered attachment layout requires pre-mutation migration before index-changing deletion; never derive legacy ownership from a post-deletion index.

## Local Verification

The canonical Work Items release gate runs in the Action Server Dev Container through Poetry. The following is a host-side Docker command; run it from the repository root because its bind mount uses host `$PWD`. The in-container scripts are cwd-independent:

```bash
docker run --rm --user vscode -v "$PWD:/workspaces/actions" -w /workspaces/actions actions-devcontainer:test .devcontainer/bin/smoke
```

`verify-work-items` checks the committed lockfile, Ruff, the Work Items test suite, wheel build, clean-wheel public import aliases, and `git diff --check`. uv bootstraps Poetry in the image but never replaces Poetry resolution or the committed `work-items/poetry.lock` authority.

Action Server loads the installed Work Items distribution under a private module name. When distribution metadata has no copied `actions/work_items/__init__.py`, the loader accepts only its PEP 610 editable local-file `direct_url.json` root and resolves a contained `src/actions/work_items/__init__.py` or `actions/work_items/__init__.py`; it never consults project import paths, keeping shadow packages from controlling the REST adapter path.

Dagger is intentionally absent from editor containers and those containers have no Docker access. Future Dagger automation may call `verify-work-items`, but it must not replace Poetry/package authority or add Docker access to the Dev Container.

From the repository root when Poetry is unavailable for diagnostic-only host checks:

When Action Server tests consume a locally changed Work Items package without a version bump, reinstall the freshly built package before testing; resolver caches can otherwise exercise stale same-version code.

```bash
PYTHONPATH=work-items/src uv run --no-project --with pytest --with pytest-asyncio pytest work-items/tests -q
uvx ruff check work-items/src work-items/tests
```

The package release gate remains Poetry-based and includes `poetry check --lock`, tests, Ruff, build, clean-wheel alias imports, and a clean diff check. Redis/DocumentDB production claims additionally require service-backed tests; deterministic fakes alone are insufficient.

Ruff's configured `UP` fixes in `work-items/src/actions/work_items` are compatible with the package's Python 3.10 floor: built-in generic and `X | None` annotations replace legacy `typing` forms without changing runtime behavior or public aliases.

## Required Regression Areas

- Filesystem traversal, malicious IDs, symlinks, persisted escaped paths, duplicate/missing attachments, and HTTP status/header behavior.
- Multiprocess SQLite reservation and rollback.
- Exact JSON payload round trips and lifecycle exception mapping.
- FileAdapter queue/state filtering, restart behavior, stable attachment ownership, and legacy migration.
- Action Server datadir/queue isolation, triggers, scheduler, process environment clearing, and absent-package behavior.

For HTTP attachments, map invalid names to 400, missing item/file to 404, and duplicate upload to 409. Construct `Content-Disposition` only from a validated filename.

## Evidence

The current hardening plan is `docs/superpowers/plans/2026-08-05-work-items-hardening.md`. It records approved target behavior, not delivered behavior. Update this guide only when the corresponding implementation and verification evidence exists.
