# Dakota actual ChatGPT host acceptance — agent prompt (DRAFT)

This is a preparation artifact, not a dispatch or a READY declaration. The parent
integrator must first confirm the concrete endpoint/auth/resource plan is ready.
Codex cloud network failures alone do not block this separate host test. Josh may
then start the local agent from the existing Actions repository on Dakota and give it this prompt.
That launch authorizes only the agreed temporary test connection and synthetic
local acceptance; it does not authorize changes to existing Executor transport,
credentials, tunnels, workspace policy, public releases, or production.

## Task for the local agent

Read this repository's `AGENTS.md`, `.agents/skills/actions-repository/SKILL.md`,
`docs/skills/README.md`, and relevant canonical operations guidance. Apply the
existing #327 / Canvas #71 / draft #328 owner contract. You are an acceptance
operator, not a second implementation owner. Do not create a branch, PR or issue,
commit/push, fix product source, change release scope, or start other agents.

Test the exact candidate below through **actual ChatGPT Desktop** with fresh
synthetic local state, document the real model/tool and rendered app interaction,
then remove only this test's temporary connection and resources. Preserve the
existing Executor and every unrelated setting. Report concrete BLOCKED or FAIL
states; neither an SDK client nor a browser/reference host substitutes for the
requested Desktop result. Do not declare the overall campaign ready.

## Immutable evidence and artifacts

The evidence review point is `ec514752` on the existing release branch. Its
`recovery-a38/installed-qualified/{README.md,build-inputs.json,wheels.json}` pins
the **tested product source**, which is older:

`f332a8284e78844abcf6700a600d2891d742b682`

| Installed artifact | SHA256 |
| --- | --- |
| `actions_runtime-1.1.0a38-cp312-cp312-linux_x86_64.whl` | `103c53cf3b960fe173d6fa53485e097267a071684bc464214739b660a4c33203` |
| `actions_core-1.1.0a3-py3-none-any.whl` | `4147cdeb2a593e54194b4d2fcd2c92f0b029fb802d1d298e35c912a1fef03167` |
| `actions_work_items-0.5.0a2-py3-none-any.whl` | `72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb` |

Verify local wheel bytes before installing into an isolated noneditable consumer;
record Python/OS/architecture, installed versions, import origins, and `pip check`.
Use the repository RCC/Poetry boundary and retained dependency/build inputs. The
Runtime wheel is Linux x86_64 CPython 3.12 only. Do not claim it qualifies a native
Windows/macOS build, use a source overlay, or replace it with an unmeasured wheel.
If unavailable or incompatible, report the exact missing artifact/platform and
stop dependent host execution. An exact-source rebuild is a new artifact needing
its own qualification, not this wheel's measured proof. Do not retry the previous
Library HTTP401 or work around an artifact access denial.

Read these retained receipts before adapting their public setup sequence:

- `recovery-a38/installed-qualified/client-fixed/qualify.py` and `receipt.json`.
  The receipt remains FAIL because its historical rollback call was wrong, even
  though the four genuine executions and artifact reads completed.
- `recovery-a38/installed-qualified/client-continuation/{qualify.py,receipt.json}`.
  This PASS uses `rollbackTo`, not `candidateRevision`, for historical activation.
- `recovery-a38/official-host/{README.md,qualify.py,browser.mjs}` and
  `browser-revised/`: independent word counter, official ext-apps 2.0.3 source
  `82221c0c8ce7661efa6771c9d461511b1650495f`, actual click/result and captures.
- `recovery-a38/codex-client-blocker/README.md`: no completed genuine model/MCP
  acceptance in either cloud probe. Do not silently upgrade this status.

Paths above are relative to `docs/program/evidence/actions-next-327/`. The scripts
contain old cloud paths and synthetic setup; they are references, not commands to
run unchanged against Dakota. Never copy their datadir, identity, auth, AppSession,
Workspace IDs, profile IDs, or existing account configuration.

## Preflight before any connection change

1. Confirm the parent-authorized scope in the active local conversation. Inspect
   repository status without resetting it; record local HEAD separately from the
   artifact source. Preserve all existing uncommitted work.
2. Identify the running ChatGPT Desktop product, installation provenance,
   version, OS, selected account/workspace and relevant connection permissions
   without collecting identity tokens, browser cookies, auth files or screenshots
   of private account details. Distinguish genuine Desktop from a web wrapper,
   browser tab, Codex or official example host. Existing login is not acceptance.
3. Inspect the actual supported UI for creating/removing a temporary custom MCP
   connection, invoking write tools and rendering MCP Apps. Recheck official
   OpenAI documentation and the installed UI; labels/features can differ by
   release/account. As reviewed on 2026-10-25, official Help establishes custom
   MCP full support on **ChatGPT web**, not this Desktop build. A missing Desktop
   capability is BLOCKED; do not silently run the test in web or change policies.
4. Record a secret-free before inventory of connection names/IDs, relevant
   settings, owned processes and listeners. Hash only the exact config files
   legitimately involved; do not dump or copy credential stores. Note the existing
   Executor identity/transport so it can be shown unchanged later. If safe config
   comparison needs reading secret-bearing content, retain only private local
   before-state/digests, never attach the content.
5. Check bounded disk/toolchain availability and exact candidate artifacts. Use
   a uniquely named private task directory, empty working directory, new datadir,
   ephemeral port and distinct connection name such as
   `actions-327-a38-dakota-<local-run-id>`. Do not reuse an existing datadir,
   database, Runtime port, browser profile or Executor connection.

Official references (revalidate locally):
[custom MCP support](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt),
[connection testing](https://developers.openai.com/plugins/deploy/connect-chatgpt),
[authentication](https://developers.openai.com/plugins/build/auth).
These links establish prerequisites, not a claim that this Desktop build or a38's
Bearer API-key mechanism is compatible with the available connection UI.

## Exact endpoint and authorization prerequisites

The owned Runtime's MCP endpoint is
`http://127.0.0.1:<new-owned-port>/mcp`, Streamable HTTP. Bind Runtime to loopback;
use a fresh private datadir and `--actions-sync=false`. The cloud receipt used a
fresh API key as `Authorization: Bearer <local-key>`, the normal installed CLI,
and explicit `ACTIONS_FOUNDRY_EXECUTION_PROFILE` / `ACTIONS_FOUNDRY_TASK_POLICY`
files. Reproduce those *public* setup boundaries with locally created synthetic
values, not SQL inserts or borrowed cloud identities. Protect private files and
logs; never paste keys into chat, URLs, evidence, screenshots or shell history.

An ordinary remote ChatGPT connection cannot reach Dakota loopback by assuming
`localhost` is the user's machine. Resolve the actual supported connection mode
before adding it: an already authorized separate reachable HTTPS endpoint ending
in `/mcp`, or a supported, explicitly authorized private transport. The exact
external URL/transport and its auth mechanism are **unresolved prerequisites**,
not values supplied by this draft. This task does not grant permission to create
or repoint tunnels, modify DNS/firewalls/proxies, disable TLS/DNS-rebinding checks,
or alter Executor. If a new route is necessary, present its concrete isolated
configuration and obtain the separately required authorization before using it.
Do not infer a generic “temporary MCP connection” grants these wider changes.

Verify that the supported Desktop connection can authenticate to this exact
candidate without weakening it. Do not assume it accepts a custom Bearer header
or equate its OAuth choice with a38's API-key auth. If the two do not match, report
the precise unsupported mechanism; no unauthenticated exposure, new auth proxy,
credential conversion, account login workaround or product patch is permitted.
Keep transport authentication distinct from saved-owner Workspace grants and
AppSession-scoped app authority. A connection success grants none of the latter.

Before public interaction, use only the owned candidate's public startup and
stopped-local `authorize-local` setup. Provision a fresh canonical Workspace and
execution profile with prepared pinned RCC evidence; explicitly authorize
`authorize-generated-source` for that profile. After an exact synthetic Deployment
exists, stop only the owned Runtime and use `authorize-exact-deployment` for that
exact target and the minimal tested Run/queue operations needed by the scenario;
restart that Runtime with the same task-owned datadir. Use the current schema and
CLI help, not guessed flags or IDs. The retained qualifier records the tested
operations. Do not introduce Knowledge a39, celld, proprietary Data Server or a
new scheduler/database authority into this a38 test.

Record endpoint shape and authentication *type*, not credential values. For any
approved HTTPS path, verify the exact host/origin policy and supported Runtime
transport setup. a38 defaults to loopback DNS-rebinding allowlists; never add a
wildcard or disable checks. The supported tunnel mechanism adds/removes only its
owned exact host/origin, but using it still requires the separate route authority.
An unexplained 401/403/421 is a diagnostic result, not permission to bypass auth.

## Actual Desktop scenario and evidence

Create the single temporary connection using the actual supported Desktop UI,
review its discovered tool schemas and metadata, and record its exact connection
ID privately for removal. No workspace-wide publication. Do not change existing
connections, trust policy or user approval preferences.

Use a new synthetic conversation. Ask the actual ChatGPT model to discover the
six-tool Canvas authoring surface, create a blank Canvas, author a useful typed
form with generated Python, validate and activate it using the public flow. A
bounded first app can normalize words and add two counts as two Actions in one
Package. Use synthetic input only. Do not seed the finished app by calling tools
from an SDK and present it as model-authored. When an operator grant step is
required, perform only the explicit exact-target local authorization above, then
resume the same model-authored app.

Check actual tool discovery, resource MIME `text/html;profile=mcp-app`, official
UI-bridge initialization, form rendering and model/app audience separation. A
plain text tool result, link to the Runtime preview, or reference-host iframe is
not a Desktop app render. Opening/reopening must not create a Run, approval or
external effect. Model-visible tools must not expose app-only dispatch/review
operations; public app interaction must carry the current scoped AppSession.
Do not save that session field in evidence.

Interact with the real rendered form: inspect the current revision and requested
operation, enter synthetic values, explicitly approve where required, click and
observe completion. Follow the actual Run/Attempt and handle-first artifact via
public interfaces; verify expected bytes (for example normalize `a  b` to `a b`,
and add `7` plus `9` to `16`). Preserve request/Run/Attempt/Package/Deployment IDs
and their association in sanitized receipts. Supplemental read-only canonical
counter inspection may explain no-duplicate behavior but cannot replace the
visible interaction or public artifact readback. Do not claim MCP Tasks support
unless Desktop actually negotiates and uses that extension; distinguish it from
app execution or SDK Task proof.

Create a second independent model-authored Python app, such as the word counter
`alpha beta beta` -> `3`, with an explicit artifact semantic node. Revise its UI
without changing its immutable backend unnecessarily. Observe failed validation
retaining the previous active revision. Exercise historical rollback with
`rollbackTo`, restore the exact prior immutable revision, and restart only the
owned Runtime. Reconnect/reopen; obtain fresh app authorization, read retained
artifacts without re-execution, and establish that stale authorization is denied.
Do not copy raw AppSession material into the transcript for a negative test.

If exposed by the supported UI/public contract, check explicit denial after
revoking only the task-owned synthetic target grant and after supplying an invalid
or stale synthetic target. Record unsupported negative cases as NOT_RUN rather
than bypassing UI boundaries or manufacturing success. Preserve the invoice app
and any existing independent apps; this test's fresh datadir must not touch them.

For each screenshot, record UTC time, artifact source, Desktop version, scenario,
app/revision and relevant sanitized Run/Attempt IDs in a sidecar:

- Temporary connection discovery/settings with credentials and private account
  details excluded, plus the actual product/version surface.
- Empty Canvas and the actual model-authored generated-backend/validation result.
- Wide rendered form before execution and the explicit operation/approval state.
- Completed result/artifact showing the synthetic expected value.
- Narrow window with readable controls/result and no horizontal clipping.
- The second independent app's form and completed result.
- Reopened retained result after rollback/restart; unchanged canonical Run count.
- A supported denied/stale/revoked state, or the exact unsupported-host error.
- Connection removal and the unchanged Executor connection inventory.

Review screenshots before retaining them. Avoid auth panels, raw request/response
traces, unredacted HAR, private account data, key-bearing command lines and browser
storage. Keep bounded sanitized receipts and selected screenshots, not whole user
profiles or broad desktop captures. Preserve earlier failed steps as failures.

## Narrow cleanup, including failures

Maintain an ownership ledger as resources are created: exact connection ID,
process IDs and their command/datadir identity, task directory, port, and any
separately authorized transport handle. On completion, failure or interruption,
remove only that temporary connection in the same supported UI; confirm it is
absent. Do not restore an entire old configuration file over concurrent user edits
or remove all entries matching a generic Actions name. If config changed since
preflight, remove only the owned entry with an exact identity check or report the
cleanup conflict for operator handling.

Stop only task-owned processes after matching their recorded identity. Revoke or
destroy only newly created task-scoped authorization/private state after saving
sanitized evidence; remove task-created secret files without printing them. Never
rotate/revoke existing account credentials, remove the ChatGPT login, kill the
existing Executor/Runtime, or delete caches/datadirs owned by other work. If a
transport was separately authorized and created, remove only that exact owned
handle; otherwise make no transport change. Verify the port/process is gone and
Executor plus unrelated connection/config inventory remains unchanged. Do not
invoke Executor write tools merely to demonstrate cleanup.

Return PASS/FAIL/BLOCKED/NOT_RUN per case, exact artifact identities, model/client
vs SDK/reference-host distinctions, sanitized screenshot paths and hashes,
source/Runtime/host versions, canonical associations, and cleanup disposition.
For a blocker give the exact action/target/reason and whether denied, pending or
uncertain; check uncertain outcomes before retrying. No publication, production
change or release-ready claim. Do not upload evidence to a denied destination.
Run the repository fail-closed evidence guard on any subsequently staged evidence;
manual screenshot/content review remains necessary. Upstream disposition: none.
