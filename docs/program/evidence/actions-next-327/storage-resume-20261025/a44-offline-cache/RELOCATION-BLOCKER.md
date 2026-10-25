# Imported hololib publish is not target-contained

The prior README route is superseded for target-containment: root's fresh import experiment reproduced a restore under the producer base, despite target-local publish/trust and later target-local env exec proof. Do not ship it as a contained recipe.

Pinned RCC 18.19.3, commit 4148c2b71705c9d2baf0e88b48d08a79cb7bda0f:

1. environmentlifecycle/builder.go CurrentRCCBuilder.Build invokes collectBuildCompatibility; compatibilityForBuiltEnvironment calls library.Restore.
2. htfs/library.go RestoreTo loads the imported compressed catalog and computes targetdir with filepath.Join(fs.HolotreeBase(), label).
3. htfs/directory.go HolotreeBase returns filepath.Dir(it.Path), retained from the catalog. Relocate explicitly rejects a different base directory.
4. ControllerSpaceName changes only the basename. holotree variables --space therefore does not repair the base. The sidecar .info is not the sole cause; changing it alone cannot correct the loaded catalog.
5. htfs/portable.go has a supported Go PortableCatalog.Rebase API used for portable artifacts, but no inspected holotree CLI exposes it for imported legacy catalogs. Raw catalog editing or a custom Go rebase helper would be a new implementation, not an existing CLI recipe, and is not proposed here.

Evidence: /workspace/recovery327/a44-offline-compiler/publish.stderr.log prints the producer-base installation plan and identity.yaml paths. Root additionally observed the deleted producer directory recreated. This lane only inspected logs/help/pinned source; it did not reproduce by execution.

No supported target-contained import→publish relocation command was identified. No permission denial occurred; the blocker is retained-base behavior in the pinned implementation. The earlier publish/proof PASS is valid for its measured checks but insufficient to establish target-contained preparation.

## Draft upstream report, not published

Candidate: joshyorko/rcc, v18.19.3 / 4148c2b71705c9d2baf0e88b48d08a79cb7bda0f.
Title: env publish after holotree import restores compatibility inventory under producer base
Reproduction: export an existing catalog, import --strict under fresh ROBOCORP_HOME, publish the exact package with --no-build --provider local. Observe producer-base restore during compatibility collection; later portable env execution may still be target-local.
Expected integration behavior: all writes for fresh target preparation remain within its owned storage. Actual: legacy RestoreTo uses catalog parent path.
Classification: confirmed local observation and source cause; upstream defect versus documented legacy portability limitation requires maintained-contract review. No public issue filed. No deduplication search completed. No external issue authority supplied. Follow-up: verify supported portability contract and deduplicate before requesting issue-only authority. Downstream gate: native a44 target-contained compiler preparation. Temporary workaround: none approved; no metadata rewriting, trust reuse or security override.

## Canonical documentation correction

“A successful holotree import and subsequent publish do not prove target-contained writes. In pinned RCC 18.19.3, compatibility inventory uses the imported catalog's legacy base path. Verify restore paths as well as final exec paths; block cross-base preparation unless a supported relocation mechanism is qualified. Changing --space changes only the basename.”

Documentation-improvement receipt: exact correction supplied to root; canonical files unchanged. Upstream disposition: draft only, no confirmed supported-contract violation yet and no external mutation.
