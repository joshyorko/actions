# PR308 native artifact selector design receipt

Status: read-only design proposal; no source changes, service runs, dependency changes, or verifier execution.

## Reviewed candidate identity

Repository: `joshyorko/actions`
Worktree: `/workspace/work/actions-mk3-rcc-candidate-version`
Branch: `mk3/rcc-candidate-version-20261010`
Commit: `76e7f64a67c7dd7d68419188190d839f2350b8b8`
Tree: `8471f44cc58f2dbe0226fbcf7d89445f440df2f0`
Parents: `284880ca80bb666de6ef1bd970b493435bb7a8a9`, `19380993febaa71238eaee3026b5c808773283ff`
Checkout observed clean. Source anchors below refer to this exact tree.

## Smallest selector contract

Extend only the RCC acceptance verifier’s explicit runtime choice, keeping source mode as the default. Preferred shape: `--action-server-mode {source,frozen,go-wrapper}` plus explicit native bundle, build manifest, and provenance/inventory inputs for `frozen` or `go-wrapper`. Preserve the candidate-wheel package installation path. Propagate the selected mode and validated artifact binding through the outer supervisor’s worker argv; do not inherit `SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE` from the caller. Only after validation, set that variable in the worker’s controlled runtime environment because `ActionServerProcess` reads it from `os.environ`.

For frozen mode, require platform/architecture and kind agreement, canonical selected path within the staged bundle, selected executable SHA-256 agreement, and successful manifest plus complete frozen-package inventory/provenance validation. For Go-wrapper mode, require the wrapper executable SHA-256 and embedded asset/archive identity against that same manifest, execute with a fresh task-owned HOME, then verify the extracted internal frozen package tree against the measured inventory/tree digest. Fail closed when any input or binding is absent or mismatched; never label source execution as native proof.

Keep candidate checkout SHA/tree distinct from native build SHA/tree and native workflow run/attempt. If claiming matching content, explicitly verify tree equality; a manifest’s Git HEAD field alone is not a clean-source attestation. Preserve candidate Core and Helper wheel versions from checked-out project metadata for generic use, with each wheel’s version/hash and actual worker distribution origin in evidence. For the current PR308 milestone, require both Core and Helper to resolve to 1.0.3; do not hardcode 1.0.3 as the future production harness’s expected version.

Keep receipt `runtime_mode` as `candidate-wheel`, and add/retain a separate `action_server_mode` of `source`, `frozen`, or `go-wrapper`. Source receipts remain source-only. Native receipts contain selected kind and relative path, selected executable hash, manifest/inventory/provenance hashes, full package tree digest, native build SHA/tree, platform/architecture, and workflow run/attempt, separately from candidate checkout and wheel identities. Existing 2400-second proof deadline, outer CLI watchdog, process-tree supervision, and bounded cleanup remain in force. Preserve the existing offline positive cells and their current meanings, especially `provider_backed_exec_fail_closed=PASS` and `offline_warm_artifact_ready=PASS`; do not change provider trust policy, omit cells, or reinterpret offline outcomes for native mode.

## Existing contracts and exact source evidence

- `action_server/scripts/verify_dakota_rcc_acceptance.py:29-31`: 2400-second proof timeout, cleanup grace, outer watchdog.
- `verify_dakota_rcc_acceptance.py:32-56,70-79,119-168`: filtered child environment and safe extra allowlist omit `SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE`.
- `verify_dakota_rcc_acceptance.py:736-756`: current parser accepts only `candidate-wheel`.
- `verify_dakota_rcc_acceptance.py:1235-1269`: current run derives source SHA and candidate wheels from checkout.
- `verify_dakota_rcc_acceptance.py:1957-2004`: outer supervisor reconstructs worker argv and controlled environment; selector must cross this boundary explicitly.
- `verify_dakota_rcc_acceptance.py:1764-1765,1899-1900`: current receipts identify candidate-wheel and source Action Server mode.
- `verify_dakota_rcc_acceptance.py:1740,1748,1866,1874`: offline positive cells remain explicit in existing evidence generation.
- `action_server/src/actions/server/_selftest.py:113-120,439-446`: `ActionServerProcess` and CLI route consult the selector from global process environment.
- `action_server/scripts/dakota_workitems_native_acceptance.py:101-148`: existing native fixture validates manifest schema, source SHA, platform/architecture, canonical path, and selected executable hash; it only validates executable identities and is not by itself complete package binding.
- `dakota_workitems_native_acceptance.py:366-393,408-450`: explicit frozen/Go selectors, measured manifest, task RCC home, candidate Core wheel, and separate receipt already exist as fixture patterns.
- `action_server/scripts/write_native_artifact_manifest.py:144-164,166-198`: native manifest contains frozen package file/tree digests, inventory locator, build run/attempt and platform; scope string expressly says Git HEAD only, not clean-source attestation, and no candidate Core wheel.
- `action_server/scripts/archive_native_artifact_provenance.py:59-94`: archive validator compares complete frozen tree inventory and package digests against the manifest.
- `action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py:169-199`: current receipt and offline-cell assertions; `:202-318` covers environment filtering and candidate wheel metadata.
- `docs/skills/repository-operations.md:1954-1962`: native executable selector also routes CLI operations and requires managed package metadata for fixtures.
- `repository-operations.md:3001-3028`: current guide requires separate candidate/build identities, full inventory and worker origins; source mode does not establish frozen behavior; historical acceptance is scoped to its candidate and does not establish Go-wrapper execution.

No native executable, native manifest, or provenance archive was present in the inspected checkout. This design therefore does not claim artifact availability or acceptance.

## Proposed focused tests

In `action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py`, cover: source default; explicit frozen and Go modes; native mode rejects absent/mismatched manifest, platform, artifact kind, canonical path, executable hash, inventory/tree digest, or build identity; inherited ambient selector does not cross the supervisor boundary; validated selector alone reaches the worker runtime environment; source and native receipts make distinct truthful claims; generic candidate version expectation derives from checkout metadata while the current acceptance contract requires Core and Helper 1.0.3; Go mode uses a fresh HOME and checks extracted package inventory. Reuse the exact selector and manifest patterns from `test_dakota_workitems_native_acceptance.py` and the archive inventory validator. Keep the existing opt-in long verifier gate unchanged and do not run it for selector contract work.

## Canonical documentation proposal

Target: `docs/skills/repository-operations.md`, adjacent to the executable selector guidance around lines 1954-1962 and Frozen Runtime acceptance around 3001-3028. Add the verifier-specific rule that its child environment intentionally filters the native selector, so a native mode must explicitly validate and forward it. State that receipts separately bind candidate checkout/wheels and native build/artifact identities; require full frozen package inventory validation and fresh HOME plus extracted-tree verification for Go-wrapper runs. Preserve the established distinction that source-mode PASS is not native acceptance, and keep offline positive cell policy unchanged.

Existing guide already covers source/native evidence separation and candidate/build identities; the durable gap is this verifier’s selector filtering boundary, manifest limitations, and Go-wrapper extraction binding. No existing guidance needs removal.

## Upstream disposition

None. Evidence points to an Actions verifier environment-selection/provenance boundary, not a defect in RCC or another upstream dependency. No upstream issue search or report is warranted.

## Correction to earlier communication

A prior coordination message contained a selector spelling typo (`SEMA4MAI...`). The exact source spelling in this receipt is `SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE`; no source or evidence file used the typo.
