# Lane D a52 Runtime artifact-only build — preparation, NOT RUN

Scope: produce one Runtime1.1.0a52 wheel from the exact integrator-pushed commit, then return its source/tree/hash/generated-input evidence through the supported Library flow. No branch writes, commits, tags, package publication, deployment, new spending or Core/Work Items rebuild. This plan reuses the reviewed build-a51.py approach and repository build tasks; producer paths are not prerequisites.

## Prerequisites and stop conditions

Integrator supplies the exact40hex commit and expected tree AFTER push; REQUIRED placeholders in manifest.example.json must not execute. Lane D supplies target-local existing checkout, fresh output parent, prepared Runtime package Python, and existing pinned RCC18.19.3. Record their resolved paths/origins and tool versions; do not install a toolchain or change locks to make the build work. Use Lane D's already supported RCC developer gateway/activated toolchain; retain its exact invocation. Do not copy producer .venv, HOME, credentials, trust or cache. Preserve real HOME and existing transport/security settings.

Require Linux x86_64 and prepared CPython3.12 tooling, Node/Poetry/Invoke versions matching the selected source's committed developer contracts. The prepared package interpreter must import invoke/build tooling successfully without setup. Candidate checkout may use existing authorized remote fetch if commit is absent; no ref/branch update beyond read-only qualification fetch. Stop if source cannot be obtained. Existing disk18GiB is a reported starting point, not a successful build measurement.

Admission13GiB free on output filesystem; abort at10GiB reserve,3GiB incremental owned-output allocation,1800seconds total or50MiB bounded combined logs. Run serially with no other heavy RCC/PG/build. Use Lane D's existing reviewed bounded process supervisor, exact PID/birth ownership/subreaper cleanup and terminal receipt. If no equivalent controller exists on target, prepare/review one before launch; raw unsupervised command completion is not cleanup proof. Failed/partial output is retained and never reused as a fresh build root.

## Exact build operations (inside the existing supervisor/gateway)

Set target-local variables `lane_checkout`, `lane_output`, `lane_python`, `lane_rcc`, `expected_sha`, `expected_tree`; paths must be absolute, output absent, and ancestors canonical. Verify source commit/tree and root clean state before copying. Reject optimized Python assertions in any reused controller.

Create a fresh local clone without hardlinks, detached at the exact commit; this gives canonical build tasks their own Git metadata without changing the user's checkout:

```sh
git clone --no-hardlinks --no-checkout "$lane_checkout" "$lane_output/source"
git -C "$lane_output/source" checkout --detach "$expected_sha"
git -C "$lane_output/source" rev-parse HEAD
git -C "$lane_output/source" rev-parse 'HEAD^{tree}'
git -C "$lane_output/source" status --porcelain
```

Require exact supplied SHA/tree, empty status and archived Runtime pyproject/module version1.1.0a52. Record source SHA/tree before any generated output. Check RCC binary SHA256 `7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428` and version v18.19.3; copy ONLY that verified executable to detached source `action_server/src/actions/server/bin/rcc-18.19.3` with executable mode. Do not fetch an unpinned binary or use system latest.

From detached source/action_server, invoke repository-owned tasks using the explicit already prepared package Python and approved gateway environment:

```sh
"$lane_python" -m invoke build-frontend
"$lane_python" scripts/build_oauth2_config.py
poetry build --format wheel --output "$lane_output/wheels"
```

These match the reviewed builder's repository frontend/OAuth/wheel flow. Frontend task uses committed lock and may require normal public dependency access; no security/proxy/registry changes are permitted to bypass failure. Record generated `_static_contents.py`, `_oauth2_config.py`, copied RCC and frontend package-lock.json SHA256 after task completion. Record `git diff --name-only` inside detached source; allow only known generated inputs, not unexplained source edits. Recheck original checkout HEAD/clean state unchanged.

## Required artifact receipt

Exactly one `actions_runtime-1.1.0a52-*.whl`; verify wheel ZIP integrity, unique safe member paths, one METADATA with Name actions-runtime and Version1.1.0a52. Record filename,size,SHA256,source SHA/tree, script/gateway identity, tool versions, source/generated hashes and terminal supervisor/resource/cleanup outcome. Bind wheel's `_static_contents.py`, `_oauth2_config.py` and bundled RCC bytes to measured generated input files; retain aggregate Runtime payload count and hashes. Preserve logs locally; share only reviewed sanitized summaries. No credentials/config dumps. A failed build returns FAILED with exact phase, never an invented artifact identity.

No clean install is required for this artifact-only lane. Mark installed metadata/import/payload/runtime execution NOT_RUN unless Lane D separately has all exact dependencies and an explicitly authorized qualification path. Root already owns Core8 wheel SHA25642e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f and Work Items0.5.0a2 SHA25672ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb; do not rebuild or package substitutes. Root will independently install/verify the returned Runtime with those immutable bytes.

## Library handoff

After build and cleanup, use the currently supported Library skill/tool flow in the target environment. Upload only the new Runtime wheel plus compact artifact/source/generated-input/supervisor receipts (or a small bundle containing them). Verify actual uploaded object version, byte size and SHA against local bytes; return Library ID/version/hash, wheel hash and source/tree to root. Never claim local producer paths transfer. No credential copying, denied-artifact alternate export, public publishing or task dispatch. If Library setup/approval is blocked, report that exact action/outcome while preserving local artifact; do not route around a denial.

## Canonical documentation proposal

Add to docs/skills/repository-operations.md: “A delegated artifact-only Runtime build may return a wheel without claiming installed qualification. Build from a detached exact source/tree with repository tasks and an already prepared target toolchain; bind generated frontend/OAuth/RCC inputs to the wheel. Reuse unchanged Core/Work Items bytes at the integration owner instead of rebuilding immutable versions. Return supported Library object identity plus actual byte hashes; target-local paths, caches and trust do not transfer.”

Evidence: source inspection of reviewed build-a51.py, action_server/tasks.py build_frontend and build_oauth2_config, and developer/toolkit package gateway. This handoff introduces no new build implementation and has not executed any build/network/service. Remaining blockers: exact pushed a52 SHA/tree, target path/toolchain/controller validation, actual build/resource/cleanup and Library delivery. Upstream disposition: none.
