# PR273 multi-package `start --actions-sync` reproduction

**Source:** `84b8c70a412db9594dfa2a6c5fcb3e8184db019b` (`fix/multipackage-import-repro-20261010`), unchanged source tree. This is a local unmanaged-package reproduction; it does not exercise a managed RCC environment or establish backend/last-good-generation behavior.

## Reproduction

Added an isolated regression file at `action_server/tests/action_server_tests/test_cli_multi_package_sync.py` (uncommitted, test-only). It creates two minimal packages, each with one `@action`, and exercises the real Action Server CLI/process with a single shared SQLite datadir:

- Additive control: run real `import --dir=A --datadir=D` then `import --dir=B --datadir=D`; both packages and actions remain enabled.
- Failing case: start the real Action Server with `--actions-sync=true --dir=A --dir=B`, then query the shared database after startup.

Command:

```sh
PYTHONPATH=/workspace/work/community-resume/runtime-wheel-test-interpreter/action_server/src:/workspace/work/community-resume/runtime-wheel-test-interpreter/actions/src:/workspace/work/community-resume/runtime-wheel-test-interpreter/action_server/tests \
  /workspace/actions/action_server/.venv/bin/python -m pytest \
  --confcutdir=action_server/tests/action_server_tests -q \
  action_server/tests/action_server_tests/test_cli_multi_package_sync.py -s
```

Result: `1 failed, 1 passed in 4.10s`. The passing sequential-import control confirms the fixture and shared datadir behavior. In the failing start case, the actual CLI logged `Found new action package: package_a`, `Found new action: from_package_a`, then corresponding package B lines, followed by `Disabling action: from_package_a`. Database rows afterward:

```text
packages: package_a, package_b
actions: (from_package_a, package_a, enabled=False), (from_package_b, package_b, enabled=True)
```

The CLI process was the source checkout (`.../runtime-wheel-test-interpreter/action_server/src/actions/server/__main__.py`) and reported Runtime v1.0.3. `--skip-lint` is passed for these deliberately tiny fixtures so lint policy does not obscure the synchronization result.

## Source explanation

`_cli_impl.py:146-153` and `:342-348` both define repeated `--dir` arguments with `action="append"`. `_import_actions` loops over every supplied package directory (`:645-673`). `start` passes `disable_not_imported=True` when `--actions-sync` is true (`:1070-1075`). For each package, `_actions_import.py:534-556` snapshots every action in the database and, when importing a new package, disables every action in that snapshot. The update path also disables every snapshotted action not seen in the current package (`:601-605`). Thus package B's sync pass treats package A's action as omitted even though A was in the same invocation.

## Contract boundary and disposition

This proves the repeated-directory `start --actions-sync=true` CLI path disables an action from a sibling directory in the same requested set. It does not prove a managed RCC package's source-snapshot rollback or runtime-generation last-good behavior. The existing documented additive recipe (sequential `import` commands followed by `start --actions-sync=false`) passes this focused test.

No upstream defect is established; the observed behavior is in this repository's local `_actions_import` synchronization logic. No release or broader runtime acceptance claim follows from this reproduction.

Documentation disposition: do not rewrite the guide to describe the repeated-directory sync path as supported until the semantic fix lands. Afterward, a concise note can state that one `start --actions-sync=true` invocation treats all repeated `--dir` values as the desired package set and removes actions only from packages omitted from that entire set. Existing sequential-import instructions remain accurate and tested.
