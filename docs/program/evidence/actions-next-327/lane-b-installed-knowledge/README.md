# Lane B: installed Knowledge acceptance assertions

Base: `da928b69e0558917c3e88af9297ddfd3bec818e8`. This slice adds a
read-only page-artifact checker and synthetic tests, not a production feature or
installed acceptance result. No production, shared guide, version, registry,
schema, authorization, compiler or migration file is changed.

## Verified boundary

The checker requires complete ordered fixture hits, contiguous pages, consistent
revision/corpus/ingestion/query/total identities, unique document identities,
bounded aggregate bytes and identical downloaded page bytes after restart.
It rejects duplicate JSON keys. Fixture expectations are supplied independently
of the downloaded pages. The successful CLI result explicitly reports
`execution: NOT_QUALIFIED`.

Use it only after the installed driver has downloaded each independently admitted
search's output through the authorized artifact route:

```bash
<installed-python> action_server/scripts/qualify_lane_b_installed_knowledge.py \
  --before page-0.json page-1.json \
  --after restarted-page-0.json restarted-page-1.json \
  --expected-hits owned-fixture-hits.json --max-bytes 65536
```

That command is a usage template, not a recorded installed run. This checker does
not validate grants, SQL seals, wheel origin, Task identity, native RCC execution,
server restart or provenance issuance. Its synthetic unit tests prove none of
those properties.
Read-only peer review found no blocker within this scope. Provenance checks
compare pages with each other, not with an independent expected revision/digest.
The CLI preflight bounds page artifacts, not the trusted expected-hits fixture.

## Evidence and remaining execution gates

Fresh isolated workspace used Josh RCC 18.19.3 Doctor, Bootstrap and ToolkitTest
in that order, with task-local ROBOCORP_HOME, XDG_CACHE_HOME and POETRY_CACHE_DIR.
Doctor and Bootstrap passed; ToolkitTest passed 190 cases. Prepared toolchain:
Python 3.12.15, Poetry 2.1.1, Node 20.19.3, Go 1.23.6. Disk available after
Bootstrap: 25 GiB. Gateway stdout remains in the task-local receipt directory.

Initial package-local command:

```bash
poetry run pytest tests/contract_tests/test_lane_b_installed_knowledge.py \
  --junitxml=/workspace/lane-b-state/receipts/page-checker.xml
```

Result: 18 passed, zero skipped. Original stdout/XML are retained as base64.
After formatting, the first lint invocation failed with six E721 exact-type
comparison diagnostics. The comparisons now use isinstance with explicit bool
rejection for numeric fields. Corrected test rerun: 18 passed, zero skipped;
Ruff check, configured Ruff format check and Isort check passed on both files.
Corrected stdout/XML and the initial lint failure are retained separately.
The first tiny run loaded optional Robot tracing; subsequent runs disable its
`robocorp_log_pytest` plugin and retain stdout/XML. No failure was discarded.

The installed lifecycle remains NOT RUN pending the integrator's immutable
generated-Knowledge checkpoint and its candidate artifacts. At this base,
`LogicalExecution.require_selected_adapters` and `prepare` reject non-Data
requirements. The a39 host-preparation/context READMEs explicitly leave generated
Task/RCC publication and clean installed a39 open. Runtime/Core metadata remains
a38/a3; the mapped compiler contract requires a39/a4. Do not build falsely
versioned candidates to bypass this boundary.

Next installed matrix, separately on real DuckDB and owned TLS PostgreSQL:

1. Verify installed distribution versions, module origins and candidate hashes.
2. Configure/provision through saved-owner public CLI with explicit grants.
3. Author/activate the generated ingestion and search Actions and Canvas controls.
4. Ingest through ordinary Task/common Run; retain Task/Run/Attempt/publication
   identities and resolve the sealed corpus artifact through public authorization.
5. Search with explicit input mappings; fetch every fixture page and its artifact.
   Apply this checker to independent expected document bytes.
6. Restart, obtain a fresh AppSession and replay retained Task/results; repeat
   paging/artifact checks without another ingestion or replacement provider write.
7. Preserve separately unauthorized/revoked search, canceled ingestion/search,
   incomplete publication and replay outcomes. Unexecuted stages remain unverified.

This matrix is planned, not an acceptance claim. The invoice fixture and universal
Canvas remain separate protected requirements.

## Integration and rollback

Cherry-pick this lane's reviewed commit onto the integrator's current branch.
Files are additive and independent of generated Knowledge production work.
Rollback removes the two lane-specific Python files and this evidence directory;
there are no persistent migrations or runtime effects. No full package suite is
claimed for this test-only slice.

## Proposed canonical documentation delta

Integrator-owned target: `docs/skills/repository-operations.md`, immediately after
the bounded lexical-search paragraph. Add exactly:

> Knowledge search pagination returns one bounded page with the immutable revision,
> ingestion handle, corpus digest, query and total match count. The standalone
> worker publishes that page as `knowledge-search.json`; downloading it does not
> establish complete-result export. Qualify multiple pages through separately
> admitted, explicitly mapped invocations, preserving corpus and query identity,
> then compare downloaded bytes and repeat after restart. Core's prepared search
> accessor cannot issue additional provider queries by changing offset or limit.

Evidence: base `knowledge_execution.py` search request, standalone execute and
`search_for_execution`; `actions/knowledge/__init__.py` prepared accessor.
Learning: distinguish single-page artifact retrieval from complete-result export.
Ambiguity removed: treating artifact download as full export qualification.
Uncertainty: recheck publication behavior at the forthcoming generated checkpoint.
No shared canonical guide was edited concurrently.

Possible independent feature for allocation: a client-side complete-page export
assembler in `action_server/scripts/lane_b_knowledge_page_export.py` plus its
lane-specific test. It would consume already authorized pages only. A new typed
backend export operation crosses reserved contracts and remains integrator-owned.

Upstream disposition: none.

## Prepared installed orchestration (not executed)

The second slice adds `lane_b_build_installed.py`, which parameterizes the retained
a38 committed-source build recipe: clean expected SHA, 8 GiB disk admission,
pinned bundled RCC, archived frontend/public OAuth generation, three wheels,
declared DuckDB extra, retained install constraints, pip check, and isolated
installed version/origin checks. It does not change candidate versions. Linux
paths are explicit; this is not cross-platform distribution qualification.
Build execution awaits the producer checkpoint; py_compile and scoped static
checks plus a genuine dirty-checkout refusal test are its validation so far.
Peer review caught preflight failures occurring before receipt initialization;
the builder now preserves those failures, refuses existing destinations without
overwriting them, constrains the tracked constraints path, and records tool paths.

`lane_b_installed_knowledge_lifecycle.py` consumes a private manifest containing
installed interpreter/prefix/versions, source checkpoint, preprovisioned stopped
datadir/profile/Task policy, Workspace, ingestion/search app and binding IDs,
query/page limit and independently expected document objects. It starts only an
owned loopback server, discovers snapshots and semantic artifact nodes, invokes
real detached Tasks, downloads authenticated output artifacts, restarts and
replays retained Task identities and bytes. It has no SQL/provider fallback.
Operator setup, source authoring, negative grant/cancellation tests and full
browser acceptance are explicit remaining gates. The checkpoint field is an
operator assertion, not independent proof of wheel/source equivalence.

A genuine subprocess refusal test uses the package's editable interpreter and
verifies that installed-origin validation fails before any server or Task starts.
Result: 1 passed, zero skipped; retained stdout/XML below. This is refusal
evidence, not successful installed execution. The runner requires 1 GiB free disk,
records artifact HTTP status without credentials, and retains failed/unexecuted
stages. Optional tracing was disabled for this test.
The subsequent joined refusal inventory passes 2 cases, zero skipped, including
the builder's preflight failure receipt. Original and later receipts are retained;
these overlapping counts are not summed. The helper's attempted Black check was
unavailable; configured Ruff format and Isort were used successfully instead.

At the base checkpoint, ordinary startup does not construct RunOutputTransport;
the optional `_server` route is supplied by the invoice-generated integration.
The runner's detached-Task HTTP download can therefore fail even when a Task
completes. This is a source-observed route dependency, not an observed installed
failure yet. A direct service read or an app-associated Canvas artifact call
does not qualify that particular detached HTTP gate. The integrator owns the
startup/auth/transport decision; this lane will not wire a new shared route.

Exact additional canonical delta proposed after the previous paragraph:

> A completed detached Task does not establish HTTP artifact-download acceptance.
> Qualify the ordinary installed host's authenticated output route separately.
> Preserve an unavailable route as a failed gate instead of substituting direct
> RunOutputService access. A lifecycle runner using preprovisioned applications
> also leaves operator provisioning and authoring as separate prerequisites.

Evidence: `_server.py` optional `run_output_transport`, the only constructor in
`data_queries/generated.py`, and the new runner's explicit HTTP route. Remaining
uncertainty: recheck ordinary wiring in the incoming generated-Knowledge checkpoint.

Production feature proposed for allocation (not implemented):
`data_queries/knowledge_export.py` and `test_knowledge_export.py`, with
`export_for_execution(service, actor, fence, request, cancelled)` consuming the
existing authorized search hook under the same fence, bounding aggregate bytes
and documents, enforcing stable revision/corpus identity, and returning
deterministic complete-result bytes. Typed operation declarations and final
publication integration remain reserved to the integrator.
