# Historical MCP key ownership checkpoint

Final local commit `6eec6c6493cf029c5bba5d8189834349a26c0f67`, tree
`41a67489bd000b98971dab7db1652de2933c89f2`, clean branch
`fix/mcp-alias-identity-20261010` in
`/tmp/work/actions-worktrees/mcp-alias-identity-20261010`.
Production commit `e789af7ce79ae0214ce216459a423e0ab9f0622f`, tree
`3107690386ac3a3c5a198b4b173fcdaa65376851`, remains preserved; final follow-up
adds only six canonical guide lines. Base remains immutable
`2286d8e21f73a704b1fe8acd1127e09a160efd64`; parent owns reconciliation to newer
integration ancestry. No GitHub writes, Devsy, installation, asset downloads,
force/reset, or subdelegation occurred.

## Root cause and red proof

The original resolver derives names solely from the current admitted set.
Mounted MCP + actual SQLite fixtures first advertise `package1__do_it` for
`package1/do_it`. Disabling the sibling collision and admitting another
package's literal `package1__do_it` action makes the stale call return
`literal-other` with `isError:false`. Exact baseline log
`baseline-2286-alias-capture.log` SHA256:
`501ae1e6f4ea0a49ee9a708000596ab357ad97d709428cce4468d6aa911c04ed`.
The original red test is preserved as `baseline-test.py` (SHA256
`6efbbfb8c81e8ba9c5f132093e709e1fa04eb091aaeed245aa31e8d20f480605`).
The baseline command used prepared Python with
`PYTHONPATH=action_server/src:/tmp/work/deployment-values-deps/site-packages`,
`--confcutdir=action_server/tests/action_server_tests/mcp` and that test selector.

Independent actual-call proof at the same baseline also establishes exact direct
resource, resource-template string, and prompt-name capture. Its retained log is
`/workspace/work/mcp-alias-identity-review/baseline-repro.log`, SHA256
`effcc276eb26da9e260e4a1efc930db7aa05e5d4229ded718dcb229658075695`.
The authoritative read-only #89 contract is `issue-89-readonly-contract.json`;
#89 remains closed. The guard preserves its deterministic equivalence contract.

## Implementation and scope

The original resolver is unchanged. Existing-DB migration 13 adds
`mcp_catalog_name`, with separate tool/resource/resource-template/prompt exact
keys and permanent original `(package name, action name)` ownership. Keys use a
64-character SHA256 indexed ID plus stored exact namespace/key, with collision
rejection. There is no public identifier-length restriction or alternate alias
allocation based on history. Ownership survives disabled, filtered, omitted,
deleted, restarted, and concurrent-process catalogs sharing that database.

`prepare_actions` takes the existing transaction and acquires the writer before
catalog/history reads: SQLite zero-row UPDATE; PostgreSQL table lock. The full
candidate validates before all new reservations are inserted. A proposed
historical reassignment rejects the complete admission with a rename diagnostic;
existing offline/import/reload transactions roll reservations back together with
metadata and executable-generation admission. Tests exercise last-good mounted
calls and explicit rename recovery. Retired tools return isError + tools/list;
resource/prompt errors explicitly name rediscovery methods. Auth and original
whitelist filtering remain enforced, and no retired alias forwards to hidden
capabilities.

History starts at migration/admission; arbitrary pre-upgrade advertisements and
independent fresh/replaced databases cannot be reconstructed. Exact string
ownership does not guard distinct-template overlap or direct-resource/template
cross-kind matching of a concrete URI. Direct URI lookup precedes template
matching. These observed limits are documented; this checkpoint does not certify
all possible stale concrete-resource reads or whole release acceptance.

## Verification and remaining gates

Prepared Python: `/tmp/work/multipackage-runtime-acceptance/venv-primary/bin/python`.
Prepared configured Ruff/isort/mypy:
`/workspace/work/community-resume/worker-exit/action_server/.venv/bin/`.
Tests use `PYTHONDONTWRITEBYTECODE=1 TMPDIR=/dev/shm/actions-alias-tmp` and
`-p no:robocorp_log_pytest`; private RAM basetemp avoids disk materialization.
No RCC autouse collection is enabled in the focused lane.

Final exact-head command from worktree root:

```text
env PYTHONDONTWRITEBYTECODE=1 TMPDIR=/dev/shm/actions-alias-tmp PYTHONPATH=actions/src:action_server/src:action_server/tests:/tmp/work/deployment-values-deps/site-packages /tmp/work/multipackage-runtime-acceptance/venv-primary/bin/python -m pytest -p no:robocorp_log_pytest --basetemp=/dev/shm/actions-alias-exact-tests --confcutdir=action_server/tests/action_server_tests/mcp action_server/tests/action_server_tests/mcp/test_alias_history.py action_server/tests/action_server_tests/mcp/test_setup_mcp_server.py -q
```

41 passed in `exact-head-focused-mcp.log`: 18 new ownership tests and 23 existing
catalog tests. New cases cover real calls, collision arrival/removal/literal
capture, disabled/whitelist/deleted states, bearer rejection, all four exact
namespaces, rename recovery, restart and UUID replacement, unrelated reservation
histories/equivalent descriptors, long public keys, digest collision, failed
batch generation/invalid UI rollback, fresh/migrated schema/index parity, and
real concurrent SQLite processes with empty history. The original pure resolver
still has forced-digest/import-order coverage.

Current-source gateway/SDK/Apps checks: 50 passed, 1 skipped, 1 deselected in
`mcp-source-boundaries.log`. Command uses same prepared environment and
`PYTHONPATH`, selects `test_mcp_gateway_metadata.py`,
`test_pinned_mcp_auth_sdk_contract.py`, `test_mcp_apps_authoring.py`, and
`-k 'not through_action_server_process'`. The skipped case requires ACTIONS_CANVAS_RUNTIME_ACCEPTANCE=1 for opt-in
RCC/browser acceptance; the subprocess fixture case is intentionally deselected.
Provenance: Core imports this worktree's `actions/src/actions/__init__.py`, Runtime
imports this worktree's `action_server/src`, MCP SDK imports prepared
`/workspace/actions/action_server/.venv/lib/python3.12/site-packages/mcp`.

Earlier broad diagnostic with published Core1.0.2 gave 49pass/1skip/1failure/1error:
advanced resource(meta=) was unavailable in published Core, and confcutdir excluded
the process fixture. `mcp-boundaries.log` preserves that result; it was not waived
or fixed by changing Core floor/template dependencies. Current source Core is
used only for advanced source Apps acceptance, independently of legacy CLI Core
compatibility.

Legacy v0-to-current migration, fresh/migrated schema and index parity, and exact
schema golden pass in `database-migration.log`, using the existing
`database_v0.__wrapped__`, `test_migrate`, and schema regression function directly.
Relevant shared DB/historical/forward-repair/SQL-adapter selectors: 15 passed,
36 deselected in `database-shared.log`. The new migration creates its index
idempotently so a restored current-shape table under an older version marker
retains data. Historical migrations remain byte-identical.

Configured mypy on nine touched Python files passes in `exact-head-mypy.log`:
from action_server cwd, `--config-file pyproject.toml --explicit-package-bases
--follow-imports=silent --cache-dir /dev/shm/actions-alias-mypy`, with
`MYPYPATH=/tmp/work/deployment-values-deps/site-packages`. Both preparation method
bodies have return annotations and are checked. Configured Ruff check/format,
isort check and git diff-check pass; logs `exact-head-{ruff,format,isort}.log`.

PostgreSQL was not run by the author. The assigned independent reviewer passed
11 PostgreSQL-adapted source cases, fresh versus v12-to-v13 schema/index parity,
and two actual PostgreSQL processes competing after a table-lock barrier.
Receipt: /workspace/work/postgres-alias-acceptance-20261010/independent-postgres-review.json.
It pins production e789/tree310769 and verifies final6eec is docs-only. This
establishes the DB reservation/migration/rollback boundary, not PostgreSQL MCP
runtime/worker/native acceptance. New real CLI transition test
`test_sync_rejects_historical_mcp_alias_capture_and_rename_recovers` is committed
and honors existing `SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE`, but source
CLI/new frozen native artifact execution is NOT RUN in this lane. Parent owns
combined-source/native gates. Old31239 frozen drain results do not prove this new
repair. Complete package/external-service suites remain outside this bounded
prepared fallback lane.

An intermediate test run hit ENOSPC (7pass/5errors); it is not a semantic verdict.
Only this lane's ignored disposable125MiB Robocorp auto-logs were removed;
source and text evidence were preserved. Root adjusted resource policy for
text/RAM tests: workspace stop below200MiB or memory below2GiB, no heavy installs
or RCC materialization. Final measured workspace306MiB free, private RAM test
and mypy dirs41MiB, memory available~7935MiB. No current source files are dirty.

Documentation improvement:
- Canonical file changed: docs/skills/repository-operations.md, same production
  commit plus preserved six-line matching-limit clarification.
- Durable learning: deterministic admission guard, permanent exact namespace
  ownership/transaction boundaries, migration/replica/restart scope,
  rediscovery/rename recovery, fixed-size index+exact equality, test/native usage,
  and proven overlapping/cross-kind resource matching limits.
- Evidence: baseline real MCP capture, 41 focused passes, 50 advanced source
  boundary passes, 15 shared DB passes, legacy schema/index parity, typed/lint
  checks, and independent exact-baseline overlap/cross-kind calls.
- Stale guidance removed: previously advertised alias can silently identify a
  different literal tool and safe historical compatibility is unimplemented.
- Remaining uncertainty: unknown pre-upgrade history, fresh databases,
  cross-template/cross-kind concrete URI identity, actual new artifact
  and PostgreSQL runtime/worker gates, full-suite/native-platform acceptance.

Upstream disposition: none. This is local catalog admission behavior; no confirmed
maintained dependency defect or upstream mutation was established.
