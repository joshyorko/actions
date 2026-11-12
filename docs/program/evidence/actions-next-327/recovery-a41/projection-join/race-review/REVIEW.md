# Independent generated projection review

Reviewed immutable backend patch SHA256 `413ca4d446e5d683ba03fe58158cbf79f09d0e6e319b69a4fb40fc8f7fd83c8d`, frontend patch `09a1124962f54c4d444c8b21e88c51872da2949b934c466dbf4f43edd6858f4b`, and proposed routing `556469a99b2abe918045e9b3cb9a871ae153bcb873c4469df51729842fe99456` in `/workspace/generic-projection-evidence/delivery`. Read current root routing/service dependencies without editing root.

## Blocker: complete generated receipt can change during result read

`generic_projection.project_generated_result.current()` validates version, current publication fence, selected output receipt and descriptor. Its before/after comparison returns only `(ref,digest,size)`. It does not compare the complete initially validated generated execution receipt or Run inputs/action metadata. The route validates the full receipt in `_read`/`service.ticket` before artifact IO; the callback only rechecks deployment, binding, app association and read grants. Changing another receipt field while the provider stream is read therefore survives the final check.

Reproducer `test_projection_race.py`, `race.log`, `race.xml`: SQLite 1 failed, 1 deselected. The fixture's receipt starts with sourceArtifactDigest=sha256:a*64; provider context close changes it to sha256:b*64. Expected AccessDenied/ValueError does not occur. This is component proof under the repository's mutable-SQL integrity test model, not proof of arbitrary external SQL access. No installed claim.

Required correction: pin the exact initially validated Run result/inputs and relevant RunPin/Attempt/intent/output preimages, then SQL-only recheck after IO; alternatively use the existing prebound retained-record validation with complete metadata pins. Ensure the pin is captured at the full route validation boundary, not after an intervening mutable gap. Add post-read mutation tests. Parent and implementing helper have the reproducer. Fix is pending independent re-review.

## Reviewed without another identified blocker

- Result selection is by exact `generated-action-result.json`, never first output or `actionResult` metadata. Current Run/Attempt, admission principal, exact snapshot, terminal success, output ownership/state/media/size and selected digest/receipt are checked; resolve enforces retained object TTL and provider identity.
- Routing proposal callback uses SQL repository.current, app association request/audit checks and artifact permission checks. It does not call `_selected`, `_read`, schema_for or provider APIs. This is source inspection, not a route-level provider trap test.
- APP_TOOLS addition excludes model audience; reply positional compatibility and read-only tool marking are parent-owned fixes already acknowledged. Complete broker/session and wrong-binding route regressions remain required.
- Frontend re-encodes canonical JSON and compares server data; UTF-8 65536 bound, NFC/scalar/finite/safe integer checks, UTF-16 object ordering and shared representative vectors match the restricted existing canonical boundary. Existing V1 serializer is untouched.
- Controller clears data on begin/fail, binds run/attempt, freezes derived data and ignores older pending results. Root adapter integration still must drive begin/fail on every submission/error/authorization denial and load only after trusted success; component controller tests do not prove this.

Evidence caution: backend receipt reports tests3 four failures retained outside delivery. Preserve those original logs/XML when publishing the checkpoint. Do not convert the 48 component tests or 25 frontend tests into installed-host acceptance.

## Exact canonical guide proposal

Target: docs/skills/repository-operations.md, generated result projection guidance.

A generated projection is a bounded read of the exact sealed generated result, not a dispatch envelope or UI execution metadata. Validate the complete retained execution before provider IO and pin its SQL preimages for the post-read check; comparing only output ID, size and digest misses changes to other execution identities during that read. Current Deployment/app/binding association and live read/artifact grants must be rechecked with SQL-only callbacks. Keep the generated data canonical bytes separate from current Run/Attempt frontend state, and invalidate stale data on resubmit, error or authorization denial. Source/component checks do not qualify installed app routing or rendered result consumption.

Verified basis: the retained failing SQLite race reproducer plus source inspection of backend, controller and routing. Correction/retest remains pending; this proposal states the required invariant, not a passed fix.

Upstream disposition: none. No external mutation or root edits.
