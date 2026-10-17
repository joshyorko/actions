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

## Final CI and owner boundary

Read-only follow-up [38982004911](https://github.com/joshyorko/actions/actions/runs/38982004911), head `32830e6e0e9b6a65e72d1ff0ac495bb310eb3603`, passed with actions:read. It verified owner original/A/B and disposable A/reseeded-C transports after original loss, all nine negative controls and unchanged owner snapshots. No second rerun or publication occurred.

Final repair source is `d3656450bf9ddddef29b9aab5c86a316e394024c`; its release-code blobs equal the qualified implementation at `221edc4e7357aca64fc654f8ab5805c484042f2c`. All eight workflows and all 26 jobs passed at final repair head `d3656450bf9ddddef29b9aab5c86a316e394024c`, including Linux/macOS/Windows Runtime integration, all three native builds and acceptance, all six toolkit jobs, package qualification, Core, HTTP Helper, coverage and audit. Implementation head221ed also passed all eight workflows. See `ci-current-head.json` and `implementation-head-ci.json`. An earlier intermediate head had one Windows post-cancellation10-second read timeout; its exact outcome is retained in `intermediate-ci-failure.json`, without changing tests or claiming a Runtime repair.

Production-controller activation remains **UNRUN until an approved merge of Draft PR325**. The branch qualification calls the unchanged shared verifier with exact code-blob binding; it does not bypass or pretend to exercise the production controller's current-community guard.

After review/approval, merge PR325 while preserving the production workflow tree, then run **Publish Actions Runtime Release** on current community with `operation=validate`, `preparation_run_id=38951733318`, `source_sha=d222f94edca26953c1506ab258adc458ded17c56`, `expected_version=1.0.4`, `manifest_sha256=1a77f6c8e09869d6bd45df1b14e6a9ce3f908bcf09351b76cee26a209504878a`. A registered owner backup run may replace the transport ID only if needed; the other immutable inputs stay original.

Do not rerun/delete the protected preparation or backup runs. Renew exact-byte copies before expiry and review the registry update; publication still requires two healthy registered runs. Final publication remains Josh's separate action. No merge, tag, package, native release, template, deployment, credential or security-setting mutation was performed by this repair campaign.

Existing upstream platform report: [actions/upload-artifact#323](https://github.com/actions/upload-artifact/issues/323). No new upstream issue was filed.

Final preservation check at 2026-10-17 00:12 UTC confirms the owner preparation/artifact unchanged; both owner backup pairs unexpired; frozen1.0.3branch/tag/four native assets unchanged; no1.0.4tag, native release or PyPI version exists. No external blocker remains for review. The exact remaining owner decision is approval to merge325, followed by read-only production validation. Final publication remains separately with Josh.

`HANDOFF.json` contains the original317/318heads, all repair/qualification identities, passed/expected-failed/unrun gates and exact production validation inputs. `final-publication-and-preservation-state.json` records the live preservation/publication checks.
