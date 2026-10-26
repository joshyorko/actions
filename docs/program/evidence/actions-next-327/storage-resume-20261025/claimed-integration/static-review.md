# Isolated claimed-Robot static qualification

Qualified only nine authorized production files in /workspace/recovery327/claimed-robot-source/action_server/src/actions/server/foundry: robot_work_item_authority.py, robot_receipts.py, robot_package_builder.py, robot_package_admission.py, robot_retained_projection.py, package_registry.py, generic_work_item_execution.py, logical_receipts.py and robot_runtime_runner.py. source-sha256.json identifies exact post-format bytes. Frozen helper tests and active checkout untouched.

Results: Ruff formatting/isort/lint all exit0; mypy reports no issues in9 source files,1279 resolved modules and0 errors in8.540s. Format changed5 files; isort changed5 files on first pass. Only formatter/import ordering edits were made; no semantic/type implementation change was required. results.json, tool logs, and gateway-final.log retain evidence. Final check-only format/isort log is style-check.log.

run-static.py explicitly resolves every target inside isolated root, uses isolated package cwd/pyproject.toml and PYTHONPATH/MYPYPATH, and disables incremental type-cache reuse. Verbose mypy log confirms all9 BuildSource targets belong to isolated source. The complete log contains no active-checkout Runtime/Core/Work Items source paths. Prepared active virtualenv supplies tooling/third-party dependencies only; this result does not qualify active source. No product imports/execution tests, DB, RCC materialization/publication, installs or rebuild occurred.

The isolated copy lacked devutils/ruff.toml; initial formatting failure is preserved in formatter-config-missing.log and results-first.json. Exact prepared formatter configuration was copied as evidence/ruff.toml, then all gates reran successfully. Isolated package mypy/isort configuration remains in use. No configuration suppression was added.

## Exact canonical documentation proposal (root applies)

Target docs/skills/repository-operations.md, isolated integration static gates:

“Static qualification of an isolated integration must record absolute target files, run from that isolated package's configuration, and set source/type-search paths explicitly. Preserve verbose typechecker BuildSource evidence and verify it names the isolated files rather than an editable active checkout. A prepared shared interpreter may provide tools and third-party dependencies; it must not silently supply the Runtime source being qualified. If a shared formatter configuration is absent from the isolated copy, retain an exact copy with the evidence instead of silently using defaults. Keep frozen helper tests and active source outside formatter targets, then run check-only format/import-order verification.”

Documentation-improvement receipt:9 explicit BuildSource records, absence of active product source paths, exact source hashes and successful gates support this delta. It removes ambiguity between tool interpreter reuse and source isolation, and between missing format configuration and a clean formatting result. Remaining behavior/SQLite/PG/installed qualification remains separately root-owned; no dynamic pass is claimed here.

Upstream disposition:none. Owned static-integration maintenance, no confirmed upstream defect, external reporting draft-only/no target and no external mutation.
