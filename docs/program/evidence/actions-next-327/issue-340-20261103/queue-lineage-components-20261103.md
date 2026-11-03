# Queue publication and child lineage components, 2026-11-03

At local commit `3d534d23653f9703a12f022706b99d4c82e5712c`, the explicit
model queue selection has exact queue IDs and a closed per-operation set.
Its guarded focused suite passed 7 cases on SQLite. A prior run reached six
passes and one failure: the round-trip fixture compared original tuple order
with deliberately sorted canonical data. The corrected assertion checks exact
membership and stable canonical bytes. An earlier setup-only attempt failed
before tests because the task-local RCC environment was not activated.

At local commit `3a2ffe8a93cf4f3cfb3c564628ba8a217d409f92`, child lineage
migration 23 stores identity, without authorizing or executing a child. Four
focused SQLite migration tests and the generated schema regression passed;
12 existing detached and release migration tests also passed on SQLite. The
first two focused attempts each failed one fixture: missing transaction, then
expecting the raw SQLite exception rather than the database wrapper's error.
Those failed receipts remain distinct. PostgreSQL parity is not established.
No database foreign keys link lineage to Runs; host admission must verify both
references and Workspace atomically. The stable identity excludes attempt epoch,
but the record alone does not enforce delegation, child quota, cancellation,
result authorization or retry fingerprint.

Each passing invocation used the existing task-local RCC environment, a 10 GiB
floor plus 48 MiB guard, and a host subreaper supervisor which reported no owned
processes remaining. Raw logs and the failed attempts are preserved in the
Library evidence archive, alongside the unpushed git bundle. These are source
component checks, not an installed Action-to-Robot vertical or release proof.

The standalone model queue guard at `1650f342e07da56c6a66bd346eb88f3b40503cb8`
passed six SQLite cases with six PostgreSQL skips, including an in-flight
callback and subsequent publication revocation on separate connections. The
supervisor confirmed no owned processes remained. The preceding concurrency
attempt failed while its test file was being edited, so its source identity is
unqualified; both that log and the frozen rerun log are retained. The guard
requires the domain callback to recheck live permissions on the same connection.
Native startup, exact live queue resolution and the guarded callback adapter
remain unwired; the component test is not an installed authorization proof.

The queue-targeted facade path at `4eb1f3f7b794915dae695eba9af7b24188e104b2`
passed 12 focused cases with two PostgreSQL skips. It calls the atomic guard and
existing domain port in one worker-thread transaction, and fails closed without
the guard. Controls include stale publication and a revoked domain queue grant.
The workspace list path and native startup remain unwired. The supervisor
reported no owned processes remaining; the raw focused log is in Library archive
`libfile_b1e3d498c26c8191b3f02281a7f5d57f`, version 4.

The atomic queue-list component at `31cc605ea5113c89dea1f233e1d24668ca7acb84`
passed 20 combined facade/guard cases with 10 PostgreSQL skips, including a
two-connection multi-page scan and concurrent publication revocation. On the
same source, existing Canvas/MCP tests passed 12 cases and protected-route
initial-denial checks passed both shutdown configurations. All were source
checks supervised with the capacity guard and no owned process remaining; they
do not qualify packaged native startup, a real ChatGPT host, or PostgreSQL.
The SQLite domain test does not replace live PostgreSQL authorization parity.

The current publication-policy adapter at `9df0482330a54af1c8531f7329ca6bbc317c5a2b`
passed five SQLite cases with five PostgreSQL skips. Its first test attempt
failed four tuple/list fixture assertions; the corrected worker-thread test also
proved the real selected queue was resolved. The combined guard, facade, list
and policy suite after lint corrections passed 25 cases with 15 PostgreSQL
skips. The policy remains a preflight; the guard and domain port recheck actual
publication and permissions.

Source native MCP wiring at `a3529268ed493e0d7b45e34776213c87a1e0cef9`
passed 18 startup, existing Canvas/MCP and protected-route cases with one
PostgreSQL skip. The initial startup attempt failed because a test double lacked
catalog identity; the corrected run includes a real SQLite policy/guard fixture.
It does not prove a built or installed native Runtime, actual ChatGPT transport,
or PostgreSQL. All supervisors reported no owned processes left. The failed and
passing logs are in Library archive `libfile_b1e3d498c26c8191b3f02281a7f5d57f`,
version 9.

The standalone internal-delegation value at
`19950123f4aaa5466aeb9e796b9ea498eab4c844` passed 12 source cases and focused
lint. The first attempt failed collection on an incorrect fixture ID import;
the second failed on noncanonical fixture digests; the third had 10 passes and
two positive fixtures with mismatched Workspaces. The corrected run retained
cross-Workspace and non-RCC-target denial tests. This is policy data only:
there is no immutable persisted Deployment delegation, host authorization,
atomic child admission, process transport or installed RCC child proof. The
failed and passing logs are retained in Library archive
`libfile_b1e3d498c26c8191b3f02281a7f5d57f`, version 10.

A reviewed completion supplied a concrete counterexample to queue publication
isolation: an authorized input ItemView included the ID of a child in its
unpublished `_output` queue. The model projection at
`a5da58bc` omits parent/child IDs because ItemView does not identify their
queues; domain and REST views remain unchanged. The focused suite passed 15
cases with seven skips, including the SQLite/DuckDB reviewed-output regression.
The first attempt stopped at missing provider fixture setup. This result does
not establish PostgreSQL behavior.

The persisted delegation schema and aligned value passed 36 combined cases.
Deploy-time target checks at `c46572c6` passed five SQLite cases with five
PostgreSQL skips using a registry-shaped test double; real installed registry
provenance remains unverified. Existing Deployment service regressions passed
26 cases with 25 skips. The first target-check attempt failed setup because its
database-location fixture was not registered. All test supervisors reported
no owned processes remaining. Raw passing and failed logs are retained in
Library archive `libfile_b1e3d498c26c8191b3f02281a7f5d57f`; the final archive
version for these checks must be recorded when uploaded.
