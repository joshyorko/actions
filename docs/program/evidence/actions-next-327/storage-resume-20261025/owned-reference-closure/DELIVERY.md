# Owned Robocorp reference closure

READY FOR ROOT REVIEW; isolated only. Active checkout unchanged. Patch reference-closure.patch SHA256463e66af5ed43e5c4743b310259317809e0cb238656f8a8f705fd6725580f1c8,144,053bytes,23files. git apply --check passes. workflow.patch separately shows the only workflow changes: remove Robocorp checkout, replace --robocorp-root with --robocorp-reference. Pinned owned custom checkout remains unchanged.

Scope: verifier, one portable test module,17 exact upstream payload files, original Apache-2.0 LICENSE among those17, inventory/object proof/README. Source/license payload108,209bytes. Exact source pin631f5601617e9935620a72c788a98e1012331323/tree0d9491c93ca6b196426dfda767ce7de34e5f2182. No custom reference source is included in the patch. Original notices/bytes remain intact. patch-files.json contains baseline/candidate hashes.

Verifier --robocorp-reference validates commit object framing/hash against the existing immutable pin, complete connected ancestor trees, all required payload blob IDs and SHA256/length inventory. Required scope is independently derived from the pinned package trees and exact five test/fixture paths plus LICENSE; a mutable inventory cannot silently omit or substitute files. Extra payloads, symlinks, unsafe proof/tree paths, unreferenced proof trees, missing or corrupted files fail. The same authoritative AST/decorator/fixture/exclusion/public-surface comparison body follows authentication. Existing two-Git-root mode and offline diagnostic behavior remain; custom Git HEAD remains mandatory and --write is rejected in authority modes.

Observed validation through prepared Work Items developer gateway:
-20 portable new tests PASS in2.27s before formatting, then included in final full suite. Test cases cover byte/commit/tree/license tampering, missing/extra source, symlink/traversal, inventory metadata, orphan proof, unchanged Robocorp semantics across source modes, assertion/decorator/fixture/export failures, invalid CLI combinations and custom HEAD failure. Portable unit parity uses an explicit synthetic custom fixture and mocks only its public surface; no custom source is redistributed.
-Independent real parity gate PASS: original verifier/two Git roots and candidate verifier/owned reference+custom Git root both passed with exact original sources and actual raw pinned commit/tree/blob objects. No mock bypasses in this gate. Minimal local Git object stores were assembled from the previously hash-verified audit evidence; these and custom audit copies remain scratch-only and are excluded from the patch. No network or external repository mutation occurred.
-Full affected Work Items suite with isolated test/validator tree:285passed,46skipped,3deselected,10xfailed in15.15s.18skips require canonical PostgreSQL fenced gate;13Redis and15MongoDB contract cases skipped;3persistent backend service tests explicitly deselected;10prior expected-red compatibility gaps remain xfailed. None are claimed passed. No PG/RCC materialization or external service workload was started.
-New test Ruff check PASS. Verifier has exactly the same10 preexisting UP038 lint diagnostics as original, no new diagnostics; lint-comparison.json retains baseline/candidate comparison. Added validator block and new test formatted; unrelated existing style was not rewritten.

Source origins: candidate verifier and tests live under candidate/work-items; full suite command explicitly selected its pyproject and tests. Existing contract-ledger tests were copied unchanged and resolve their ROOT to the candidate, so old authority flag/head checks exercise the candidate verifier. Runtime library source is unchanged and remains the prepared Work Items environment's installed package. Candidate/reference fixture bytes were not imported as runtime modules. No original package tests or source files were overwritten.

Next exact gate: root reviews/applies the focused patch after concurrent-source safety, reruns the authoritative candidate command with the retained pinned custom checkout and standard release gates. No source tree/network check should be substituted by the mutable offline digest. Existing external-service qualification remains independently pending.

Documentation improvement:
- Canonical file proposed: docs/skills/work-items.md, Compatibility Contract Inventory.
- Exact replacement text and command: canonical-delta.md.
- Durable learning: complete Git object ancestry can retain immutable source authority offline; selected test snapshots or mutable digests alone cannot.
- Evidence:20new boundary tests, real original/new authority parity,285available full-suite passes, exact source and payload hashes.
- Removed ambiguity: explicit upstream checkout is no longer the only supported source-authority acquisition; mutable diagnostic mode is still not authority.
- Remaining uncertainty: excluded service gates; custom pinned licensing inconsistency remains unresolved and no new custom attribution is made.

Upstream disposition: none. Owned reference acquisition change; no upstream defect or external issue target.
