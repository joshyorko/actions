# Installed harness read-only review

No imports, process launches, RCC, PostgreSQL, or source edits performed. AST parsing succeeded for all four files; reviewed fingerprints are adjacent. Harness helpers may continue editing, so this receipt applies only to these bytes.

## Preparation
No new blocking defect found in the a44-to-a46 preparation delta. Required measured source and Runtime wheel SHA, pinned Core a7 bytes, installed Runtime payload comparison, bundled RCC digest, Robot 7.4.2 origin/version, exact Core payload proof, fresh target-local trust and --no-build proof are coherent. Initial free-space check is 12.5 GiB; sampled limits reserve 10 GiB and cap the lane at 2.5 GiB. This is static approval of the change, not evidence of a successful preparation run. Existing cleanup/sanitization mechanics were retained; no new general-purpose safety guarantee is implied.

## Fix before installed harness launch
1. Both qualify.py scripts run authorize-local via subprocess.check_output with no timeout; Knowledge providers-local also has no timeout. A stalled CLI can hold the lane indefinitely. Add explicit bounded timeouts or prove the chosen outer supervisor bounds and cleans these children.
2. Both stop() functions signal only the server PID despite start_new_session=True. On graceful failure/timeout they do not enumerate, kill, or reap surviving RCC/process descendants, and do not assert descendant absence. Run under the established task-owned subreaper supervisor with bounded descendant cleanup (or implement equivalent ownership-checked cleanup in the harness). Do not treat parent PID exit as execution cleanup proof.
3. Knowledge initializes actual_generated_execution to NOT_PROVEN and never updates it, even after status PASS. Set a measured value only after the real RCC receipt/result and restart assertions pass, or remove the misleading field.

## Accepted scope and limitations
Candidate Runtime origin and wheel payload verification are explicit. Knowledge additionally checks exact Core a7 and compiler proof hash; Robot checks prepared artifact/package digest. Local authorization uses public offline CLI, exact deployment grants, a random loopback-only key, and SQL reads rather than SQL authorization writes. Claimed Robot tests assert actual XML status, real RCC exit, complete artifact hashes, claim terminal state, and restart equality. Knowledge asserts ingest/search values, matching RCC artifact/exit, failure, and retained artifact equality after restart. These harnesses do not qualify independent browser hosts, multi-principal isolation, or MCP Tasks: tasks discovery is explicitly expected false. Robot docstring mentioning Task acceptance should be narrowed.

## Exact canonical documentation proposal
Append to the installed qualification guidance: “Run installed qualification under an owned bounded supervisor. Server PID exit is not descendant cleanup evidence: preserve subreaper ownership, bound each offline CLI call, and verify no owned execution descendants remain after failure. Report actual execution only after validating the RCC receipt and domain result; restart readback alone does not establish execution. Label disabled Tasks and untested browser/multi-principal gates explicitly.”

Documentation-improvement receipt: exact delta proposed to root; shared canonical files were not modified. Evidence: reviewed stop/authorize/provider_request functions and Knowledge receipt initialization; source fingerprints and AST results recorded. Upstream disposition: none; these are local harness concerns, no confirmed upstream defect and no external mutation.
