# Independent review: staged RCC control fixture-repair repin

Disposition: **APPROVE the control repin for publication; the actual RCC two-case acceptance remains NOT RUN.** No RCC or native execution was performed.

## Source and control identity

- GitHub API readback advertises source `1e795c6c4dbf9ffcb46c0076b08fc5b4908750e6`, tree `cdd4d65d914df9be3eaa4cf979d6b224fde431c3`, parent `2552a8c3419b213825294a51927843b2d61f662e`. The API lists the fixture source file blob as `aa2fc0ae8787c10fca9525f7310b5c643e9cee39`, matching the local tree.
- Repin commit `345df52bf73e0049c83ba345d1ed593c0abe68cd`, tree `6f1a2d42b6d93c912c56efa3e9e6ac72729404a8`, parent `f103edc9015128bb5e6d3875208c4077644e8fe4`. Parent f103 and published control `0ed580eabf2b74fa7b2530f03760b650565b2178` have identical tree `e2420f11d98ac92ab1c1918209a893a578cf0ce6`.
- The repin diff is exactly four files: workflow generator, generated rollback workflow, its workflow contract test, and canonical repository-operations guide. Candidate SHA/tree are consistently `1e795...` / `cdd4...` in generator, YAML checkout/verification/admission env, and contract constants. The two old pins remain only in the guide's historical baseline paragraph; no stale control assertion remains.
- Runtime and dependency inputs remain unchanged. Current candidate Git blob IDs are `_models.py` `964d31c51e42dc285e5eb77e02d86e62adecd6bb`, `_database.py` `e7d9e6d06d8db537c81a24888615f9b7b74e8753`, `source_staging.py` `b475fd6688b7afc6606cde2cba9a1294d771a64c`, `_actions_import.py` `50f72e8c95dcc4455a8225eb19c8d3309faada58`, and `_action_package_handler.py` `a306eb11038f8cd4114415fb978321eb2ac51a0f`; they are identical between the source and control candidate trees. The workflow's RCC pin is unchanged at v18.19.3, SHA-256 `7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`.

## Contract verification

Using the already prepared worker-exit Python 3.12 environment, with no RCC variables set:

```sh
/workspace/work/community-resume/worker-exit/action_server/.venv/bin/python -m pytest \
  --confcutdir=developer/tests \
  --basetemp=/dev/shm/luna-rcc-control-repin-20261010 \
  -q developer/tests/test_rcc_provider_rollback_workflow.py \
     developer/tests/test_rcc_provider_rollback_summary.py
```

Result: **34 passed, 0 skipped, 40.49s** (only dependency deprecation warnings). The workflow contract regenerates the YAML and compares bytes; it checks the pinned candidate commit/tree and both exact nodes: `test_current_candidate_failed_reload_keeps_last_good_action_usable` and `test_staged_package_executes_in_managed_rcc_runtime`. Summary contracts reject skipped/incorrect JUnit results and missing, duplicate, or unexpected source/staged inventory paths. No service, RCC command, environment creation, or native artifact was run.

## Acceptance boundary and preserved failure

The old failed run `38068024443`, job `114259549777`, remains a failed baseline for candidate 2552: its one rollback case passed, but the staged consumer could not open SQLite because the test-owned `runtime-data` parent did not exist. The preserved failure excerpt SHA-256 is `218a4719f82b6d9bac95d521992e25115abfbe26c1b1704892d0415c3b2c5d2b`. The repin does not convert that run into acceptance. The new exact-source/control RCC two-case gate remains **NOT RUN** until the refreshed control is published and a source/tree-bound receipt records both exact passing JUnit cases with no skips.

## Required dispositions

Upstream disposition: none. The prior failure was a test-owned SQLite directory prerequisite; the source repair and repin are local test/control changes.

Documentation improvement:
- Canonical file changed or proposed: `docs/skills/repository-operations.md` (updated in 345df52).
- Durable learning captured: the old run is a fixture-setup baseline, the repaired candidate initializes a private current-schema SQLite catalog, and acceptance still requires a fresh exact-source two-case RCC run.
- Evidence: preserved failure excerpt and source commit/API/tree/blob readback; local 34-contract pass confirms the pin and generated workflow.
- Stale or ambiguous guidance removed: 2552 is labeled as the previous failed candidate; all active control pins now reference 1e795/cdd4.
- Remaining uncertainty: no new hosted RCC run has executed this candidate; actual managed-worker provenance and staged Action result are unverified.
