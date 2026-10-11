Canonical file proposed: docs/skills/repository-operations.md, after the implemented Canvas published-mode controls paragraph. Source14c remains frozen; the integration owner can apply this exact backed addition.

> A hash-checked import alone does not bind a helper's later subprocess execution.
> The Linux owned-process helper launches its own `__file__`; bind and verify the
> reviewed helper bytes for both module loading and that child invocation. Load
> from the verified byte buffer to avoid an unchecked second read or cached
> bytecode. Preserve a private, unchanged helper snapshot and check it before and
> after ownership calls. Record command, supervisor and outer gateway deadlines
> separately: the command budget excludes bounded supervisor cleanup. An observer
> cancellation request and its post-join sampler liveness are separate from Runtime
> cleanup admission. Require exactly one last-stage final observer report with
> `sampler_cancelled is True` and `sampler_alive is False`; offset snapshots may omit
> those fields. Missing, non-boolean, duplicate or stale final reports fail admission.
> An absent field never establishes cancellation or stopped sampler state.
>
> Keep the Runtime's measured wrapper, snapshot and descendant-reap flags and its
> reader/error/live/zombie observations intact. A later outer subreaper result does
> not turn a false Runtime cleanup predicate into a pass. The accepted browser
> owner returns a CompletedProcess without all per-browser cleanup fields; record
> its narrower contract and the outer supervisor's own result separately. A DEBUG
> browser launch path can establish the selected executable for that launch; it
> does not establish a live PID identity or natural shutdown.

Documentation improvement:
- Canonical file changed or proposed: proposed docs/skills/repository-operations.md; source14c guide already improved and remains unchanged here.
- Durable learning captured: bind self-launched helper bytes, distinguish finite budgets and sampler liveness, preserve per-kind measured cleanup flags and actual launch evidence scope.
- Evidence: exact frozen helper60acf... launches its __file__ and computes600+4*10+5=645; helper282edc7... returns CompletedProcess and checks only wrapper/live cleanup; observer943d... cancels and joins0.05s while separately reporting sampler_alive; frozen runner controls50PASS exercise actual helper self-launch and final predicate/primary-error admission; no actual consumer executed.
- Stale or ambiguous guidance removed: import hash pins subsequent executable reread;600s means whole gateway; cancellation means thread/process exit; outer reap can silently repair false Runtime admission; browser CompletedProcess or DEBUG PID proves full cleanup/live identity.
- Remaining uncertainty: exact actual native/public-Core gate, receipt/counters/raw launch evidence and real cleanup remain NOT_RUN. Read-only hash checks plus private mode0444 snapshot are operation-bound byte checks, not an atomic OS execution primitive or universal descendant adoption proof. Later302/integration source requires its own producer admission.

Upstream disposition: none. Preparation import-root failures were local harness configuration, not an established upstream defect.

The following independently proposed canonical patch is accepted and reused exactly for root integration, alongside the helper/self-launch/sampler delta above. Source14c remains unchanged.

--- a/docs/skills/repository-operations.md
+++ b/docs/skills/repository-operations.md
@@ -114,6 +114,24 @@
 case without skips or retries and the existing five persisted Runtime Run
 records. These are implemented admission controls; an actual native/public-Core
 bridge receipt still requires a separately reviewed immutable runner and run.
+
+An external pytest ownership hook must bind to the module object on the exact
+collected item, not just a qualified preimport of the same file. Pytest can
+collect that file under a different module name, leaving the live hook unset.
+Qualify the actual collection boundary with `--collect-only`: require the
+expected single node, source file and bytes before installing only the owned
+callback, and restore the previous hook in `finally`. Exercise public-mode
+admission and exact command/result forwarding on that collected object with a
+fake controller; collection controls do not execute Runtime or authenticate a
+product result.
+
+Preserve primary test output and the returned outer supervisor cleanup result
+before raising for a nonzero worker exit. If public-mode admission fails before
+Runtime startup, missing Runtime cleanup observations remain unavailable; a
+failed strict cleanup assertion does not identify a Runtime leak. Keep that
+failed attempt distinct from the next immutable runner proposal and require
+new review and execution authority. Do not relax product assertions or infer
+cleanup fields from a different process owner's result.
 
 Compare retained native producer inputs to the resolved ordinary merge tree,
 then repeat at the committed harness checkpoint. Divergent tips can omit later

Documentation evidence supplement: frozen v2 failedattempt989584 and independent failure reviewf519daf; collection-only diagnosis proves same file/different module; successor50 service-free controls exercise actual pytest plugin collection, public admission/CompletedProcess forwarding, binding poisons, and actual worker failure restoration. Stale ambiguity removed: qualified import pins actual collected module; missing Runtime owner implies native leak; nonzero child may discard returned outer cleanup. Actual v3 native/public consumer remains NOT_RUN; later302/fullCore/coldregistry/productartifact/OAuth scope remains open. Upstream disposition: none (external harness binding defect, not product defect).
