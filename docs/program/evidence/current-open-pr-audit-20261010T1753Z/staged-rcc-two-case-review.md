# Independent managed RCC gate review

Review date: 2026-10-10 UTC

Decision: PASS for this bounded Linux managed-RCC rollback/staged-consumer gate.

## Immutable run tuple

- Repository: `joshyorko/actions`
- Workflow run: `38070431104`, attempt `1`; branch `test/rcc-provider-rollback-hosted-20261010`
- Workflow control: `473e42ec8f7a9f3fed623efc135b550ac3c08190`, tree `6f1a2d42b6d93c912c56efa3e9e6ac72729404a8`
- Runtime candidate: `1e795c6c4dbf9ffcb46c0076b08fc5b4908750e6`, tree `cdd4d65d914df9be3eaa4cf979d6b224fde431c3`
- Job `114266535865`: completed / success. All test, evidence, validation, and artifact-upload steps completed successfully.
- Artifact `11676657463` (`rcc-provider-rollback-38070431104-1`): 2,647 bytes; GitHub-advertised and independently measured ZIP SHA-256 `cf6200fde73448a211df5e2dfde658f9d07014b8866fcc8ba7c5ddd7225949c0`.

## Artifact members

- `acceptance-summary.json`: SHA-256 `128cc95008c279f71bf97b90e35bdb5999e0177381805d73376f48028d991f84`
- `acceptance-summary.log`: SHA-256 `012b9aa7dac26d5283f7694ade74bbdbba2deddb93cd7a932bb8c1725600cef3`
- `staged-consumer-receipt.json`: SHA-256 `ec47ddb0a2cfc84ad0b20b96a4e9b677f83ee9f00d9f12d69329cbd76d12399c`

## Acceptance checks

- **PASS — run/source binding:** job logs show workflow control and candidate checkout at the exact SHAs above; summary trees match Git object trees. The nine summarized candidate file digests independently match blobs read from the candidate commit.
- **PASS — test selector/result:** job logs show two collected items and both exact selected nodes passed: `test_current_candidate_failed_reload_keeps_last_good_action_usable` and `test_staged_package_executes_in_managed_rcc_runtime`. The hosted validator summary reports 2 tests, 0 failures, 0 errors, 0 skipped, matching identities, exit code 0. The raw JUnit XML was ephemeral and is not a member of the uploaded artifact; its exact node names and PASS status are visible in the job log, and the hosted validator reports its exact-identity check passed.
- **PASS — staged source equality:** receipt binds candidate SHA/tree; source and staged inventories are equal and contain exactly two unique paths (`action.py`, `package.yaml`); per-file digests and source/staged digest maps agree. The staged action digest matches the runtime-reported action source digest.
- **PASS — managed runtime provenance:** receipt reports Core `1.0.2`; Python executable and Core module paths are beneath the managed `holotree` root; action source path is under `.rcc-runtime-sources`. Hosted validation reports managed worker origins and candidate runtime-module hashes/origins matched.
- **PASS — RCC pin:** summary and receipt report RCC `v18.19.3`, SHA-256 `7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`; hosted validation reports the runtime and Action Server default binaries matched the pin and version. This review checked the job's actual recorded verification and does not claim to possess the runner binary.
- **PASS — lifecycle:** hosted validator reports lifecycle receipt PASS, natural exit PASS, return code `1` before cleanup (an allowed value in the validator), no forced stop, cleanup return code observed, and zero remaining owned descendants. This is the provider-rollback worker lifecycle exercised by these cases, not broad process-restart or release acceptance.
- **PASS — runner floor:** hosted runner reports glibc `2.39`, meeting the workflow's `>=2.36` requirement.

Independent artifact checks were performed in memory from `/dev/shm/luna-rcc-managed-run38070431104/evidence.zip`; no native/RCC executable was downloaded or run locally. The workflow's embedded admission validator was inspected at control commit `473e42e`; the hosted job logs show that validator step succeeded. The uploaded artifact does not include raw lifecycle receipt or raw JUnit XML, so the lifecycle and JUnit conclusions are bounded to the runner's successful validator plus sanitized summary and test log, not independent re-parsing of those omitted raw files.

## Scope boundary and follow-up

This proves the two selected tests for the exact candidate/control tuple on Ubuntu 24.04 with the pinned managed RCC/Core environment. It does not prove a full release, cross-platform behavior, Go-wrapper behavior, all RCC operations, or acceptance of a different source tree. The earlier failed run `38068024443` is unchanged and is not used as evidence here.

Canonical guide suggestion: after this first passing hosted tuple, add a short dated-independent, durable procedure note that acceptance is tied to the immutable control SHA, candidate SHA/tree, artifact digest, and managed tool hashes, and that omitted raw JUnit/lifecycle files should be retained or explicitly treated as validator-attested rather than independently replayable. Current evidence does not require an upstream report; disposition: none (no upstream defect identified).
