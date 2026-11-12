# Generated Knowledge v3 source checkpoint receipts

SOURCE COMPONENT / SYNTHETIC QUALIFICATION ONLY. Installed a39 acceptance is pending. No fixture, database, corpus blob, cache, wheel, AppSession, credential or live client artifact is included. Root integrates explicit files through the publishing guard; this directory is outside Git and makes no publication or merge claim.

## Results and interpretation

- source-joined: 18 selected modules, 563 passed, zero failed/errors/skipped; selected.json inventories, per-module receipts and original stdout/XML (base64) retained. These tests cover source/component and synthetic generated-host paths, not actual installed generated RCC execution.
- core-suite: 411 passed, zero failed/skipped; exact selected inventory and stdout/XML retained. Older helper Core attempts remain separately retained and overlap.
- post-format: two modules, 20 passed, zero failed/skipped, cleanup_exit=0. This is a repeat subset, not 20 additional unique cases.
- quality: final-types.log reports success across 581 source files. final-style.log failed on fixture imports; final-style-fixed.log failed on three F811 fixture-shadowing diagnostics. final-style-qualified.log succeeds after documented test-only suppression. Both earlier failures remain failures.
- helpers/compiler, helpers/contract, helpers/search, helpers/core: original failing and final passing receipts plus explanatory READMEs/counts/source hashes. Compiler final 65 passed/one skipped; contract final54 passed; search final20 passed. Historical runs overlap and must not be added into a campaign unique-pass total. The compiler README discloses overwritten baseline stdout; surviving baseline XML and separately named old-baseline log are retained, not reconstructed.
- helpers/full-publication: original red, confirmed-red, corrected and combined helper receipts retained; source-only full wrapper final-publication checks.
- review-B337: independently reviewed exact1ae380539fff0803efd3934615c8a571358fd19f, helper-only18passed; no installed lifecycle claim.

## Source identity correction

The source-joined and post-format joined-summary.json fields named source and tree identify the BASE commit5b16289da3d0f45f3d2534a4abf29fb1e3a9463e and its BASE tree. They are NOT the tested dirty source tree. Preserve original receipts; do not relabel those identifiers as a tested immutable checkpoint. Batch source_sha256 pins the selected test module at execution, not all production dependencies.

dirty-source-manifest.json records exact SHA256 for current changed production/tests and package metadata, captured after successful final formatting. It is a checkpoint snapshot, not retroactive proof that every historical batch executed those exact bytes. The upcoming integrator commit should bind these source bytes and receipts; installed qualification must pin that immutable candidate independently.

## File map and privacy

filemap.json gives original private source path, original SHA256, decoded-payload SHA256, staged-file SHA256, encoding implied by .b64, byte count and redaction status for each receipt. Decode .log.b64/.xml.b64 to inspect. sanitization.json records pre-encoding credential-like scan findings; no credential-like lines matched. Original bytes are preserved when redacted=false. Credential-shaped JSON fields were also inspected with the repository evidence guard's recursive inspector. No secrets were transferred; this bounded scan does not replace the integrator's mandatory staged guard.

Candidate canonical guide addition is documentation-delta.md. Upstream disposition: none.
