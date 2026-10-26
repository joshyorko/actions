# Selected adapter readiness checkpoint

Scratch-only four-file patch; exact original file hashes in base-hashes.json, originals under baseline/. No root edits, RCC, containers, cache or dependency/environment mutation. No startup/provisioning/grant behavior changed.

API: ConfiguredProviderExecution.require_adapter_available(reference, operations) validates selected configured source/object mappings and imports duckdb and/or psycopg only as needed. LogicalExecution.require_selected_adapters(snapshot) reads exact immutable requirements/Deployment bindings. GeneratedRccExecution._verified_selection calls it only for bound capabilities; TaskHost already calls this selection before TaskService admits a Run.

Dependency import is selected readiness, not an engine query/connection. PostgreSQL CSV does not depend on DuckDB; selected Parquet needs the shared DuckDB decoder. Missing/import-link failures are sanitized. No automatic installation/fallback or refusal based on unused providers.

Tests: red.xml2failed1passed (missingselected dependency admitted before fix, factory API absent); green.xml3passed; final.xml5passed1.64s; host-final.xml5passed1.58s strengthens checks to real TaskHost.require_ready with only thread-running state mocked. Missing dependency leaves existing Run/Attempt counts unchanged; present one admits one new Run and no Attempt. Engine/current-catalog methods set to forbidden in readiness test. PostgreSQL adapter cases exercise dependency selection with synthetic typed metadata/import hooks, not live PostgreSQL. Mypy3sourcefiles/Ruff/isort clean.

Command: PYTHONPATH=action_server/src:common/src:devutils/src:action_server/tests /workspace/actions/action_server/.venv/bin/python -m pytest -p no:robocorp_log_pytest action_server/tests/action_server_tests/test_logical_readiness.py -q --junitxml=/workspace/actions-recovery-327/logical-readiness-evidence/host-final.xml

Upstream disposition: none. This is a repository-owned readiness join; declared optional dependency absence is not an upstream defect. Exact canonical guide proposal attached. Root retains installed failure evidence and owns explicit extra installation/new-datadir qualification.
