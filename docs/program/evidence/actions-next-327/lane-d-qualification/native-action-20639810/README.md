# Frozen Linux synthetic Action, authenticated persistence and restart

PASS on retained native executable built from integrated source
20639810107cbe4b28e7f1acc5e2ac68bdde06b6, Runtime1.1.0a40.
Executable SHA256 remains
d5c2ce56a6bde29ea08a48a9c8345bff8596ac2efe652c96c594405112b428a8.
This is direct frozen Linux execution, not installed-wheel, browser/ChatGPT or
native Windows/macOS acceptance. No production edits/shared tests changed.

Reuses managed package manifest contract from existing
`test_cli_successful_generation_drain.py::_write_generation`: RCC Python3.12,
uv0.9.26, published owned actions-core1.0.2. This exercises that explicit existing
fixture version, not current Core1.1.0a3 candidate semantics. `probe_action.py`
returns synthetic doubled input plus actual worker Python/Core origin/version.

Actual native authenticated legacy Action endpoint:
POST /api/actions/native-qualified/durable-probe/run with {"value":21} returned42.
GET /api/runs/{run_id} with local synthetic key returned persisted PASSED result;
without authorization returned403. Stopped the process, launched a distinct native
PID on a different loopback port with the same datadir and actions-sync=false,
then read identical status/result through the authenticated API. No SQL mutation,
manual grant injection or auth bypass. This legacy action API uses its configured
API-key contract; it does not qualify generated Canvas scoped Deployment grants,
Work Item dispatch or modern output-provider authorization. No genuine synthetic
grant permission blocker arose for this existing legacy API seam.

Final Run: run-000-fbb78d5d-578b-49f0-804e-ebd549f5bc7e.
Initial/restarted native PIDs24704/24951. Worker Python3.12.15, Core1.0.2 from the
fresh task-owned actions-home/holotree path recorded in receipt. Genuine RCC
bootstrap/action execution, no simulated worker. Renderer/resource smoke remains
in the prior native-linux evidence; browser rendering still NOT_RUN.

## Reproduction and resource scope

Retained run.py and package inputs are the exact harness. Run from the prepared
native checkout action_server using package-local Poetry:
`poetry run python /workspace/lane-d/native-action-isolated-20639810/run.py`.
For a fresh qualification copy harness/package to a new owned directory first.
Use the pinned RCC18.19.3 toolchain and task-local Poetry/XDG caches as documented
in ../native-linux-20639810/README.md. Harness strips Python selector variables,
sets ACTIONS_HOME/ROBOTS_HOME, uses loopback only, synthetic key and fresh datadir;
startup deadline180s, request deadline90s, termination deadline15s. Stops owned
process groups. stdout preserved; no optional huge tracing enabled. Initial free
space21GiB; fresh RCC env consumed about1.8GiB.

First run passed functional checks but revealed default ~/.actions worker cache:
ROBOCORP_HOME alone is overridden by Runtime's action RCC adapter. Its receipt is
retained as initial-default-cache-receipt.json, not fresh-cache qualification.
Final rerun uses supported ACTIONS_HOME and proves imported Core under that owned
root. No existing user environments or data were deleted or modified by cleanup.

## Dependency ownership regression

Dedicated consumer qualifier now refuses replaced sema4ai-http-helper and
sema4ai-common distribution names, normalized under Python package-name rules,
and any Requires-Dist declaration naming them even behind an inactive extra.
This prevents a lock-valid or optional vendor dependency from silently returning
to the inspected installed release artifact closure. Four negative cases cover
both names as installed packages and inactive root declarations. It does not scan
all possible uninstalled artifacts or prove extension VSIX closure.

322 devutils tests passed; required full stdout/XML retained. Existing SBOM
strict-graph and declared-graph controls remain passing. No version/lock/release
hook changed. Rollback this commit removes the dedicated guard/test and evidence;
no database migration. Upstream disposition: none; this is owned qualification.

Exact canonical-guide delta proposed: “For native Action qualification, set
ACTIONS_HOME as well as ROBOTS_HOME: the Runtime Action RCC adapter derives its
ROBOCORP_HOME from ACTIONS_HOME. Verify returned worker import origin, authenticate
both execution and durable reads, require a negative unauthenticated read, and
restart the actual frozen process before readback. Label legacy API persistence
separately from generated Canvas scoped grants. Reject replaced vendor helper/
Common names in installed release metadata, including inactive Requires-Dist.”
Learning/evidence: isolated worker origin and restart receipts plus negative
metadata controls. Uncertainty: no generated deployment grant, browser, full
optional-provider or native Windows/macOS acceptance claimed.
