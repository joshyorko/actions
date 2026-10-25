# a48 readiness failure — stale fixture, isolated correction

The frozen broad suite's failure remains recorded. A single-test prepared RCC reproduction (`red.log`) exposed only the original exception class/attribute: `AttributeError capability_runner`. `TaskService._require_ready` intentionally replaces internal exceptions with a generic `TaskHostUnavailable`; this is correct public detail suppression, not an authorization defect.

`test_logical_readiness.task_host` builds a `DetachedTaskHost` with `object.__new__` and manually supplies fields. Production `DetachedTaskHost.__init__` always sets `self.capability_runner = capability_runner`, default None. Its new Robot-aware readiness selection reads that field before generated selection. The synthetic fixture omitted it. Production source requires no change, and no exception fallback or authorization bypass is proposed.

The four-hunk fixture/test-only `repair.patch` supplies the constructor-default field and strengthens two boundaries:

1. Missing DuckDB must actually reach the selected dependency check; a recorded `duckdb` call is required before the generic denial and unchanged Run/Attempt assertions. Previously the unrelated missing attribute let this negative test pass falsely.
2. The no-provider-I/O check now exercises full real `DetachedTaskHost.require_ready`, not only the lower-level generated selection helper. `open_provider` and `check_current` remain forbidden.

Validation: prepared gateway isolated module **5 passed in3.21seconds**, `green.log`/`green.xml`. Real product imports are explicitly asserted under `/workspace/actions/action_server/src`; only tests are supplied from the isolated file. No PG, RCC materialization, server or heavy build. RCC was used solely as the existing developer package gateway. `green-import-failure.log` preserves an initial isolated harness import failure before source tests directory was added to test imports; it is not a product failure. `red.log` preserves the confirmed original failure. Independent cleanup_review cleared the fixture default and selected-dependency assertion; root owns integration.

Exact run:

```sh
source /workspace/actions-cloud/activate.sh
rcc task script -r /workspace/actions/developer/toolkit.yaml -- python /workspace/actions-cloud/package-command.py action_server run python /workspace/recovery327/a48-broad-repair-readiness/run.py
```

`receipt.json` binds original/candidate test bytes and patch SHA256. No shared source changes performed.

## Exact canonical guide proposal

For parent-owned `docs/skills/repository-operations.md`, testing/readiness section:

> When public readiness deliberately hides internal exceptions, assert that negative tests reached the intended dependency/authority boundary before counting their generic denial as a pass. A fixture constructed with `object.__new__` must initialize every constructor field consulted by the real readiness path, including optional runner fields with their true default. Exercise the full readiness method while forbidding provider/engine I/O; do not weaken production exception suppression or authority checks to repair a synthetic fixture.

Documentation-improvement receipt: exact durable proposal above is supported by the original AttributeError reproduction, false-positive negative-path diagnosis and five passing strengthened tests. Shared canonical docs remain root-owned.

Upstream disposition: none. Owned stale Actions test fixture, no external defect or mutation. Any external reporting remains draft-only absent explicit target authority.
