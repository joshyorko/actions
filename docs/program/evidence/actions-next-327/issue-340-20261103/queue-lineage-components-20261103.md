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
