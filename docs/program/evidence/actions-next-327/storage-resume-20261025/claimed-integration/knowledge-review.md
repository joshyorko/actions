# Mapped Knowledge Core a7 compatibility review

Verdict: current public generated mapped-Knowledge authoring is blocked when supplied package.yaml pins Core 1.1.0a7. It is not restricted to legacy fixture reachability. Unmapped bindings and ordinary generated actions do not enter this v3 check.

Trace: foundry/authoring.py:865 calls compile_trusted_source with backend logical requirements; foundry/package_registry.py:594 invokes compile_generated_python_action with the expected Knowledge compatibility ranges. The bundle path authoring.py:881 builds equivalent policies; deployments/capability_bundle_compiler.py:167 uses the same compiler. deployments/package_revision_compiler.py:75 selects v3 on any non-None invocations, validates known operation contracts, then line91 requires exact Core==1.1.0a4. Assembly calls it at1262; verification calls it again at579. Thus changing only the caller range or bypassing admission would be wrong. templates/basic/package.yaml:17 currently pins1.1.0a7. Generated Knowledge fixtures explicitly downgrade source to a4; the mapping contract tests explicitly reject a5 as unqualified, reflecting the original deliberate candidate restriction.

Reproduction: probe.py reuses compile_mapped from the existing test_knowledge_input_mapping fixture and its synthetic compiler executor. Prepared package gateway, no actual RCC execution, no DB and no installs. Same mapped requirement and policy: a4 compiled successfully; a7 returned no package and compiler_workspace_failed. Direct pure compatibility validation returned the exact Core a4 / Runtime a39 rejection. result.json retains both outcomes. The failure receipt labels build/import/test not-run although source control flow reaches the compatibility check during assembly after executor phases; those labels are not evidence that a real build ran in this synthetic probe.

Minimal proposed remediation (root-owned, not applied): keep one explicitly qualified candidate set in _validate_invocation_compatibility, retain a4 for existing immutable artifacts, and add a7 only alongside current Core context contract qualification. Do not replace a4 with a7, accept all versions matching the broad advertised range, or disable the second verification check. Preserve exact compatibility metadata checks and unknown-operation rejection. Prefer explicit candidate membership to a moving installed-version equality, which could invalidate historical packages after a Runtime upgrade. Update the error to name supported candidate pins accurately. A separate typed compatibility failure receipt/pre-build validation can improve diagnostics, but must not weaken retained verification.

Regression boundary: reuse test_knowledge_input_mapping compile_mapped for a4/a7 successful compile + verify, keep a3 and unqualified a5/future candidate failures, reject altered ranges and unsupported operations. Exercise both public single-source and bundle authoring paths with a7 source and input mappings. Tamper retained environment pin and compatibility fields to prove verification fails. Qualify actual owned Core a7 logical context install/reset/mapped parameters and installed generated Knowledge RCC success/failure separately before claiming installed support. Existing PR lanes already supply the implementation; no duplicate implementation is needed.

Documentation improvement: exact proposed addition to docs/skills/repository-operations.md:

“Mapped Knowledge packages use the v3 invocation contract and validate both advertised compatibility ranges and an explicitly qualified Core package pin during compilation and retained verification. A newer basic-template Core pin does not automatically qualify that reader. When advancing a candidate, retain supported immutable older pins, exercise the current pin through public single-source and bundle authoring, and keep unqualified future pins rejected. Synthetic compiler fixtures prove admission behavior, not installed RCC execution.”

Evidence: probe.py, probe.log, result.json and paths above. Stale ambiguity removed: current template pin implies mapped Knowledge compiler support. Remaining uncertainty: no a7 installed Knowledge execution performed in this lane; remediation is proposed, not applied.

Upstream disposition: none. This is an owned local compiler qualification mismatch, not an external upstream defect.

## Focused regression delivery

New allocated test file: action_server/tests/contract_tests/test_knowledge_core_a7_327.py. RED: 3 failed, 9 passed in 1.41s (red.log/xml). Only the a7 compile prerequisite fails. a4 exact invocation metadata and retained verification pass; a3/a5/a6/a999 reject; altered compatibility and retained mapping/compatibility claims reject. No production changes. This suite does not claim public authoring or installed execution coverage; public single/bundle path trace above remains source evidence. Root owns the compatibility extension and GREEN gate.

Additional exact canonical sentence proposed: “Retain candidate-specific RED evidence before extending the mapped-Knowledge Core allowlist; require exact invocation metadata and retained-verification tamper negatives for every supported candidate, not merely successful compilation.”

## Root extension GREEN

After root added only a7 alongside a4 to the exact pin guard, the three Knowledge modules passed32 tests (green.log/xml). Existing general compiler and mocked Foundry authoring modules also completed successfully (compiler-authoring.log/xml). These are synthetic compiler and in-memory authoring gates, not installed Knowledge/RCC qualification. Ruff check and format --check passed for compiler and new test. Initial targeted mypy invocation stopped at duplicate module naming; see type.log and explicit-package-bases retry separately.

Canonical proposal updated to implemented scope: “Mapped Knowledge compilation and retained verification explicitly accept Core a4 and a7 with unchanged a4/a39 compatibility metadata; a5, a6 and unknown future candidates remain unqualified. Keep both historical and current pins in contract coverage, including exact mappings and retained manifest tampering. Mocked authoring and compiler passes do not qualify installed Knowledge execution.”

Final counts: 32 Knowledge contract tests passed; general compiler plus mocked authoring46 passed,1 skipped. Targeted mypy --explicit-package-bases passed with no issues in1 source file; original duplicate-module failure retained. Total78 passed,1 skipped across the two runs. No production changes by this lane.
