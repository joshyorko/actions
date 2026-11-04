# Bounded lifecycle counterexamples

These are deliberate guard mutations, not failures of the repaired Runtime.

## broken-recovery

```mermaid
---
title: "One Robot Run: durable launch, leases, and recovery"
---
stateDiagram-v2
  state "Legend" as legend {
    lg0: Breaks NoDuplicateExecution
    lg1: Path to the NoDuplicateExecution bug
  }
  class lg0 breaks
  class lg1 bugPath
  s0: Queued
  s1: Attempt leased
  s2: Launch committed or awaiting publication
  s3: Expired with retained launch
  s4: Recovery authorized#59; retained launch blocks progress
  s5: Replacement attempt fenced
  s6: Owned process running
  s7: Duplicate external execution
  [*] --> s0
  s0 --> s1: Claim Run
  s1 --> s2: Record Intent
  s2 --> s3: Expire Run
  s3 --> s4: Authorize Recovery
  s4 --> s5: Recover
  s5 --> s6: Spawn
  s6 --> s6: Record Intent
  s6 --> s7: Spawn
  classDef breaks fill:#ffecee,stroke:#e72e3b,stroke-width:2.5px,color:#cd2834
  class s0 bugPath
  class s1 bugPath
  class s2 bugPath
  class s3 bugPath
  class s4 bugPath
  class s5 bugPath
  class s6 bugPath
  class s7 breaks
  class s7 bugPath
```

## broken-publication

```mermaid
---
title: "One Robot Run: durable launch, leases, and recovery"
---
stateDiagram-v2
  state "Legend" as legend {
    lg0: Breaks NoStalePublication
    lg1: Path to the NoStalePublication bug
  }
  class lg0 breaks
  class lg1 bugPath
  s0: Queued
  s1: Attempt leased
  s2: Launch committed or awaiting publication
  s3: Expired with retained launch
  s4: Stale publication committed
  [*] --> s0
  s0 --> s0: Claim Item
  s0 --> s1: Claim Run
  s1 --> s2: Record Intent
  s2 --> s3: Expire Run
  s3 --> s3: Spawn or Finish Process
  s3 --> s4: Publish
  classDef breaks fill:#ffecee,stroke:#e72e3b,stroke-width:2.5px,color:#cd2834
  class s0 bugPath
  class s1 bugPath
  class s2 bugPath
  class s3 bugPath
  class s4 breaks
  class s4 bugPath
```

## broken-cancel

```mermaid
---
title: "One Robot Run: durable launch, leases, and recovery"
---
stateDiagram-v2
  state "Legend" as legend {
    lg0: Breaks CancellationRequiresStop
    lg1: Path to the CancellationRequiresStop bug
  }
  class lg0 breaks
  class lg1 bugPath
  s0: Queued
  s1: Attempt leased
  s2: Launch committed or awaiting publication
  s3: Waiting for stopped-launch confirmation
  s4: Cancellation reported without stopped proof
  [*] --> s0
  s0 --> s1: Claim Run
  s1 --> s2: Record Intent
  s2 --> s3: Request Cancel
  s3 --> s4: Confirm Cancel
  classDef breaks fill:#ffecee,stroke:#e72e3b,stroke-width:2.5px,color:#cd2834
  class s0 bugPath
  class s1 bugPath
  class s2 bugPath
  class s3 bugPath
  class s4 breaks
  class s4 bugPath
```

## Retained-launch progression remains unsupported

This is a current missing progression, not a deliberate mutation. Safe refusal does not settle the Run.

```mermaid
---
title: "One Robot Run: durable launch, leases, and recovery"
---
stateDiagram-v2
  state "Legend" as legend {
    lg0: Path to the AuthorizedRecoveryProgress bug
    lg1: Repeats forever, so AuthorizedRecoveryProgress breaks
  }
  class lg0 bugPath
  class lg1 repeats
  s0: Queued
  s1: Attempt leased
  s2: Expired before launch
  s3: Launch committed or awaiting publication
  s4: Pre-launch recovery authorized
  s5: Expired with retained launch
  s6: Owned process running
  s7: Recovery authorized#59; retained launch blocks progress
  s8: Replacement attempt fenced
  s9: Result published
  [*] --> s0
  s0 --> s1: Claim Run
  s1 --> s2: Expire Run
  s1 --> s3: Record Intent
  s2 --> s4: Authorize Recovery
  s3 --> s5: Expire Run
  s3 --> s6: Spawn
  s4 --> s8: Recover
  s5 --> s7: Authorize Recovery
  s6 --> s5: Expire Run
  s6 --> s3: Finish Process or Unobserved Exit
  s7 --> s7: Crash Host
  s3 --> s9: Publish
  s8 --> s2: Expire Run
  s8 --> s3: Record Intent
  class s0 bugPath
  class s1 bugPath
  class s3 bugPath
  class s5 bugPath
  class s7 bugPath
  class s7 repeats
```
