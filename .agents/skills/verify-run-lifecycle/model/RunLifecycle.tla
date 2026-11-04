---------------------------- MODULE RunLifecycle ----------------------------
EXTENDS Naturals, FiniteSets, TLC
CONSTANTS Claimed, Fault, AllowCancel, MaxEpoch, StableClaim
VARIABLE s
vars == <<s>>
Workers == {1, 2}
Epochs == 1..MaxEpoch
Terminal == {"passed", "failed", "cancelled"}
Init == s = [status |-> "queued", epoch |-> 0, owner |-> 0,
  runLive |-> FALSE, claimEpoch |-> 0, claimOwner |-> 0, claimLive |-> FALSE,
  queue |-> "pending", cancel |-> FALSE, launch |-> 0, intents |-> {},
  spawned |-> {}, running |-> {}, reaped |-> {}, results |-> {}, recovery |-> 0,
  ticketOwner |-> [e \in 0..MaxEpoch |-> 0],
  ticketClaim |-> [e \in 0..MaxEpoch |-> 0],
  frame |-> [e \in 0..MaxEpoch |-> FALSE], badWrite |-> FALSE]
LiveRun(t) == t > 0 /\ t = s.epoch /\ s.ticketOwner[t] = s.owner /\ s.runLive
LiveClaim(t) == ~Claimed \/ (s.claimLive /\ s.queue = "claimed"
  /\ s.ticketClaim[t] = s.claimEpoch /\ s.ticketOwner[t] = s.claimOwner)
Fence(t) == LiveRun(t) /\ LiveClaim(t) /\ ~s.cancel /\ s.status = "running"

\* SQL queue reserve/lease takeover; its epoch is independent of RunAttempt.
ClaimItem(w) == Claimed /\ ~s.claimLive /\ s.claimEpoch < MaxEpoch
  /\ s.queue \in {"pending", "claimed"} /\ s.status \notin Terminal
  /\ s' = [s EXCEPT !.claimEpoch = @ + 1, !.claimOwner = w,
      !.claimLive = TRUE, !.queue = "claimed"]
\* Admission + first Attempt claim. IDs and immutable selection are fixed.
ClaimRun(w) == s.epoch = 0 /\ s.status = "queued" /\ ~s.cancel
  /\ (~Claimed \/ (s.claimLive /\ s.claimOwner = w))
  /\ s' = [s EXCEPT !.epoch = 1, !.owner = w, !.runLive = TRUE,
      !.status = "running", !.ticketOwner[1] = w,
      !.ticketClaim[1] = s.claimEpoch, !.frame[1] = TRUE]
ExpireRun == s.status = "running" /\ s.runLive
  /\ s' = [s EXCEPT !.runLive = FALSE]
ExpireClaim == Claimed /\ s.queue = "claimed" /\ s.claimLive
  /\ ~(StableClaim /\ s.recovery > 0)
  /\ s' = [s EXCEPT !.claimLive = FALSE]
CrashHost == s.epoch > 0 /\ s.frame[s.epoch]
  /\ s' = [s EXCEPT !.frame[s.epoch] = FALSE]
\* Control-plane authorization records an opaque operator no-effect receipt.
AuthorizeRecovery == s.status = "running" /\ ~s.runLive
  /\ s.epoch < MaxEpoch /\ s.recovery # s.epoch /\ ~s.cancel
  /\ (~StableClaim \/ (s.claimLive /\ s.claimOwner # s.owner))
  /\ s' = [s EXCEPT !.recovery = s.epoch]
\* DetachedActions.claim allows verified PRE-LAUNCH replacement only.
\* Claimed GenericWorkItemExecution._dispatch returns the old ticket instead.
Recover(w) == ~Claimed /\ s.status = "running" /\ ~s.runLive /\ ~s.cancel
  /\ s.epoch > 0 /\ s.epoch < MaxEpoch /\ s.recovery = s.epoch
  /\ (s.launch = 0 \/ Fault = "recovery")
  /\ LET e == s.epoch + 1 IN
      s' = [s EXCEPT !.epoch = e, !.owner = w, !.runLive = TRUE,
        !.recovery = 0, !.launch = 0, !.ticketOwner[e] = w,
        !.ticketClaim[e] = s.claimEpoch, !.frame[e] = TRUE]
\* record_launch_intent owns a durable transaction; OS spawn is NOT atomic with it.
RecordIntent(t) == Fence(t) /\ s.frame[t] /\ s.launch = 0
  /\ s' = [s EXCEPT !.launch = t, !.intents = @ \cup {t}]
\* A permit may race expiry/cancel after its final live check. Conservatively
\* allow that spawn; the retained intent still forbids a replacement attempt.
Spawn(t) == t \in s.intents /\ t \notin s.spawned /\ t \notin s.reaped /\ s.frame[t]
  /\ s' = [s EXCEPT !.spawned = @ \cup {t}, !.running = @ \cup {t}]
FinishProcess(t) == t \in s.running /\ s.frame[t]
  /\ s' = [s EXCEPT !.running = @ \ {t}, !.reaped = @ \cup {t},
      !.results = @ \cup {t}]
\* A process can disappear after its host dies, without delivering a receipt.
UnobservedExit(t) == t \in s.running
  /\ s' = [s EXCEPT !.running = @ \ {t}]
\* Combined Run/output publication + Work Item finish is ONE SQL transaction.
Publish(t, terminal) == s.status = "running" /\ t \in s.results /\ s.frame[t]
  /\ (Fence(t) \/ Fault = "publish")
  /\ s' = [s EXCEPT !.status = terminal, !.badWrite = ~Fence(t),
      !.queue = IF Claimed THEN "done" ELSE s.queue,
      !.claimLive = IF Claimed THEN FALSE ELSE s.claimLive]
RequestCancel == AllowCancel /\ s.status \in {"queued", "running"} /\ ~s.cancel
  /\ s' = [s EXCEPT !.cancel = TRUE,
      !.status = IF s.epoch = 0 THEN "cancelled" ELSE s.status,
      !.queue = IF Claimed THEN "cancelled" ELSE s.queue,
      !.claimLive = IF Claimed THEN FALSE ELSE s.claimLive]
\* Only the original frame owns the process; an expired frame can stop its OWN
\* process, but cannot use a different ticket/epoch to stop another execution.
StopOwned(t) == t \in s.running /\ s.frame[t] /\ (s.cancel \/ ~Fence(t))
  /\ s' = [s EXCEPT !.running = @ \ {t}, !.reaped = @ \cup {t}]
ObserveStopped(t) == s.cancel /\ s.frame[t] /\ s.launch = t
  /\ t \notin s.running /\ t \notin s.reaped
  /\ s' = [s EXCEPT !.reaped = @ \cup {t}]
\* Cancellation does not need a live lease, but needs original identity and
\* exact stopped/reaped launch evidence. A restart cannot recreate that frame.
ConfirmCancel(t) == s.status = "running" /\ s.cancel /\ t = s.epoch
  /\ s.frame[t] /\ s.launch = t /\ s.ticketOwner[t] = s.owner
  /\ (~Claimed \/ s.ticketClaim[t] = s.claimEpoch)
  /\ ((t \in s.reaped /\ t \notin s.running) \/ Fault = "cancel")
  /\ s' = [s EXCEPT !.status = "cancelled"]
Done == UNCHANGED vars
Next == (\E w \in Workers: ClaimItem(w) \/ ClaimRun(w) \/ Recover(w))
  \/ ExpireRun \/ ExpireClaim \/ CrashHost \/ AuthorizeRecovery \/ RequestCancel
  \/ (\E t \in Epochs: RecordIntent(t) \/ Spawn(t) \/ FinishProcess(t)
      \/ UnobservedExit(t) \/ StopOwned(t) \/ ObserveStopped(t) \/ ConfirmCancel(t)
      \/ (\E terminal \in {"passed", "failed"}: Publish(t, terminal))) \/ Done
Spec == Init /\ [][Next]_vars
  /\ (\A w \in Workers: WF_vars(Recover(w)))
NoDuplicateExecution == Cardinality(s.spawned) <= 1
NoStalePublication == ~s.badWrite
CancellationRequiresStop == s.status # "cancelled" \/ s.epoch = 0
  \/ (s.epoch \in s.reaped /\ s.epoch \notin s.running)
PrelaunchRecoveryProgress == \A e \in 1..(MaxEpoch - 1):
  (s.recovery = e /\ s.launch = 0 /\ ~s.cancel) ~>
  (s.epoch > e \/ s.status \in Terminal)
AuthorizedRecoveryProgress == \A e \in 1..(MaxEpoch - 1):
  (s.recovery = e /\ ~s.cancel) ~> (s.epoch > e \/ s.status \in Terminal)
=============================================================================
