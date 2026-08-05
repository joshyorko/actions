# Task 1 report: Close every filesystem attachment boundary

## Implementation

- Added resolved-containment helpers for attachment names, item directories, and attachment paths.
- Routed SQLite and File adapter attachment add/get/remove/seed/delete paths through the helpers.
- SQLite now checks work-item existence before deriving/removing its directory and verifies every persisted file path before read, removal, or item deletion.
- Added API validation and stable mappings: invalid name 400, missing item/file 404, duplicate upload 409; only validated names are used in `Content-Disposition`.
- Preserved public aliases and FileAdapter JSON item behavior for safe IDs.

## Files

- Created `work-items/src/actions/work_items/_paths.py`.
- Created `work-items/tests/work_items_tests/test_attachment_paths.py`.
- Modified `work-items/src/actions/work_items/_adapters/_sqlite.py`.
- Modified `work-items/src/actions/work_items/_adapters/_file.py`.
- Modified `action_server/src/sema4ai/action_server/_api_work_items.py`.
- Created `action_server/tests/action_server_tests/test_server/test_work_items_files.py`.

## RED / GREEN

RED commands and observed outputs:

```text
PYTHONPATH=work-items/src uv run --with pytest pytest work-items/tests/work_items_tests/test_attachment_paths.py -q
ERROR ... ModuleNotFoundError: No module named 'actions.work_items._paths'

PYTHONPATH=work-items/src:action_server/src uv run ... pytest --confcutdir=action_server/tests/action_server_tests/test_server action_server/tests/action_server_tests/test_server/test_work_items_files.py -q
FAILED ... ValueError: Invalid attachment name
```

The first direct virtual-environment attempt could not run because its interpreter lacked pytest; the Action Server package fixture also requires a missing bundled RCC binary. The recorded RED runs above used isolated UV dependencies and the test-local conftest cutoff; the latter failed at the unhandled adapter validation boundary as intended.

GREEN commands and outputs:

```text
PYTHONPATH=work-items/src uv run --with pytest pytest work-items/tests/work_items_tests/test_attachment_paths.py -q
11 passed, 1 warning

PYTHONPATH=work-items/src:action_server/src uv run ... pytest --confcutdir=action_server/tests/action_server_tests/test_server action_server/tests/action_server_tests/test_server/test_work_items_files.py -q
1 passed, 1 warning
```

## Full verification

```text
PYTHONPATH=work-items/src uv run --with pytest pytest work-items/tests -q
27 passed, 1 warning

PYTHONPATH=work-items/src:action_server/src uv run --with ruff ruff check --select F,I [Task 1 files]
All checks passed!

git diff --check
passed
```

Warnings were pre-existing test-environment configuration (`asyncio_mode`) and upstream Starlette TestClient deprecation warnings.

## Self-review

- Unsafe names cover traversal, absolute and nested paths, both separators, dot segments, empty names, NUL/C0 controls, and quotes.
- Resolved paths detect both lexical traversal and symlink escapes.
- Compromised SQLite `file_path` values cannot read or unlink an outside sentinel, and item deletion verifies all persisted rows before filesystem removal.
- API test exercises the user-visible error mapping, safe header, and full upload/download/delete round trip.

## Concerns

- The full Action Server suite was not run because `action_server/src/sema4ai/action_server/bin/rcc-18.18.1` is absent; the focused API suite is isolated from that unrelated integration fixture using `--confcutdir`.
- The task intentionally does not migrate or clean pre-existing unsafe SQLite rows; it rejects them before filesystem access/deletion.

## Documentation improvement

- Canonical file changed or proposed: Proposed update to `docs/skills/work-items.md` (do not edit while canonical guidance is concurrently managed).
- Durable learning captured: Attachment names are single filename components only: reject empty, dot segments, absolute paths, either separator, quotes, and C0 controls. Resolve the storage root and candidate before containment checks; this catches existing symlink escapes. SQLite persisted paths are untrusted input and must match the resolved expected `<files_root>/<item_id>/<name>` before read, unlink, or recursive item deletion. Verify item existence before deriving/removing its directory. Map API invalid names to 400, missing file/item to 404, duplicate uploads to 409, and construct `Content-Disposition` only from validated names.
- Evidence: `work-items/tests/work_items_tests/test_attachment_paths.py` preserves outside sentinels for traversal, FileAdapter JSON IDs, persisted SQLite paths, and symlink escape; `action_server/tests/action_server_tests/test_server/test_work_items_files.py` verifies 400/404/409, header safety, and round trip.
- Stale or ambiguous guidance removed: Replace advice that treats adapter-supplied or SQLite-stored attachment paths as trusted with the resolved containment rule above.
- Remaining uncertainty: Whether deployed Action Server test environments provide the bundled RCC binary; this does not affect the focused HTTP router test.
