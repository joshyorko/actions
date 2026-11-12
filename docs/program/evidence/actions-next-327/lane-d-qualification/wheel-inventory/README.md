# Exact retained candidate wheel inventory

This follow-on gate qualifies only the retained Linux CPython 3.12 a38 wheel
built from production source da928b69, recorded by the earlier lane build receipt:

`actions_runtime-1.1.0a38-cp312-cp312-linux_x86_64.whl`

SHA256: `34f5b7c1db29d4def4ba84214d225f6b82d037fa39e3b819eab6fe1ff15898ce`.

The frozen first combined Canvas artifact and newer production changes (including
list_indexes) are NOT qualified by this wheel. The checker verifies an explicitly
supplied artifact digest; it does not independently attest source or builder origin.

Inspection found the existing release bundle validates external inventory/digests,
while the installed-wheel verifier checks selected Python bytes/origins. The new
read-only gate additionally verifies every archive member against wheel RECORD,
including non-Python assets and the embedded RCC binary. No existing pipeline,
metadata, versions or production helper is changed, and no publication occurs.

Prepared RCC 18.19.3 and package-local Poetry command from `action_server`:

```bash
poetry run python scripts/qualify_wheel_inventory_327.py \
 --wheel /workspace/lane-d/wheels/actions_runtime-1.1.0a38-cp312-cp312-linux_x86_64.whl \
 --expected-sha256 34f5b7c1db29d4def4ba84214d225f6b82d037fa39e3b819eab6fe1ff15898ce \
 --expected-version 1.1.0a38 \
 --output /workspace/lane-d/receipts/candidate-wheel-inventory.json
```

**PASS: 320 archive members**, exact RECORD membership, SHA256 and size checks;
26 `Requires-Dist` declarations retained verbatim from the hashed METADATA.
Embedded `actions/server/bin/rcc-18.19.3` hash matches the pinned Linux release:
`7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`.
The receipt includes each member's path, size and digest, without extraction or
executing wheel contents. It creates a new output file, never overwrites evidence.

From `devutils`: `poetry run pytest tests/test_wheel_inventory_327.py -q
--junitxml=/workspace/lane-d/receipts/wheel-inventory-tests.xml`: **10 passed**.
Nine malformed internal inventories are rejected even when the supplied outer
hash matches those altered bytes: duplicate RECORD/archive members, incorrect
size/hash/self-entry, unrecorded/missing/tampered members and path traversal.
The positive control also checks wrong selected digest and distribution version.
Fixtures are synthetic wheel archives; the 320-member qualification is real.

Scope limitations: this is checksum/internal-inventory consistency plus declared
dependency provenance, not signature verification or a resolved/transitive SBOM.
The declarations do not establish installed versions, hashes, licenses or CVEs.
The strict checker admits SHA256 RECORD entries and rejects explicit directory
entries; it is qualified for this measured producer, not arbitrary third-party
wheel formats. Native executable/image inventories, full resolved SBOM and
cross-platform/reproducible builds remain separate required gates.

## Exact canonical-guide delta for integrator

> Bind a wheel qualification to its explicit outer digest, then verify exact ZIP
> member/RECORD membership and every non-RECORD member's size/hash, including
> bundled non-Python binaries. Keep duplicate-member and matching-outer-hash
> mutation negatives. Wheel METADATA Requires-Dist fields are declarations tied
> to those bytes, not evidence of a resolved dependency graph or complete SBOM.
> Do not transfer an earlier wheel's receipt to a newer combined source build.

Evidence: real 320-member receipt, embedded RCC digest and ten passing controls.
Removed ambiguity: external bundle checks imply internal wheel inventory checks;
dependency declarations constitute resolved SBOM proof. Uncertainty: resolved
closure, native/image inventory, signatures and later candidates.
Upstream disposition: none. Rollback removes the dedicated script/tests/evidence;
no runtime state or dependency changes require recovery.

Affected full devutils suite: `poetry run pytest tests -q
--junitxml=/workspace/lane-d/receipts/devutils-inventory-full.xml`:
**286 passed, zero skips**. Changed-file Ruff, formatter, Isort and diff checks pass.
Task-local `POETRY_CACHE_DIR` and `XDG_CACHE_HOME` remained set for execution.
