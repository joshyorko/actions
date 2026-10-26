# A58 integrity checkpoint evidence

See [the integration result and remaining original gates](INTEGRATION.md) for
the reviewed a58 repair and subsequent verification. This copied snapshot
preserves the earlier source identities and unresolved diagnostics verbatim.

Read-only evidence bundle assembled 2026-10-26. It records the source path and SHA-256 of every copied source; copied artifact hashes are included for integrity. Campaign JSON/Markdown references had only erroneous leading `actions/` removed from repository-relative docs paths. Compact JSON is whitespace-minified with keys preserved.

## Scope and findings

- Hosted coverage run #512 at PR head `207300bf` completed **FAILURE**: Per-package counts are itemized in `hosted-ci/coverage-512-terminal-207300bf.md`; one Runtime test failed and no coverage baseline was written. The source receipt distinguishes the downstream incomplete-source-inventory gate from the Runtime failure.
- Campaign reconciliation is **NOT READY / NO-GO**. The A57 Python SBOM profile evidence is bounded: base profile has 64 active distributions; `data-duckdb` has 65. Both producers and pip checks pass, but strict raw CycloneDX-vs-active-edge comparison fails with 29 inactive edges, retained with complete reconciliation. This evidence does not qualify distribution.
- Windows diagnosis and fix receipts retain the original red/green story: Git Bash host shell was available while a child `bash` resolved to WSL; the test helper now selects Git for Windows Bash explicitly. Hosted rerun is still needed to confirm the new selector on Windows.
- Auth route inventory and direct authorization proof remain distinct. The focused configured-key test covers 117 method identities and 234 missing/wrong credential requests; broader 88-test auth run is separate evidence. Global API key semantics do not establish multi-principal isolation.
- The official Runtime 1.0.4 public wheel SHA-256 is `ab0925ddfbc804d4790b5bd839461310b851c3dedf5f4781e4b4c8472bcf5eba`. The bounded a57 queue/attachment recovery gate passes, including exact installed payload verification, schema-version safe refusal, unchanged refusal fixture, and pre-upgrade backup rollback. Full Runtime restore remains **NOT_QUALIFIED**. Historical network/setup/verifier failures remain described in the source receipts.
- Temporary evidence excerpt records the 24 filesystem tests, 19 diagnostic tests, and 88 auth tests from `/tmp/327-*`; `a58-current-checks.md` adds the 89-test output suite, 661-file typecheck, and independent final review. These local results do not invent a new exact commit identity. The latest quality/lint attempt remains failed on a formatting diagnostic. The working tree was dirty and based on `207300bf`.

## Documentation improvement proposal

Propose these exact insertions in `actions/docs/skills/repository-operations.md`:

1. In `### Installed SBOM declaration and active graphs`, after the current verification paragraph: “For a lock-qualified consumer, keep the raw declared CycloneDX inventory, lock-derived active profile graph, and marker/extra reconciliation as separate evidence. In the measured `cyclonedx-bom` 7.5.0 profiles, the strict raw-edge comparison retained 29 inactive edges and failed while the independently resolved 64-distribution base and 65-distribution `data-duckdb` profiles passed their bounded consumer checks. Preserve that strict failure; the bounded SBOM subgate does not qualify the full distribution.” Evidence: both A57 consumer READMEs and copied ready, producer, strict, graph, and reconciliation receipts.
2. In the existing Windows `bash -n` paragraph near frozen-wrapper contract tests, append: “For child scripts on Windows, select `bash.exe` from the resolved Git-for-Windows installation explicitly; a bare PATH lookup can resolve to the WSL launcher even when the hosted Actions step itself uses Git Bash. Fail clearly when Git Bash is unavailable rather than enabling WSL. A passing local resolver regression still needs a hosted Windows rerun.” Evidence: copied hosted diagnosis and test-only fix receipt, retaining the prior failure and focused 10-test pass.
3. In `### Frozen-lock consumer qualification`, after the installed recovery paragraph: “When reconstructing a published Runtime baseline, distinguish the actual installed companion tuple recorded by the installed-smoke receipt from the older source lock's develop-path dependency identity, and verify each public wheel against official release metadata and retained digests. Keep a bounded installed queue/attachment safe-refusal and pre-upgrade rollback result separate from full Runtime/database restore qualification; an explicit schema refusal that preserves fixture bytes is not a full restore pass.” Evidence: copied public 1.0.4 input and a57 legacy recovery receipts; Runtime wheel SHA-256 `ab0925ddfbc804d4790b5bd839461310b851c3dedf5f4781e4b4c8472bcf5eba`.
4. Add a short terminal-coverage reporting paragraph under the existing hosted validation guidance: “For hosted aggregate coverage, retain the PR head and actual merge checkout identity, per-package pass/fail/skip counts, the first failing test, service startup/cleanup results, and whether downstream baseline or source-inventory failures were caused by that test failure. Do not claim a coverage baseline when the aggregate gate withholds it.” Evidence: hosted run #512 receipt; one Runtime failure caused `baseline_written=false` and incomplete source inventory, while service startup and cleanup succeeded.
5. After the sealed-output authority paragraph, add: “The Linux filesystem provider verifies each complete touched 64 KiB block against digests measured when the object is opened, then advances the reader cursor only after all requested blocks and the final descriptor-identity check succeed. A failed read returns no bytes and leaves the cursor unchanged. Objects are capped at 64 MiB, `pread` is required at provider initialization, and the output transport requests 64 KiB chunks.” Evidence: independent final review and focused filesystem tests, 24 passed in 0.42s.

No canonical guide was changed in this isolated lane. The proposed additions capture measured behavior and preserve the existing non-promotion boundaries.

Canonical file changed: none (isolated evidence-only lane). Stale or ambiguous guidance removed: none here; proposed deltas only. Remaining uncertainty: final candidate source/version acceptance, full distribution acceptance, Windows hosted rerun, and complete Runtime restore.

Upstream disposition: none. No upstream defect was investigated or established.

## Provenance manifest

The machine-readable `manifest.json` lists each original absolute source path, its original SHA-256, each copied relative filename and digest, and any normalization. The temporary log excerpt also lists each source path and digest.
