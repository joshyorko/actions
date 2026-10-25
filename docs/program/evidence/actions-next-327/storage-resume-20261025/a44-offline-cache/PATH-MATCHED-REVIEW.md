# Fixed absolute path workaround review

Viable, conditionally, for the identified RCC 18.19.3 legacy restore-base defect. Build the public dependency catalogs on the producer under exactly `/tmp/actions327-a44-offline-v1/compiler`, with ROBOCORP_HOME exactly its `robocorp` child. Import and publish on the target under the same absolute root. This avoids relocation rather than changing RCC metadata or policy.

Source basis: htfs/library.go RestoreTo joins the catalog's HolotreeBase with ControllerSpaceName. htfs/directory.go HolotreeBase is the parent of the catalog's embedded path. User/controller differences affect only the basename. Therefore matching the base keeps this restore destination within the target-owned root. Local env publish still generates new target provenance/SBOM/revocations as previously traced; export no producer trust or receipts.

Preconditions for the root-owned experiment:

- Root and existing ancestors resolve canonically without symlinks; target compiler root must not exist before preparation. Keep owned HOME, TMPDIR, ACTIONS_HOME and ROBOCORP_HOME beneath it.
- Build fresh catalogs there; do not reuse the earlier cross-base catalogs. After export, inspect every compressed catalog's JSON `path`, not merely its .info sidecar. Its parent must equal `/tmp/actions327-a44-offline-v1/compiler/robocorp/holotree`, basename must equal `identity`, and platform must be linux_amd64. Include base and pip catalogs selected by the observed exact blueprint identities, not assumed historical IDs.
- Transfer only the supported catalog/library zip plus independently hashed exact package and Core wheel. Verify archive names/inventory, embedded paths, bounded expanded size, and absence of credential/trust files before deleting any producer-owned materialization. Preserve evidence and export outside the directory being cleared.
- Target imports through `holotree import --strict`, publishes exact package with `--no-build --provider local`, records actual restored paths, and runs isolated full Core 87-member verification using its newly generated local trust and observed digests. Retain the approved low-capacity bounds and owned subreaper cleanup.

This source review proves the relevant restore-base expression when those preconditions hold. It is not a blanket claim that arbitrary archive payload/symlinks cannot escape, nor an execution result. Do not claim target containment until the root-owned fresh-target experiment checks emitted paths and retained files. No commands were run beyond read-only inspection in this lane.

Canonical documentation proposal: “Pinned RCC legacy catalogs retain their absolute build base. A fixed-path offline cache transfer may avoid cross-base restore only when producer and fresh target use the exact same canonical owned root and every compressed catalog path is verified before import. Keep this qualification distinct from general relocatable artifact support; target publish must still generate new trust and rerun payload proof.”

Documentation-improvement receipt: exact proposal delivered to root; shared docs unchanged. Upstream disposition remains draft-only as recorded in RELOCATION-BLOCKER.md; no external mutation or approved RCC source fix.
