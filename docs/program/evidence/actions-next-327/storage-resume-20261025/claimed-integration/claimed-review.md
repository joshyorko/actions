# Independent claimed Robot integration review

Read-only comparison to committed e6e8f0130e6a7cfba2142e1382cbdd1f07901d39. Inspected root authority/receipt/binding changes plus isolated runner and new test source. No source edits, tests, database, RCC execution, installs or external mutations performed by reviewer. Delivery's37passed/37PostgreSQL deselected are producer-reported, not independently executed.

Reviewed source SHA256:
- robot_work_item_authority.py ab2847fc2a9f1b5442e91d02b36214b4352d47ac9b87ff9c78053507ab57f57f
- robot_receipts.py a4daef5becbcd1035630fc611488d0a024aac5c0237d6913a5ea04612702b287
- generic_work_item_execution.py 72092080ab0097ba8d23a4babd94132a8c166855061a4f630a7470522d24c313
- robot_runtime_runner.py 6ebd7a4cee862bb808aad9684dd9070db4431dc38c605b473338a64baf7b524d

## Finding disposition

No confirmed blocking authorization or atomic-publication defect found in inspected changes. This is source-review acceptance only, not installed/concurrent/PostgreSQL qualification.

Authority issuance checks exact canonical owner type, shared DB/registry/deployment identity and no active transaction (robot_work_item_authority.py:38–47). Package-row pin is captured before artifact reads and rechecked after them (:50–82). Issued object is tied to exact owner, caller, ticket and snapshot (:23–34). Generic binding rejects unissued/nested/mixed binding and clears in finally (generic_work_item_execution.py:630–651); current checks reuse verified declaration but re-authorize stored deployment/package policy (:86–120,206–225). Final prepared Robot selection supplies its independent source/provider pins; this binding does not replace them.

Claim and Attempt epoch are intentionally independent. Receipt requires canonical claim identity/owner and bounded claim epoch, not equality to Attempt epoch (robot_receipts.py:113–123). Claimed journal/terminal checks bind queue item, immutable policy, input digest, snapshot and idempotency key (:229–250). Running receipts require IN_PROGRESS owner/deadline/no cancellation (:255–262). Terminal receipts instead require matching final item state and cleared owner (:251–254), which correctly avoids requiring an expired live lease for retained terminal metadata.

Publication uses the generic transaction lock for claimed execution, repeats current claim authority, requires COMPLETE, and publishes Run/Attempt/sealed outputs before finishing the exact queue claim within the same transaction (robot_runtime_runner.py:108–118,214–235). A finish exception unwinds the enclosing transaction. Heartbeat composes generic claim renewal and Attempt renewal (:87–92; generic_work_item_execution.py:709–716). Pure final host-stop check is retained at:212–213. No new queue, admission or automatic retry is introduced.

Optional no-claim is allowed only by immutable optional declaration (runner:331–343; receipts:221–228). Receipt mode remains standalone for no claim, but retained declaration validation prevents this from bypassing required-input/consumer. No extra queue item is synthesized. Producer and allow_outputs are rejected explicitly.

## Acceptance blockers and exact next tests

1. **Concurrent lease/claim race remains unproven.** New test_robot_claimed_work_items_327.py:270–310 mutates epoch/deadline sequentially after synthetic adapter completion or monkeypatches finish. It proves rollback/late checks, not concurrent PostgreSQL lock ordering. Run two independent connections/processes: pause publisher between initial _check and queue.finish_fenced, race claim cancel/steal/expiry and COMPLETE revocation, release barrier; assert one authorized terminal outcome or full rollback, no mixed final Run/provisional queue state, and no deadlock. Also force Attempt renewal failure after queue renewal and verify both lease changes roll back. PostgreSQL parameters being deselected is an explicit missing gate, not a source-review blocker.

2. **Actual failed Robot/RCC semantics remain unproven by these FAIL cases.** New test:245–247 returns replace(result,status='FAIL',return_code=1) after SyntheticAdapter succeeded. This checks metadata publication, not real failing Robot XML/process cleanup. Installed RCC must execute an actual failing owned task, retain actual FAIL XML/stdout/stderr/RCC receipt, and prove claim state FAILED with same receipt/run identity. Do not call these synthetic FAIL tests installed failure-lifecycle proof.

3. **Retained terminal corruption/read gate should be explicit.** Terminal SQL checks were extended for claimed queue linkage, but new success assertions:251–266 inspect persisted fields directly. Add reopen/authorized retained-read assertions and mutate item epoch, queue/payload, terminal state or claim_owner independently to prove receipt rejection, plus allowed expiry of read metadata versus output authorization. Existing baseline receipt tests may cover standalone shapes; claimed terminal extension needs its own evidence. No actual bypass demonstrated.

4. **Authorization race versus artifact reads.** The design rechecks package pin and final SQL authority, and tests source mutation/nested binding. Add a barrier between authority preparation and binding/final publish with package row/Deployment activation replacement and ensure rejection before adapter/publication. This complements static pin reasoning rather than indicating a known defect.

Recommendation: integrate only under explicit pending installed/claim-concurrency gates. Preserve original failed installed candidate history. Delivery accurately states no real RCC/PostgreSQL proof and producer/child-output unsupported scope.

Documentation improvement:
- Canonical file proposed: docs/skills/work-items.md.
- Exact addition: “Claimed Robot tests that rewrite a synthetic adapter result to FAIL verify receipt publication only; real RCC failure/cleanup must be qualified separately. Sequential epoch mutation and injected finish exceptions establish fencing and rollback contracts but do not qualify concurrent PostgreSQL claim/Attempt renewal or publication races. Terminal claimed receipt tests must reopen retained state and validate exact queue/input/epoch linkage after lease expiry, without borrowing output-read authority.”
- Evidence: test_robot_claimed_work_items_327.py:245–247,270–310; robot_receipts.py:229–262; producer receipt37PostgreSQL parameters deselected.
- Stale ambiguity removed: source-level atomicity and synthetic FAIL receipts are not installed/concurrent acceptance.
- Remaining uncertainty: gates above; reviewer intentionally ran no processes or DB workload.

Upstream disposition: none. Local review only; draft-only, no external issue target or report.
