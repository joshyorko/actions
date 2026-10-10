# Independent review: staged RCC consumer SQLite fixture

Disposition: **APPROVE the fixture-only checkpoint for source review and later hosted control dispatch. The real-RCC two-case acceptance remains NOT RUN.**

## Exact source and change scope

- Published source: commit `2552a8c3419b213825294a51927843b2d61f662e`, tree `af7e419414261525c89db5511c5cbbc6f07981b0`, parent `e886d26ebaefafa9189a69517f6707691b53662e`.
- Fixture repair: commit `1284310db62220534977e8db52fd33351e59a4a1`, tree `cdd4d65d914df9be3eaa4cf979d6b224fde431c3`, parent `e886d26ebaefafa9189a69517f6707691b53662e`.
- Comparing the exact trees shows only `action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py` and `docs/skills/repository-operations.md` changed. Runtime source, Actions source, helper source, their package metadata and lockfiles are identical to 2552. Relevant `_models.py` and `_database.py` blob IDs match across both commits.
- The new helper creates `runtime-data` before `Database` opens its file, registers `get_all_model_classes()`, and creates tables using current DB rules. The service-free regression asserts `mcp_catalog_name` exists. The RCC test reuses that same helper, replacing its incomplete hand-selected registry.

## Independent execution

Command, from `action_server/`, using the prepared worker-exit venv and the exact repair checkout as first-party source roots:

```sh
PYTHONPATH=/workspace/work/staged-rcc-dbdir-repair-20261010/action_server/src:/workspace/work/staged-rcc-dbdir-repair-20261010/actions/src:/workspace/work/staged-rcc-dbdir-repair-20261010/actions-http-helper/src:/workspace/work/staged-rcc-dbdir-repair-20261010/devutils/src \
PYTHONDONTWRITEBYTECODE=1 \
/workspace/work/community-resume/worker-exit/action_server/.venv/bin/python -m pytest \
  --confcutdir=tests/action_server_tests \
  --basetemp=/dev/shm/luna-staged-rcc-fixture-20261010 \
  -q tests/action_server_tests/test_source_staging_rcc_consumer.py::test_runtime_catalog_database_fixture_creates_directory_and_current_schema
```

Result: `1 passed, 1 warning in 0.24s`; warning is the unknown `integration_test` mark because `--confcutdir` excludes repository conftest registration. Import-origin preflight resolved both `_database.py` and `_models.py` from the repair checkout and confirmed `McpCatalogName` is in `get_all_model_classes()`. The run did not invoke RCC, provider services, or environment creation.

## Failure and D10 evidence boundaries

The preserved hosted failure receipt is `/workspace/work/ci-current-readonly/rcc-provider-rollback-run38068024443-job114259549777-failure-20261010T165013Z.txt`, SHA-256 `218a4719f82b6d9bac95d521992e25115abfbe26c1b1704892d0415c3b2c5d2b`. It records the test constructing SQLite under a missing `runtime-data` parent and an `unable to open database file` error; it also confirms the RCC/source pin assertions passed. The regression addresses this local fixture prerequisite and includes the current model registry. It does not demonstrate the managed-RCC case.

D10 probe `/workspace/work/d10-samefile-repro-evidence/initial-probe.json`, SHA-256 `98493f5f9f6440ba1514741660da0f4aeab3749e58b9062389534fe465b1897d`, records one Linux source-mode `actions.server import` on current `e886d26` with a source package inside the datadir. It passed and stored a datadir-owned `.rcc-runtime-sources` snapshot, so it disconfirms failure only for that current-source/inside-datadir scenario. The probe explicitly did not run an outside-datadir control, historical wheel, frozen binary, non-Linux platform, or full start/restart acceptance. It does not prove the historical wheel issue fixed or broad RCC acceptance. Its recorded incidental RCC download is not relied upon as acceptance evidence.

## Required dispositions

Upstream disposition: none. Evidence points to a local test fixture omitting directory creation and the current model registry; no upstream defect is established.

Documentation improvement:
- Canonical file changed or proposed: `docs/skills/repository-operations.md` (changed by checkpoint 1284310).
- Durable learning captured: create the private SQLite data directory before opening the consumer DB, initialize from `get_all_model_classes()`, and keep this service-free fixture regression separate from managed-RCC execution proof.
- Evidence: preserved hosted failure above; independent SQLite regression passes with current source origins and current `McpCatalogName` registration.
- Stale or ambiguous guidance removed: none; the addition explicitly distinguishes fixture setup from RCC execution evidence.
- Remaining uncertainty: new two-case hosted RCC gate is required to establish staged-source worker execution and its provenance receipt; the D10 probe remains limited to current e886 source and one import path.
