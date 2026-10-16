# Josh's Runtime 1.0.4 publication inputs

Source qualification and preparation are complete. Owner read-only validation
passed twice (runs38953955933 and38954043063); wrong-digest and missing-artifact
controls refused their inputs and every publication job was skipped. The failed
preparation-rerun recovery gate remains in the accompanying report. This handoff
does not publish.

Open [Publish Actions Runtime Release](https://github.com/joshyorko/actions/actions/workflows/runtime-release-publish.yml),
choose **Run workflow**, branch **community**, then copy these inputs. The default
operation is read-only `validate`. Josh alone changes it to `publish` when he
chooses to publish this release; both original and triggering actor must be Josh.

| Input | Value |
|---|---|
| `operation` | `publish` (Josh's final decision only) |
| `preparation_run_id` | `38951733318` |
| `source_sha` | `d222f94edca26953c1506ab258adc458ded17c56` |
| `expected_version` | `1.0.4` |
| `manifest_sha256` | `1a77f6c8e09869d6bd45df1b14e6a9ce3f908bcf09351b76cee26a209504878a` |

[Original successful preparation](https://github.com/joshyorko/actions/actions/runs/38951733318),
artifact `runtime-release-bundle-38951733318-1`, ID `12069321636`, expires
**2026-11-15T19:02:03Z**. Preserve this run and its original attempt1 artifact.
The full GitHub ZIP SHA-256 is
`bbe3d066fb082c1dc61a8916af549bf9a7b66369f36866a2b37a8256a95524e5`.
Independent download review verified the archive and all 34 retained files.
The manifest is included alongside this handoff; its digest is distinct from
the archive digest.

The complete release source tree is `c426aad8258a61da8dbf592696ea37a5499e5bb4`,
equal to qualified source `9e8cfd7caa602031db4eba75f545b1211f882561` and the
approved #321 staging merge. No local Poetry command, hand-created tag,
legacy publisher dispatch, new credential or security-setting change is needed.

The button publishes the seven retained PyPI distributions and four unsigned
native assets, then creates the immutable source tag and makes the complete
native release public. Unsigned admission was checked with all existing native
signing credentials absent; it does not bypass configured signing. It performs
no template, Homebrew or deployment action. Cross-service publication is not
atomic. If interrupted, inspect actual remote state, retain this original
preparation, and retry publication with these same immutable inputs. Never
rerun preparation, rebuild for recovery, substitute a different bundle, change
the manifest digest, or overwrite/retarget existing objects. Existing mismatched
bytes fail closed and require owner investigation. The release workflow tree
must continue to match current community; the controller rechecks this condition.

A deliberate all-jobs rerun of the separate rehearsal preparation deleted its
original GitHub artifact, despite the attempt2 rebuild refusal. Its original
attempt1 success remains visible, but direct artifact lookup returns404.
The corresponding artifact-retrieval recovery gate failed. The untouched owner
preparation above remains available. Current publication cannot restore a lost
preparation artifact from the independently downloaded backup. Josh must choose
whether the documented preserve-original-preparation contract is sufficient, or
require a separately reviewed durable recovery extension before publication.
Draft #324 corrects this guidance without changing release bytes.

Final publication and actual live partial-publication recovery remain deliberately
unrun. No agent publication is authorized by this handoff. Template08 future
mode D and skipped external-service tests are unverified.
