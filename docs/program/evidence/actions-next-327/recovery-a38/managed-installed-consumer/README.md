# Ordinary installed a38 managed consumer Action

This recipe uses ordinary Runtime CLI, Canvas MCP authoring, generated Python,
real RCC execution, and managed HTTP operations. It does not inject SQL state or
install a test-only service. The retained run passed completion and completion
replay after restarting the same datadir. It is not extension UI acceptance,
Robot execution, failed-job retry, or restart-during-execution proof.

## Pinned prerequisites

- Runtime source `f332a8284e78844abcf6700a600d2891d742b682`.
- Runtime 1.1.0a38 Linux CPython 3.12 wheel SHA256
  `103c53cf3b960fe173d6fa53485e097267a071684bc464214739b660a4c33203`.
- Core 1.1.0a3 and Work Items 0.5.0a2; MCP client 2.3.0.
- Existing installed interpreter
  `/workspace/actions-327-a38/installed-fixed/consumer/bin/python`.
- Prepared RCC 18.19.3 receipt
  `/workspace/actions-327-a38/compiler/prepared.json`, immutable artifact
  `sha256:23094fc1820262a768fd601f4964d633417fc2641f349666a5be55ab524f7598`.
  The script checks that exact artifact and the adjacent package.yaml digest;
  that package.yaml is the generated app's package contract. Do not substitute
  another compiler cache or copy private Runtime state to another machine.
- At least 5 GiB free. Keep this fixture under 1 GiB and logs under 20 MiB.
  This run used 847,195 fixture bytes and 4,900 log bytes. Check limits while
  running if adapting the script; they are asserted again at exit.

From the directory containing qualify.py:

```sh
ACTIONS_ACCEPTANCE_DIR=/workspace/managed-consumer-fresh \
  /workspace/actions-327-a38/installed-fixed/consumer/bin/python -I qualify.py
```

The target must not exist. The script creates a private directory, a random
loopback port and fresh synthetic bearer in process memory, then uses public
`authorize-local` dry-run/expected-grants-digest operations. It reads SQL only
to discover the bootstrap owner and compare counts. It stops every server in
finally and retains sanitized evidence. Do not transfer the private datadir,
profile, authorization requests or credentials. Transfer only screened evidence.

## Tester interaction recipe

Parent coordinates the tester; this document does not launch a desktop session.
On the tester host, provision the same pinned prerequisites locally. The script
is an executable reference for setup and sequencing, not a persistent fixture
host: its default run completes and stops all servers. For an interactive
harness, retain its fresh local key in a local mode-0600 file or process memory,
not an evidence file. Pause its ordinary server at the following boundaries:

1. After `provision_execution`, start with the exact profile and retained datadir.
   Give the extension the locally generated key, loopback URL and canonical
   Workspace UUID. Discover schema/capabilities/queues; use the exact `input`
   QueueRef and descriptor snapshot from canvas_inspect. No fixture bearer or
   authorization may be copied from another machine.
2. Enqueue the NDJSON payload, then claim it under the profile's trusted worker.
   Save the returned claim locally. Extension completion is not execution.
   Invoke `capability_invoke` through MCP with mode generic, exact snapshot and
   that claim to run the installed consumer Action in real RCC.
3. After successful execution, invoke managed `items.complete` with the same
   queue/claim, outcome done and a stable idempotency key. Do not submit output
   payloads or invented Run IDs. Inspect `runs.get`, its successful Attempt and
   four retained RCC/result artifacts. The extension can read/download these
   through advertised authenticated routes; capture UI screenshots separately.
4. Stop Runtime gracefully and restart the identical datadir/profile/key/port.
   Replay the identical completion request and require replay=true. Re-read
   the same Run ID, Attempt ID, output handles and counts. Never recreate state
   to simulate restart. Then stop Runtime and remove only this owned fixture.

The checked-in script performs steps 1–4 automatically. Its execution receipt
and before/after counts are API/installed proof; no extension screenshots are
claimed. A terminal successful Run is retained across restart, not resumed.

## Concrete missing paths in this installed version

GenericManagedWorkItemsService.capabilities advertises complete (with live
complete+claim grants and trusted worker identity), but never retry. Its
_completed method verifies the already successful canonical Run/Attempt and
exact four-output inventory. An items.complete call cannot start RCC work.

Ordinary foundry/bootstrap.py wires SQLManagedWorkItemsService with
NativeTerminalCompletion, but no worker_for callback. sql_service._operations
requires worker_available for reviewed retry; _worker_available is false
without worker_for. Granting retry permission does not wire an executor.
Do not claim native retry coverage or add a test-only worker to bypass this gap.

The exercised generated package is an Action consumer. It establishes no Robot
entrypoint, Robot RCC job, Robot completion, or Robot retry path. Those need
separate canonical installed setup and evidence; the managed protocol's generic
operation names alone are insufficient.

Upstream disposition: none. No external issue, publication, or repository change.
