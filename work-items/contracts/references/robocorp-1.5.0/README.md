# Pinned Robocorp Work Items reference

Inert source authority for contract verification, not a runtime dependency or executable test package.

Original repository: https://github.com/robocorp/robocorp
Commit: 631f5601617e9935620a72c788a98e1012331323
Root tree: 0d9491c93ca6b196426dfda767ce7de34e5f2182
License: original Apache License2.0 in payload/LICENSE. Original source bytes and notices are unchanged. No applicable NOTICE file exists in the pinned root/workitems tree. This README, inventory and object-proof container are owned packaging metadata, not upstream source files.

payload contains17 original files totaling108,209 bytes: all11 package Python files, the three complete source test suites, fixtures.py, mocks.py and root LICENSE. The complete test_adapters.py preserves excluded Control Room nodes for selection-gap checks. Package sources are parsed only; no upstream dependencies are installed or imported. Runtime distribution package declarations remain under src/ and do not add this fixture as an importable package.

inventory.json records original paths, byte counts, SHA256 and Git blob IDs. object-proof.json retains the exact raw commit object and8 complete ancestor-tree objects, base64 encoded. Raw Git object framing/hashing matches the existing immutable commit pin; tree entries authenticate every selected blob and every package Python path. The commit and ancestor trees were reconstructed from pinned public Git object metadata and accepted only after reproducing their exact object IDs. The commit is unsigned: this is commit-addressed source provenance, not author-signature verification.

Do not update these files using the mutable offline digest --write command. An intentional upstream reference change requires review of the new pin, complete source/license bytes and corresponding Git proofs. Routine authoritative verification needs neither upstream checkout nor network; the separately pinned owned custom Git root remains mandatory and is not bundled here.
