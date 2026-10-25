# Owned PostgreSQL historical migration qualification

Production source remains da928b69; corrected tests are commit be716ebc.
That correction commit is unchanged. This receipt closes its explicit PostgreSQL
skip only; it does not imply other service, installed or full Runtime gates pass.

Prepared RCC 18.19.3/Poetry 2.1.1 ran `controller.py` from `action_server`, with
owned Poetry/XDG caches. The controller uses the canonical fixture contract
`ACTIONS_INVOICE_TEST_POSTGRES` and `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1`, so a
missing listener cannot silently skip. It invokes:

```
poetry run pytest -p no:robocorp_log_pytest tests/action_server_tests/test_task_clock_migration.py -q -rs --junitxml=<owned>/tests.xml
```

Result: **2 passed, zero skipped**, SQLite and actual PostgreSQL. Both preserve
the archived v20 source/DDL and data, verify v21 behavior, then upgrade through
current schema and recheck retained data. Existing full fresh-schema parity is
SQLite-only, as before; this result does not add a PostgreSQL parity claim.

The repository-pinned image was fetched by immutable digest:
`postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81`.
The owned container uses `--pull=never`, 768 MiB memory, 1 CPU, 128 PIDs,
512 MiB data tmpfs, and a random port bound only to 127.0.0.1. The credential is
synthetic and local. Readiness was checked with a deadline. Fixture schemas and
the exact owned container were removed; cleanup returned zero. No network policy,
production credential, migration or version changes were made. No host fallback.

Documentation proposal to integrator: amend the earlier correction receipt's
uncertainty to record this real PostgreSQL pass while retaining the explicit
SQLite-only fresh-schema parity boundary. In the canonical guide, retain the
rule that required provider qualification sets `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1`
and supplies an owned live fixture; a skipped parameter is not provider proof.
Evidence: controller, exact invocation/limits in receipt, JUnit, stdout.
Uncertainty: broader PostgreSQL release/recovery and installed-binary behavior.
Upstream disposition: none.

## Next bounded scope proposal (not implemented)

Proposed sole new implementation path:
`action_server/scripts/qualify_installed_artifact_http_327.py`, plus evidence below
this lane directory. No edits to production transport/auth/routes, shared tests,
fixture SQL, version metadata or release configuration are requested.

Use the current rebuilt wheel in a fresh consumer with declared locked dependencies;
verify installed module origins/bytes and run the assembled Runtime on a real
loopback socket. Reuse existing service/control-plane APIs to seed one synthetic
owned output and persisted grants, not parallel schemas. Check authorized GET,
installation-key-only rejection, wrong Actor credential, wrong workspace, and
revoked persisted grant, including before-provider denial and no logical state
mutation. Stop the owned process and retain stdout/JUnit or equivalent per-case
receipts. Bound data and process lifetime; preserve every failed attempt.

The server-owned synthetic credential verifier is explicitly a test trust carrier,
not production OAuth/authenticated ChatGPT proof. This gate would close the
installed-wheel + actual HTTP transport gap in the existing `TestClient` suite,
not implement a new login protocol or qualify full artifact HTTP features.
If ordinary installed startup cannot inject the existing trusted transport without
production changes, stop at that concrete blocker and request exact ownership.
No shared code change is authorized by this proposal.
