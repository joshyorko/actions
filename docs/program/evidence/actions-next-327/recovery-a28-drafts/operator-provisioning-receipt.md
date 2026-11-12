# Local offline operator authorization draft

Base fdc38d7090c4ac470171c499e77eab636fd452e6. Four-file patch `operator-provisioning.patch`, SHA256 `d58eda961d331572e92626e878b695a4e512556427424b37d4904a3b7e5c1084`. Own scratch only; no shared source, active datadir, credentials, external repository, RCC environment, network service, or release mutation. `git apply --check` against the current shared checkout passed read-only.

## Exact proposed canonical documentation addition

Append to `docs/skills/repository-operations.md`, ordinary Runtime operator setup:

The configured Runtime still never grants execution during startup, activation, discovery or dispatch. An explicit local operator can use `action-server authorize-local` to provision its existing saved owner after stopping Runtime and all independent SQLite writers. This v1 command is POSIX/local-SQLite only, uses the existing canonical `action_server.lock`, never kills a lock holder, and refuses `ACTION_SERVER_DATABASE_URL`. It opens only the existing `server.db` in the specified datadir; it neither creates a realm/database nor migrates one. Custom DB filenames and remote PostgreSQL deployments need a separately qualified operator path. The caller must exclude concurrent same-user filesystem changes: path-based file checks and the cooperating Runtime mutex are not adversarial same-user filesystem confinement or proof that arbitrary SQLite tools have stopped.

The datadir must be owned by the invoking OS user with owner-only permissions; `server.db`, the request and profile must be private owned regular files. Symlink paths, hardlinked state, unsettled SQLite sidecars, and an unsafe canonical lock file are refused. No permission bits are repaired automatically. The command verifies the existing bootstrap Request and Audit lineage and active saved Workspace; it cannot select an arbitrary grant recipient. Schema/validation errors do not echo rejected token values.

Use `action-server authorize-local --schema` to inspect the strict request schema without opening state. The only grant recipient is the saved owner. Supply an explicit existing trusted Runtime execution-profile file and its exact Workspace. That profile is selected configuration, not proof of prepared RCC readiness; the authorization command never invokes RCC or creates profiles/packages/admission records.

For generated source, prepare a private request file with `schema_version: actions.local-authorization/v1`, `operation: authorize-generated-source`, `target: generated-source`, a unique `request_id`, exact `workspace_id`, and absolute `runtime_profile`. This explicitly authorizes Workspace `execute_generated_source` and the selected worker/policy/output-provider references' deploy/execute operations. It does not silently restore unrelated authoring grants or authorize other profile references.

First run `action-server authorize-local --datadir /absolute/private/datadir --request /absolute/private/request.json --dry-run`. Review the returned owner, Workspace, exact references and scope; copy its `expected_grants_digest` into the request. Then run the same command without `--dry-run`. A changed grant state fails the compare-and-swap check inside the same canonical SQL transaction as grant changes, Request and Audit. Repeating the identical request ID/body returns its historical receipt and current scope digest without restoring revoked grants; changing the request under the same ID is rejected. Keep a new ID for a new operator decision.

After a generated revision is activated, `authorize-exact-deployment` with `target: deployment` additionally requires the exact active immutable `deployment` reference and explicit `run_permissions` and/or `queue_permissions` lists. Its profile and retained Package/capability/plan identities are validated. **Existing authority granularity is preserved:** Run permissions are stored for the application ID and can affect retained/future revisions, subject to other live checks. Queue permissions cover all queues of the exact Deployment revision, with a Workspace permission gate. This is not a new per-Run-revision or per-queue grant system. Named Run operations are read/execute/cancel; queue operations are the allowlisted read/enqueue/claim/complete/cancel/review/artifact-read permissions. Retry is not enabled. Dry-run receipts and the request schema explicitly show these scopes. Permission grants do not claim a corresponding optional adapter or execution path is available.

`operation: revoke` retains the same explicit target and named operations. It subtracts only command-owned Foundry permissions, preserving unrelated grant rows. Explicit named Run revocation affects the existing application-wide grant, including other revisions. Other independent grants can still permit an operation; removal of this command's rows is not a promise that every independent authority was revoked. Revocation may select an exact retained previously activated revision without reactivating it. Existing command-owned rows require their prior authorization Request/Audit provenance. Historical revocation validates retained identity/profile and does not require Package source/provider or RCC environment readiness. It neither executes nor registers an admission. Authorizing an old nonactive revision remains refused.

Qualify this seam through real owner/bootstrap/SQL and immutable Package fixtures, stale-CAS and replay checks, historical revocation, rollback on Audit failure, root help/schema parsing, filesystem and cross-process canonical-mutex rejection. Installed CLI qualification is separate: source tests and synthetic compiler fixtures do not establish an installed release, actual RCC execution, public MCP grant administration, or PostgreSQL offline safety.

## Evidence and limitations

- `red.log`: initial missing-module regression (source was temporarily absent).
- `first.xml`: 12 setup errors from unrelated package feedback fixture looking for scratch RCC binary; no product execution occurred. Offline tests now explicitly override that feedback fixture to prohibit RCC.
- `second.xml`: 11 passed, one held-lock reentrancy error; corrected to a controlled refusal.
- `third.xml`: 17 passed.
- `final.xml`: 20 passed.
- `qualified.xml`: 22 passed, including a separate Python process holding the canonical Runtime mutex.
- `historical.xml`: 25 passed, including old-authorize refusal, historical revoke, no readiness calls, replay and missing ownership provenance refusal.
- `release.xml`: 26 passed, adding lock-symlink external-target immutability.
- `help.xml`: root CLI help snapshot passed.
- `complete.xml`: final complete file run (see exact receipt).
- `final-static.log`: mypy two source files passed; Ruff passed. Formatting-only CLI changes followed, with complete tests rerun.
- `request-schema.json`: generated actual strict request JSON schema, no instance secrets.

Only own synthetic SQLite state was changed. PostgreSQL is intentionally unsupported and rejected, not counted as skipped proof. No RCC process or compiler environment was used. No installed qualification or public owner gate is claimed. Full package/integrated tests remain root-owned after the frozen gate.

## Documentation improvement receipt

- Canonical file proposed: `docs/skills/repository-operations.md`; exact addition above.
- Durable learning: explicit local owner-only provisioning, existing grant granularity, stable replay/CAS, historical removal without operational readiness, and limits of an offline datadir mutex.
- Evidence: the strict CLI/schema, common SQL tests/receipts listed above, existing RunAccessGrant key and SqlQueueAuthorization exact-reference policy.
- Stale or ambiguous guidance removed: the statement that no public operator provisioning route exists must become version-qualified; startup/activation still grant nothing. Do not describe application-wide Run permissions as revision-local or a Runtime mutex as remote DB quiescence.
- Remaining uncertainty: installed consumer and full integrated package qualification; external databases/custom filenames/non-POSIX systems remain unsupported. All writers, including independent SQLite tools, must be stopped by the operator.

Upstream disposition: none. This is a repository-owned missing operator seam; no external issue or mutation.
