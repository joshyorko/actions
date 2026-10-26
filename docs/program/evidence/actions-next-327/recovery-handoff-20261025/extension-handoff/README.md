# Automation 2.20.14: independent a37 managed acceptance

This handoff is acceptance only. It transfers no release implementation ownership.
Use an isolated Linux cloud VM; bind HTTP only to loopback. Do not use production
state, credentials, tunnels or a second campaign. No credential value is included.

## Candidate and schema prerequisite

`artifacts.json` records verified filenames/hashes/local paths. Exact remote source:
`f1b11838674494cd6a34d343b97404cbb1537004`, tree
`f094faf5d2eabbef0a159a7fabb4983a59a8e56c`. Runtime/Core were built from local
`b23df406f1e32e508e9a951f2469c6f57fa8c703`, the identical tree. The inherited SDK
wheel has unchanged work-items source versus frozen3037. Runtime a37/Core a3/SDK
0.5.0a2 exceed the client's version floors; that does not establish schema equality.

`managed-v1.json` is the actual installed a37 export and equals the source export.
Sorted compact UTF-8 JSON SHA256 is
`f815b507681e5ed0a3bfe761a3d12aed47d84d4fef4b74413431ddd138401d69`;
raw file SHA256 is `d8eb71c42f0b544dd15638420305eda6013b413a0b2c03b9894dd0900fab047d`.
The tester reported `360923ed094302e1cc6dd556d2c9117b445fbf8046b5684145c9eb2c2682123e`.
Desktop tester confirmed real drift: ExecutionSnapshot.capability_authority was added
(legacy-action/package-revision, default legacy-action); QueueView.mode adds
required-input. Installed2.20.14 correctly rejects this schema. Existing extension
owner is reviewing the contract adaptation with negative tests; do not bypass
equality or mutate that repository from this handoff.

No supported remote wheel download has been verified. Library tools/list returned
HTTP401; no upload IDs exist. Existing local wheel files are not cross-container
URLs. Rebuild from the verified private-repository commit using existing authorized
GitHub access; authentication/connectivity remains the tester's prerequisite.
Rebuilt wheels may have different archive/build metadata and hashes. Record them;
do not claim they are the exact previously qualified binary.

## Rebuild in an isolated checkout

Use pinned RCC18.19.3 and the repository's declared toolchain, not latest RCC or
ad hoc package installations. Example, with paths chosen in the tester VM:

```bash
git clone https://github.com/joshyorko/actions.git actions-a37
cd actions-a37
git checkout --detach f1b11838674494cd6a34d343b97404cbb1537004
git rev-parse HEAD^{tree}
rcc run -r developer/toolkit.yaml --dev -t Doctor
rcc run -r developer/toolkit.yaml --dev -t Bootstrap
rcc run -r developer/toolkit.yaml --dev -t ToolkitTest
python3 /path/to/handoff/build_candidate.py --source "$PWD" --output /path/to/owned-wheels
```

The helper creates a temporary RCC task using this checkout's developer/setup.yaml,
then calls committed toolkit.poetry for frontend embedding, PUBLIC OAuth generation
and the three wheels. It never reads another workspace's protected OAuth file.
This portable wrapper is provided for reproduction; it was syntax-checked, not
rerun as a second full build during handoff. `dependency-constraints.txt` retains
the installed a37 dependency set. A clean consumer may install only these rebuilt
wheels with those constraints, then run pip check; no editable/source overlay
qualifies as installed-binary acceptance. Base managed UI does not require the
optional DuckDB extra. Data execution separately requires its declared extra.

Pinned RCC18.19.3 requires a top-level `tasks` mapping even when invoking
`--dev`; a descriptor containing only `devTasks` is rejected. The wrapper now
declares the identical Build command in both mappings and an explicit temporary
`artifactsDir`, preserving the exact `developer/setup.yaml` and `--inside-rcc`
source boundary. Its descriptor regression preserves the initial missing-tasks
failure; this correction alone is not a completed wheel-build receipt.

Use a task-owned writable `POETRY_CACHE_DIR` in fresh testers. The desktop tester
reported that a read-only inherited cache appeared as PyPI connectivity failure;
setting a writable cache resolved Bootstrap through the pinned gateway. Inspect
the underlying filesystem error before changing dependency pins or network setup.

## Small runnable queue/review/Run/artifact fixture

After Bootstrap, use the prepared package interpreter:

```bash
/path/to/actions-a37/action_server/.venv/bin/python /path/to/handoff/fixture_host.py \
  --source /path/to/actions-a37 --state /path/to/new-private-synthetic-state --port 8765
```

The source tree is verified before setup. State must be new. The fixture generates
a local secret into mode0600 `local-bearer`; read it ONLY inside the tester VM into
the extension's existing secret-storage UI. Do not print it, send it across threads,
commit it, place it in URLs or include it in screenshots. Configure the extension
with `http://127.0.0.1:8765`, the canonical Workspace UUID from `fixture.json`, and
that local bearer. No caller-provided actor/worker header is trusted. Stop with
Ctrl-C; no worker or external service remains. Use a fresh state directory for a
new session/key; keep old state private if evidence is needed.

This is an explicitly synthetic definition/authorization fixture running actual
Runtime SQL, query Run/Attempt, sealed output and review services. It creates a
small invoice source and an actual completed bounded query, then a pending review.
`fixture.json` gives exact queue/deployment/review/Run/artifact identities and contains
no bearer. It is NOT an ordinary installed Runtime/bootstrap, generated RCC or
production identity proof. Self-test passed:401 without auth, live schema equality,
capabilities, review listing, Run read and artifact read (`self-test.log`).

Negotiate authenticated GET `/api/managed-work-items/v1/schema`, then GET
`/api/managed-work-items/v1/capabilities?workspace_id=<fixture UUID>`.
POST `/api/managed-work-items/v1/operations` with closed typed commands from the
export. Test queue list -> reviews.list -> explicit reviews.decide approve using
returned proposal -> items.list/get -> claim/renew -> Run/log/artifact inspection.
Use unique idempotency keys per intent; replay the SAME key and exact request after
a transport uncertainty. Cancel uses the actual item epoch and an explicit reason.
Never fabricate a completion, alter a claim owner, treat queue IDs as paths, or
supply arbitrary Run IDs/output bytes as proof of execution.

This fixture advertises read/list/review/claim/renew/cancel/Run/log/artifact operations
subject to grants. It has no RCC worker; retry and complete are NOT advertised.
No model-facing tools are hosted by this small fixture. Client controls must follow
negotiated operations, not version or the union of another queue's capabilities.

## Supported production surface and remaining acceptance

Ordinary a37 routes share canonical SQL authority. Reviewed queues can support
retry and completion only with the actual configured worker/native completion and
trusted worker identity; their durable receipts/fences decide success. Generic
optional/required/consumer queues currently advertise discovery/read/enqueue,
claim/renew/complete where eligible, and Run/log/artifact reads. Generic review,
retry and cancel are not advertised by that delegate. Producer output queues are
not interchangeable with reviewed input queues. `/api/work-items` legacy CRUD is
not this managed protocol and must not be used as fallback. Artifact handles remain
authorized opaque references, not arbitrary filesystem paths.

Actual ordinary installed generic producer/consumer browser evidence is already
in recovery-a32/ordinary-browser; Task execution/restart is in recovery-a35/installed;
a37 installed Data/readiness is in recovery-a37/installed-readiness. Those receipts
do not close extension acceptance. Full completion/retry UI acceptance needs an
actual configured execution fixture, not the subset host above. Preserve that as
a remaining gate if the tester's scope requires it. Do not start tunnels or modify
credentials to bridge machines. No other repository mutation is authorized here.
