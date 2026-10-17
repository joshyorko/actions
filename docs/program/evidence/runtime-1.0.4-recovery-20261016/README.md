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

## Remaining gates and owner boundary

A read-only follow-up at `32830e6e0e9b6a65e72d1ff0ac495bb310eb3603` verifies the reseeded carrier with A. Final exact-head hosted CI/native results will be recorded in the final evidence checkpoint and PR325 before handoff. No passing result is claimed here for those pending runs.

Production-controller activation remains **UNRUN until an approved merge of Draft PR325**. The branch qualification calls the unchanged shared verifier with exact code-blob binding; it does not bypass or pretend to exercise the production controller's current-community guard.

After review/approval, merge PR325 while preserving the production workflow tree, then run **Publish Actions Runtime Release** on current community with `operation=validate`, `preparation_run_id=38951733318`, `source_sha=d222f94edca26953c1506ab258adc458ded17c56`, `expected_version=1.0.4`, `manifest_sha256=1a77f6c8e09869d6bd45df1b14e6a9ce3f908bcf09351b76cee26a209504878a`. A registered owner backup run may replace the transport ID only if needed; the other immutable inputs stay original.

Do not rerun/delete the protected preparation or backup runs. Renew exact-byte copies before expiry and review the registry update; publication still requires two healthy registered runs. Final publication remains Josh's separate action. No merge, tag, package, native release, template, deployment, credential or security-setting mutation was performed by this repair campaign.

Existing upstream platform report: [actions/upload-artifact#323](https://github.com/actions/upload-artifact/issues/323). No new upstream issue was filed.
