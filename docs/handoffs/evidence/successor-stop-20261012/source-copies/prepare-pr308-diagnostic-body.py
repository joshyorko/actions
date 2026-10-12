import json
from pathlib import Path

root=Path('/workspace/successor-evidence')
prior=(root/'pr308-before-diagnostic-body.md').read_text()
history=prior[prior.index('<details>'):]
body='''Provider and worker cleanup now retain their original readers, verify process birth identities before signal authority, and report typed ownership evidence. Opt-in Linux supervisor metadata preserves raw wait observations, uncapped captured identity census and unavailable facts; it rejects unsupported birth matches and contradictory PID bindings without replacing the primary outcome. Production RCC remains pinned to18.19.3.

Current head: `eeb806e7699d7f8e6878d5cc1dd83cd22e795ff5`, tree `ce7ae02d6c7db06ceffedf771c6eb365d11517b9`, based on accepted integration `48eeaf171e695d9b8ac140ea53239eaeb6eff331`. The latest diagnostic slice preserves the same3-second startup/.2-second cleanup budget and strict stopped/complete assertions. It captures typed startup cleanup facts and reaps/closes only its original child in emergency test teardown. The production helper and common process implementation are unchanged from0546. Independent controls reproduce the old teardown defect, then pass four diagnostic/deadline controls; affected source tests329PASS/1SKIP/3nativeDESELECT and configured static checks pass. The final additive documentation correction changes no tested source bytes.

Retained fe1 Windows source CI was cancelled once after a bounded reproduction proved its fake waitpid backend omitted WNOHANG and entered a constant-clock fallback. Corrective0546 changes test models only. Its observed CI has22 successful checks, one macOS failure and Windows integration still running. macOS source units report1420PASS/216SKIP/1FAIL in the provider-stopped assertion. Historical typed facts were unavailable, so actual cause remains UNKNOWN. Controlled scheduler overshoot demonstrates a possible route, not the actual macOS cause. This new head requires its own CI; no identical failing CI was replayed.

The independently verified fe1 sdist/six-wheel package set and fresh public Core1.0.2/Helper1.0.3 consumer pass complete Runtime Python membership/provenance, nine installed OAuth controls, dependency checks, template creation and idle HTTP200/403/200. This scope does not qualify later whole source heads or installed native/MCP/platform/lease behavior.

PR remains draft and unmerged. Genuine managed18.19.3 Action baseline attempts remain ZERO. Complete controller/deadline/reader/descendant/lease admission, usable self-cgroup binding, accepted resources, exact-head CI and native platforms remain HOLD. The eeb-v9 native profile is SOURCE-PREPARED-NOTRUN. Optional18.19.5 then exact727 are unexecuted and require baselinePASS first. Runtime1.0.3 and separate RCC18.19.6 publication remain HOLD. No pin/tag/release change, timeout increase, broad permission relaxation, bypass or publication occurred.

'''+history
(root/'pr308-diagnostic-body.md').write_text(body)
(root/'pr308-diagnostic-update.json').write_text(json.dumps({'body':body},indent=2)+'\n')
