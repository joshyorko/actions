# a38 canonical execution checkpoint

Base source: bd03a285a38072e3a07822c216700d4f66bf7b84 plus exact files in
source-sha256.json. This is source qualification; clean installed/client proof
is a separate gate. No publication or release-ready claim.

- Real pinned RCC compilation and execution of two independent typed Actions in
  one immutable Package and Deployment: **2 passed, 0 skipped**, common SQLite
  and PostgreSQL. Both selected plans produce expected values and four sealed
  artifacts; replay retains the same Run/Attempt and rejects another execution.
  Mismatched capability/plan selection is denied before any Run. Artifact reads
  require both Run and application authority.
- Registry denial translation regression: initial **7 passed, 1 failed**;
  corrected **8 passed**. The real registry's denial now becomes the execution
  boundary's bounded AccessDenied, matching other selection failures.
- Integrated Knowledge execution: **76 passed, 0 skipped**, common SQL SQLite
  and PostgreSQL crossed with actual DuckDB and PostgreSQL version stores.
  Covers retained ingestion, canonical publication, bounded search, revoked
  authority, cancellation, publication-failure replay, tampered/expired receipts
  and fresh-process reconstruction. This explicit host-bound service is not yet
  ordinary installed Knowledge operator/Task/generated-Python wiring.

Prior runs remain failures: canonical (2 mismatched-denial failures),
canonical-corrected (2 wrong test handle-shape failures), canonical-final
(2 missing independent application-read grant failures). knowledge-integrated
failed before collection because its copied launcher was missing. The corrected
knowledge-qualified run executed all 76 cases. No failed run is relabeled.
Exact selected inventories and per-run receipts are retained. XML diagnostics
are base64 encoded without changing their bytes; xml-sha256.json verifies the
decoded originals. Private fixtures, credentials and bulk RCC logs are excluded.

The prepared RCC artifact was built using exact Core a3 wheel
4147cdeb2a593e54194b4d2fcd2c92f0b029fb802d1d298e35c912a1fef03167,
portable package.yaml, and an owned local RCC wheel directory. Actual isolated
RCC inspection matched all 52 installed Python members to that wheel.
Prepared artifact: sha256:23094fc1820262a768fd601f4964d633417fc2641f349666a5be55ab524f7598.

Rollback: restore the prior candidate and its pre-migration snapshot together;
version 21 readers reject schema 22. No downgrade in place, force push, merge,
public tag, credential or production change is part of this checkpoint.

Upstream disposition: none.
