# Work Items owned reference audit

Recommendation: replace only the mandatory robocorp/robocorp checkout with an owned, inert reference bundle authenticated to the existing commit. Retain the explicitly owned custom reference checkout initially; its licensing provenance needs reconciliation before a second bundle. No repository source edits, installations, RCC/database/build workloads or external mutations were performed. Read-only pinned GitHub API/raw reads produced the evidence here.

## Existing verification meaning

.github/workflows/work_items_release.yml checks out both exact commits and invokes work-items/scripts/check_contract_port_provenance.py with both roots. _verify_authoritative requires HEAD identity, derives selected tests from complete source suites, checks normalized AST bodies, selected class decorators, fixture signatures, declared exclusions and public exports/signatures. _definitions recursively parses every package Python file. Plain offline mode checks a mutable local digest only; substituting that mode would weaken the gate. Existing HEAD validation does not itself check dirty working-tree bytes; object-authenticated local reference bytes can improve this boundary.

## Minimal Robocorp bundle without changing semantic checks

Commit: 631f5601617e9935620a72c788a98e1012331323.
Root tree: 0d9491c93ca6b196426dfda767ce7de34e5f2182.
Payload: 17 files / 108,209 bytes: all 11 Python files under workitems/src/robocorp/workitems; test_adapters.py, test_email.py, test_workitems.py, fixtures.py, mocks.py under workitems/tests/workitems_tests; root LICENSE. Keep complete test_adapters.py, including excluded Control Room class, because selection-gap and explicit exclusion checks need it. Keep all package Python files rather than selecting only current exported definitions: existing recursive traversal and duplicate-definition ordering remain identical. No package execution/import is required.

Exact file sizes, Git blob IDs and SHA256 values are in inventory.json; bytes are in reference-files/robocorp. License is the original Apache-2.0 text, 11358 bytes, SHA256 3e4fd3f14628823f070a603435a95eff548eae90ba23d7fcbca2f1526c136f3e; upstream pinned tree has no applicable NOTICE file. Preserve copyright notices and add a clearly separate acquisition/provenance README without rewriting upstream payloads. Exclude this inert fixture from wheel/package runtime discovery.

robocorp-object-proof.json contains an exact 261-byte raw commit and eight necessary complete ancestor-tree objects totaling 2,099 bytes. Locally reconstructed objects match the immutable commit and tree IDs using Git object framing; every downloaded payload matched its expected Git blob ID, length and recorded SHA256. Thus the binary payload plus raw Git proof is 110,569 bytes before JSON/base64 inventory overhead. Full upstream history, unrelated blobs, a clone, and upstream access during routine verification are unnecessary. Proof is anchored to the already reviewed commit pin, not to an independently editable list of SHA256 strings. Both commits are unsigned; do not claim author signature attestation.

## Smallest owned patch

1. Add work-items/contracts/references/robocorp-1.5.0/ with those 17 unmodified payload files, raw object proof, file inventory and attribution README. Use stored original paths. No cloud SDK, optional adapter execution, or active upstream dependency is added.
2. Extend check_contract_port_provenance.py with --robocorp-reference, mutually exclusive with --robocorp-root and requiring --custom-root. Validate raw commit hash equals the existing manifest pin; parse its tree; hash/parse every required ancestor tree; resolve each required original path to its exact mode/blob; verify exact bytes and SHA256/size. Reject traversal, symlinks, extra Python files, missing files, altered modes/types and unreferenced proof objects. Inventory must cover exactly every Python file in the complete package trees and the five required tests plus LICENSE, not merely a user-supplied subset. Do not permit --write to regenerate this authority.
3. Refactor only acquisition/identity validation so both checked Git roots and the authenticated owned bundle feed the same _verify_authoritative semantic comparison body. Preserve original explicit two-Git-root mode and wrong-HEAD failures. For Git mode, consider verifying selected working-tree bytes against pinned blobs, but do not silently broaden this minimal change.
4. Remove only the Robocorp checkout step in work_items_release.yml; pass the owned reference flag and keep the pinned custom checkout. Do not touch tag/publication approvals or dependencies.
5. Update docs/skills/work-items.md to distinguish immutable-object offline authority from the existing mutable digest diagnostic. Root owns documentation integration.

## Required red/green plan

New focused tests under work-items/tests/work_items_tests: successful bundle with networking/subprocess checkout unavailable; parity of reference and two-Git-root semantic inventories; failures for commit/tree/blob corruption, same-length source tamper, changed license, missing required source, inserted duplicate-definition Python file, path traversal/symlink, changed class decorator/fixture signature/assertion/public export and invalid flag combinations. Ensure immutable bundle cannot be refreshed by --write. Existing 123 selected-node semantics and exclusions stay unchanged. Run full Work Items package tests and authoritative gate using the owned reference plus exact custom checkout through prepared gateway. No backend skips become passes. No tests were executed in this read-only audit; object/hash reconstruction checks are the observed verification.

## Custom reference limitation

Pinned custom commit c56c70102423a18ed54037221116f81ccccd4f4e has tree 1abf68bcacec8724458f1b491dcd1d1dad9fcf0b. Its pyproject.toml declares MIT; README says '[MIT](LICENSE) (or project-specific license)', but its complete tree contains no LICENSE/NOTICE. Local ported-tests.json instead labels custom Apache-2.0 and local custom source snapshot adds Apache copyright text. This is a real metadata inconsistency, not evidence of authority to relicense newly copied entire custom modules. Evidence copied here for review includes 15 verifier-required Python files (216,922 bytes) plus pyproject/README, 17 files/230,755 bytes total; custom object proof also hashes to its exact commit. Owner clarification of intended license/copyright and inherited Apache portions is required before treating the entire custom source bundle as licensed under one label. No external mutation is requested or performed. Robocorp-only closure can proceed independently.

Documentation improvement:
- Proposed canonical file: docs/skills/work-items.md, Compatibility Contract Inventory.
- Exact initial addition: “The current source-authority gate still requires both pinned Git roots; offline digest verification alone is not a substitute. An owned reference can replace upstream availability only when original source and license bytes are authenticated through Git blob/tree/commit objects to the existing immutable pin and the same semantic checks still run. The custom reference's pinned license metadata must be reconciled before attributing a new full-source fixture.”
- Durable learning: selected-node snapshots alone omit public-surface and exclusion authority; preserve full reference suites, recursive package source coverage and original license.
- Evidence: current verifier/workflow; pinned object proofs; inventory.json; pinned custom pyproject/README.
- Stale/ambiguous guidance: after implementation replace the unconditional upstream-checkout requirement with the dual supported authenticated-source modes, retaining the distinction from mutable offline diagnostics. Do not claim the planned bundle is already implemented.
- Remaining uncertainty: custom licensing reconciliation; implementation and semantic parity tests pending.

Upstream disposition: none. No upstream functional defect established. Custom licensing is an owner clarification item; no authorized external issue target or mutation.
