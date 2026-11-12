# Approved dual-evidence qualification

Supersedes the pending contract proposal, not the original failed receipt.
Integrator approved raw declaration plus separate selected-profile evidence.
Producer labels `sbom_dependencies: DECLARED`; success is scoped to dependency
inventory/provenance evidence, not runtime reachability, signing or publication.
The original strict FAIL remains in python-sbom-producer/receipt.json, and the
new receipt also records strict_active_graph.result=failed explicitly.

Actual wrapper execution exited 0 on the original a38 consumer with 67 Runtime
packages plus bootstrap pip, all 68 declaration nodes independently matched and
29 inactive edges accounted for by markers/extras. Raw standard producer output
is byte-identical to the preceding failed run (SHA256
183898f562696bbab4437de84c853dda67cc799ff2431d3038400ee30275aba1).
No edges were removed or rewritten. Runtime wheel source is da928b69, not the
frozen combined candidate. Native/OS inventory and native platform qualification
remain outside this Python-only result.

Reproduce using the exact command/environment in ../python-sbom-producer/README.md,
changing only --output-dir to /workspace/lane-d/producer-dual-qualified. Directory
must not exist. Additional artifacts are declaration-reconciliation.json and
resolved-graph.json, each hashed in receipt.json. Prior inspect/wheel/lock binding
checks remain. Installed members verified before/after: 319. Existing limitations
remain: caller digest is not signature authority; snapshots do not defend against
a hostile concurrent mutator; selected extras are supplied profile context.

Integration hook remains integrator-owned. It should consume all three documents
(raw SBOM, resolved graph, reconciliation) and receipt, preserving the DECLARED
label and strict-failure field. Never present this scoped success as raw-active
graph equality. No new release workflow/version/config changes were made.

Tests: new independent validator tests include captured actual export and seven
mutation negatives. Existing strict active-graph mutation tests remain unchanged.
Full devutils stdout/XML are retained here. Lint/format checks use package-local
tooling. Rollback this slice restores the previous strict producer behavior;
no schema/dependency migration is involved.

Canonical guide delta for integrator: “Admit Python dependency evidence only when
raw declared graph exactly matches installed metadata projection, selected-profile
closure separately passes, and every difference is explained by inactive markers.
Keep raw bytes intact, label dependencies DECLARED, bind both views and the full
reconciliation by hashes, and preserve strict-active comparison results. This is
inventory/provenance evidence, not measured execution reachability.”

Learning/evidence: actual producer output remains identical under the approved
contract; only evidence evaluation differs. Uncertainty: no runtime call-graph
measurement or native/OS SBOM. Upstream disposition: no established upstream
contract violation and no external report/publication performed.
