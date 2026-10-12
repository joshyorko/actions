import json
from pathlib import Path

r=Path('/workspace/successor-evidence')
prior=(r/'pr308-diagnostic-body.md').read_text()
history=prior[prior.index('<details>'):]
body='''Queued async requests now register their cancellation state before dispatch and carry the same object into execution. A request cancelled while waiting for its worker reaches CANCELLED before acquiring an action process. Completed futures and failed submissions retire only their own state. Validation responses and existing scoped-run guards are preserved.

Current head: `f949bef2eeab518ffd34d9e69955938a007f8922`, tree `ce5a94a37f108438daa9d2d283ab575b1000ce99`, based on accepted integration `48eeaf171e695d9b8ac140ea53239eaeb6eff331`. This combines the independently accepted launcher fixture correction `d358f9c2` and cancellation admission fix. The fixture verifies the reported Python child's birth and original launcher lineage before cleanup, then requires child exit, original Popen reap and typed cleanup completion. It retains the prepared package interpreter and existing3-second startup/.2-second cleanup budget.

The frozen cancellation test's20-second sleeps and assertions are unchanged. On eeb Linux, both async requests returned before cancellation reported no runtime info; the second action began only after teardown killed the first worker. A genuine persisted-Run/held-executor control reproduced that missing-entry failure. The corrected source passes11 independent lifecycle controls, including existing RunPin/common-service tests;373 affected tests pass, one skips, three native tests are deselected, and configured static checks pass. Independent source/security review is GO. This head needs its own required CI.

The previous eeb RuntimeTests run remains FAILED: Windows source2FAIL/1413PASS/225SKIP from an unsupported child-PID/root-PID equality; Linux frozen1FAIL/131PASS/20SKIP from cancellation admission; macOS succeeds with1424 source passes and132 frozen passes. The previous0546 Windows job independently succeeds with1412 source passes and131 frozen passes, while its overall workflow remains failed on macOS. Historical0546 macOS cause stays UNKNOWN. All failed receipts and exact source identities are retained.

Retained changes also preserve provider/worker original readers, verified process births and opt-in ownership observation transport. Unwitnessed wait-birth matches and contradictory census PIDs are rejected; unmeasured reader/sampler/enforcer facts remain unavailable. Production RCC18.19.3 pin and permission expectations are unchanged.

PR remains draft and unmerged. Genuine admitted managed18.19.3 Action baseline attempts remain ZERO. Whole-operation640-second enforcement, full descendant/reader/lease cleanup, usable self-cgroup binding, accepted resource admission, current installed packages and exact-head platform gates remain HOLD. Optional18.19.5 then exact727 require baselinePASS first and remain unexecuted. Runtime1.0.3 and separate RCC18.19.6 publication remain HOLD. No release/tag/default/pin change or publication bypass occurred.

'''+history
(r/'pr308-f949-body.md').write_text(body)
(r/'pr308-f949-update.json').write_text(json.dumps({'title':'fix(runtime): preserve owned cleanup and queued cancellation','body':body},indent=2)+'\n')
