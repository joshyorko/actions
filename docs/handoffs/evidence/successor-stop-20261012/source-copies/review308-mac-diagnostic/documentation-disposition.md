Canonical file: docs/skills/repository-operations.md
Read-only review proposed this precise replacement to the b30 deadline paragraph:

If the absolute cleanup deadline has expired, the current helper skips a new kill.
If its final zero-budget wait still fails, it records an unreaped wrapper.

Disposition: implemented by the integration writer in immutable eeb806e7. The exact Git delta follows.

diff --git a/docs/skills/repository-operations.md b/docs/skills/repository-operations.md
index 74521935..a72f2066 100644
--- a/docs/skills/repository-operations.md
+++ b/docs/skills/repository-operations.md
@@ -2690,8 +2690,8 @@ emergency test teardown, and report those facts on failure. Always kill, wait,
 and close that original child's pipes in `finally`; successful teardown cannot
 retroactively qualify a failed cleanup. A cooperative `Popen.wait` may resume
 after its requested timeout because of scheduler delay. If the absolute cleanup
-deadline has expired, the current helper skips a new kill and records an unreaped
-wrapper. Use injected clock controls to distinguish that outcome from failed
+deadline has expired, the current helper skips a new kill. If its final
+zero-budget wait still fails, it records an unreaped wrapper. Use injected clock controls to distinguish that outcome from failed
 ownership capture; a live-child assertion without its typed result cannot
 identify which path failed.
 

Durable learning: expiration forbids new cleanup escalation; the subsequent wait result is a separate observed fact and can succeed without a new signal.
Evidence: unchanged common/process.py final zero-budget Popen.wait branch, timed and overshoot controls; eeb changes only canonical guidance and retains all b30 source/test bytes.
Stale guidance removed: unconditional “records an unreaped wrapper” after expiration; record that fact only when final wait fails.
Remaining uncertainty: actual historical macOS cause unknown and fresh exact-head CI pending. Controlled overshoot is a demonstrated possible route, not proof of the historical cause or a production repair. Native/provider/lease/controller admission remains unqualified.
Upstream disposition: none.
