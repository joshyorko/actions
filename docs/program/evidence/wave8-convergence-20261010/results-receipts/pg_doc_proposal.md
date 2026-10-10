# Proposed canonical guide delta: PostgreSQL failed-SAVEPOINT proof

Target: `docs/skills/repository-operations.md`, nested database transaction guidance around lines 98–104. This is a proposal only; source/docs are read-only for this task.

Suggested text to append:

> Keep the SQLite authorizer denial test and PostgreSQL transaction-abort behavior as separate cases. The SQLite authorizer can deny SAVEPOINT creation directly. For PostgreSQL, a failed statement inside an outer transaction leaves the server transaction aborted; a later nested `Database.transaction()` then attempts its generated SAVEPOINT and PostgreSQL returns SQLSTATE `25P02` (`InFailedSqlTransaction`). Let that error unwind the outer transaction, then assert the production nesting counter returns to zero, the connection is idle, the nested body did not run, and the same connection can subsequently commit an outer transaction containing both a rolled-back nested transaction and a committed nested transaction. Record the triggering SQLSTATE, SAVEPOINT error, server version, and same-connection recovery rows. This demonstrates cleanup after SAVEPOINT failure in an already-aborted transaction; it does not demonstrate a healthy-transaction privilege denial of SAVEPOINT.

Evidence: one bounded actual run against PostgreSQL 17.11 / psycopg 3.3.4 at source `1421fcf85c1b681aef1fe58fe2902f776f208167`, using production `Database.transaction()`. Division by zero produced SQLSTATE `22012`, then `savepoint savepoint_0;` failed with `25P02`; cleanup returned nesting to 0 and connection status to IDLE; same-connection recovery retained exactly `inner-committed` and `outer-kept`. The SQLite authorizer regression remains useful for an explicit admission-denial path and should not be presented as a PostgreSQL test.

Stale/ambiguous guidance to remove: none identified; this is a clarification of backend-specific fault injection.

Remaining uncertainty: the PostgreSQL failure is induced by an already-aborted transaction, not by rejecting SAVEPOINT in a healthy transaction. This run does not cover migrations, multiprocess startup, full CLI/server behavior, wheels, native packaging, or release acceptance.
