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
