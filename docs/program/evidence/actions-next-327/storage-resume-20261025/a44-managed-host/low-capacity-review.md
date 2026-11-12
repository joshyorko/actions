# Independent low-capacity profile review

Static review CLEARED for bounded target trial. No script import, server, credential, RCC execution, materialization, or browser operation was performed by this reviewer.

Exact reviewed source:
- compiler/prepare-compiler-managed.py SHA256 6b97c262bc6e807b72959f732586a2aa337d504108900921813310ab60b3e3af
- managed-qualify-low-capacity.py SHA256 e393bdd7ebf65248522a114052d2677e1b975b7444f8bfea35bcfb5d431f6253

Compared both with retained strict variants. Compiler changes require 4.25 GiB initial free space, retain 2 GiB allocated cap and require 1 GiB free reserve; PATH includes standard /usr/sbin and /sbin. The independently observed parent receipt at a44-compiler-capacity-fixed/capacity.json reports three successful phases with no cleanup errors and sampled peak 1,935,241,216 bytes. This is below 2 GiB by 212,242,432 bytes. Parent runtime-capacity.json reports actual installed direct protocol/RCC measurement PASS, sampled peak 2,953,277,440 bytes, explicitly browser not run. The proposed combined compiler/fixture cap is 3 GiB, leaving 267,948,032 bytes of sampled margin. These are sampled observations in the producer environment, not proof of a native peak or GUI acceptance.

The UI-only variant explicitly records independent_generated_execution=NOT_RUN_IN_THIS_UI_ONLY_VARIANT. Three operator-reported UI Runs are correlated to backend IDs, two completed/four-output states and one failed/three-output state, authorized failure artifacts and exact compiler artifact identity. Authentication/Host/Origin denials, stale-session rejection, restart, rollback and revoked-read checks remain. Completion requires six bounded PNG files and parent visual review. Successful status remains BACKEND_PASS_UI_REVIEW_PENDING; strict Playwright/sandbox/actual ChatGPT are not claimed.

Allocation counts inode-deduplicated file blocks across the prepared compiler root and fixture on one filesystem. Fixture logical size remains under 256 MiB and log bound under 12 MiB; free reserve is 1 GiB. Installed consumer/host already present before preparation are outside the combined lane-allocation sum but consume filesystem free space. Compiler needs 4,563,402,752 actual free bytes, so a rounded decimal GB display is insufficient authorization to proceed past its actual-byte guard.

AST-only mock proof: low-capacity-mockchecks.py extracted only main finally and watch_capacity. Nine cleanup cases passed (success plus host stop/log close/Runtime stop/key read/key disposal/budget/receipt/signal-handler failures). Later cleanup phases were attempted, retained receipts excluded synthetic sensitive error messages and failures did not report success. Two watchdog cases passed: budget failure records exception type and cancels owner; cancelling the watcher propagates without cancelling owner. All process/filesystem/key operations were inert mocks. Results: low-capacity-mockchecks.json. Both complete scripts parse successfully.

Limitations: .25 seconds is a nominal async sleep, not a guaranteed sampling interval. Synchronous readiness, authorization subprocesses and shutdown block that event loop; sampled caps are not quotas. The fixed source retains bounded startup and shutdown paths, and a watcher abort reaches existing independent cleanup. No additional independent-client executions are silently counted as passing in this variant. This review does not prove native startup/network/capacity or screenshots.

Next exact gate: target executes the separate low-capacity preparation, then UI-only qualifier after checking actual free bytes. Retain its capacity/cleanup receipts and six captures; parent visually reviews before upgrading the GUI status.

Documentation improvement: “A low-capacity qualification profile must be named and preserve the strict recipe. Record exact-byte initial/free-reserve guards, measured allocation scope, sample limitations, and omitted gates explicitly. A successful reduced profile cannot inherit unexecuted independent-client or GUI proof; link separate receipts and retain parent visual review.”

Upstream disposition: none. Owned qualification tooling, no confirmed upstream defect or external reporting target.
