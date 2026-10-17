# Runtime 1.0.4 exact-byte recovery qualification

The repaired verifier and nonpublishing archiver were qualified at code source
`221edc4e7357aca64fc654f8ab5805c484042f2c`. The original release source remains
`d222f94edca26953c1506ab258adc458ded17c56`, qualification
`9e8cfd7caa602031db4eba75f545b1211f882561`, version `1.0.4`.
Production workflow files and the original release bytes remain unchanged.
This evidence contains metadata and hashes, no binaries, credentials or signed URLs.

## Passed recovery gates

- Full Devutils: 249 passed; qualification guards: 10 passed; configured static checks passed.
- Fresh independent read-only review: no findings; all eight initial cached ZIP hashes/sizes recomputed; all four backup workflow blobs match the reviewed template.
- Owner preparation `38951733318`, artifact `12069321636`, remains attempt 1 SUCCESS and unchanged before/after the rehearsal. Its exact ZIP SHA-256 is `bbe3d066fb082c1dc61a8916af549bf9a7b66369f36866a2b37a8256a95524e5`; manifest SHA-256 is `1a77f6c8e09869d6bd45df1b14e6a9ce3f908bcf09351b76cee26a209504878a`.
- Independent owner backups `38977206416` and `38977943959` each retain the exact original ZIP, unchanged manifest and all 34 members, with payload/raw artifacts expiring January 14, 2027. Registry contains only these owner copies.
- A new explicitly disposable preparation `38977611441` was archived twice, then rerun exactly once. Attempt 2 refused rebuilding with the expected guard; its original artifact `12080295206` disappeared while original attempt 1 remained successful.
- Hosted qualification [38981527410](https://github.com/joshyorko/actions/actions/runs/38981527410) at `692d8a1954cedcce30af4288b3e72881cf6156ed` passed retrieval through both disposable backups `38978632251` and `38978889937`, and owner original/A/B transports. Every original manifest and all 34 members matched.
- All nine negative controls passed: absent original, wrong manifest digest/source/version, unregistered transport, wrong registered artifact, one-copy publication refusal, same-size wheel corruption and changed original manifest.
- Reseed [38981788683](https://github.com/joshyorko/actions/actions/runs/38981788683) at `9cd625d87bcc33092f39143f2a0b5b0b488ab879` used only disposable A's registered **raw archive**, after original loss. Its receipt says `source_kind=registered-raw-archive`; independent downloads verify the exact original ZIP/manifest/all 34 members. Backup B remained physically stored; only A was configured for this test.

## Approved activation and owner publish handoff

Josh approved merging PR #325 and the nonpublishing production validation. PR #325
merged as `0e80d41c6b4e5df9579675731e6cdbda733acd35`. The merged tree equals tested
PR head `d3656450bf9ddddef29b9aab5c86a316e394024c` exactly, including the unchanged
production workflow tree. The eight PR workflows and all 26 jobs remain successful.
Fresh local premerge Devutils verification passed 249 tests again. All five post-merge push workflows and all 17 jobs also passed, including native Linux/macOS/Windows and all six toolkit jobs. See `postmerge-ci.json`.

Production validation [39016104442](https://github.com/joshyorko/actions/actions/runs/39016104442)
ran the actual production workflow on `community` at that merged controller.
It passed using original preparation `38951733318` and artifact `12069321636`,
original release source `d222f94edca26953c1506ab258adc458ded17c56` and original
manifest `1a77f6c8e09869d6bd45df1b14e6a9ce3f908bcf09351b76cee26a209504878a`.
The `validate` job succeeded with Actions/Contents read permissions; `publish`
was skipped. The original ZIP digest matched, the existing strict source/member/
package checks passed and both registered raw backups passed fresh byte checks.
The read-only result leaves private-draft ownership for the eventual writer to
verify before any write.

`production-validation.json` records the exact run/jobs/permissions/output.
`dispatch-receipt.json` records the single validate dispatch. `merge-and-preflight.json`
records the approved head/base, merge identity, reviews, tests and exact tree match.
`post-validation-preservation.json` confirms the protected owner and both backup
pairs unchanged/unexpired, frozen 1.0.3 branch/tag/four native assets unchanged,
and no 1.0.4 tag/native release/PyPI version after validation.

The owner workflow URL was verified active and returned HTTP 200:
[Publish Actions Runtime Release](https://github.com/joshyorko/actions/actions/workflows/runtime-release-publish.yml).
The copy-ready fields are in `owner-publish-inputs.json` and `OWNER-PUBLISH-HANDOFF.md`.
The original release `source_sha` stays unchanged; the current community controller
is the new merge commit. Final publication remains Josh's separate click.

Existing upstream platform report: [actions/upload-artifact#323](https://github.com/actions/upload-artifact/issues/323).
No new upstream issue was filed. No package/tag/native release/template/deployment
publication or credential/security-setting change was performed.
