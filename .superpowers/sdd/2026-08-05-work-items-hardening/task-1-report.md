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

## Fix Round 1

### Implementation

- `resolve_item_directory` now requires the resolved item directory to be a strict descendant of the storage root; empty and dot IDs are rejected before SQLite can recursively remove the files root.
- Added sentinel regressions for root-valued item IDs and for `delete_item` with a persisted escaped SQLite path.
- Added Action Server download/delete assertions for a quote-bearing filename, which verify the 400 validation boundary before a response header can be constructed.

### Covering tests

- `test_rejects_storage_root_item_ids_without_deleting_sentinels`
- `test_delete_item_rejects_persisted_escaped_path_without_removing_files`
- `test_work_item_file_api_maps_attachment_errors_and_round_trips`

### RED / GREEN commands and exact outputs

RED:

```text
PYTHONPATH=work-items/src uv run --with pytest pytest work-items/tests/work_items_tests/test_attachment_paths.py -q
...........FF.                                                           [100%]
FAILED ... test_rejects_storage_root_item_ids_without_deleting_sentinels[]
FAILED ... test_rejects_storage_root_item_ids_without_deleting_sentinels[.]
2 failed, 12 passed, 1 warning in 0.03s

PYTHONPATH=work-items/src:action_server/src uv run --with pytest --with fastapi --with python-multipart --with httpx --with termcolor --with pydantic pytest --confcutdir=action_server/tests/action_server_tests/test_server action_server/tests/action_server_tests/test_server/test_work_items_files.py -q
F                                                                        [100%]
FAILED ... assert 200 == 400
1 failed, 1 warning in 0.20s
```

The API RED failure came from a multipart parser normalizing a literal quote from the upload filename; the required quote-bearing download/delete boundary assertions remain URL-routed and pass after validation. Upload validation remains covered by the direct attachment-name regression.

GREEN:

```text
PYTHONPATH=work-items/src uv run --with pytest pytest work-items/tests/work_items_tests/test_attachment_paths.py -q
..............                                                           [100%]
14 passed, 1 warning in 0.02s

PYTHONPATH=work-items/src:action_server/src uv run --with pytest --with fastapi --with python-multipart --with httpx --with termcolor --with pydantic pytest --confcutdir=action_server/tests/action_server_tests/test_server action_server/tests/action_server_tests/test_server/test_work_items_files.py -q
.                                                                        [100%]
1 passed, 1 warning in 0.20s
```

### Full verification

```text
PYTHONPATH=work-items/src uv run --with pytest pytest work-items/tests -q
..............................                                           [100%]
30 passed, 1 warning in 0.04s

PYTHONPATH=work-items/src:action_server/src uv run --with ruff ruff check --select F,I work-items/src/actions/work_items/_paths.py work-items/tests/work_items_tests/test_attachment_paths.py action_server/tests/action_server_tests/test_server/test_work_items_files.py
All checks passed!

git diff --check
passed
```

### Documentation improvement

- Canonical file changed or proposed: Proposed delta to `docs/skills/work-items.md`.
- Durable learning captured: Item-directory containment is strict: after resolution, `<files_root>/<item_id>` must be a descendant of, not equal to, `<files_root>`. Reject `""` and `"."` before any filesystem mutation, because a root-valued persisted item ID could otherwise make item deletion recursively remove all attachment directories.
- Evidence: `test_rejects_storage_root_item_ids_without_deleting_sentinels` retains both a sibling attachment sentinel and an outside sentinel for `""` and `"."`; `test_delete_item_rejects_persisted_escaped_path_without_removing_files` retains both the outside sentinel and the valid item file.
- Stale or ambiguous guidance removed: Replace “remain under storage root” with “resolve to a strict descendant of storage root; equality is invalid for an item directory.”
- Remaining uncertainty: Multipart parsing normalizes a literal quote in the synthetic upload filename, so quote-bearing HTTP behavior is directly verified on download/delete routes and by the adapter-level name validation regression.
