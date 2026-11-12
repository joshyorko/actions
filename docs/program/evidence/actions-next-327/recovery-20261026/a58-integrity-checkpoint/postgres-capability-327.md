# Docker server OS preflight for the owned TLS PostgreSQL fixture

## Finding and correction

The hosted Windows run recorded 151 failures and 16 errors, including this
owned TLS PostgreSQL fixture. The fixture launches a pinned Linux PostgreSQL
image, but its old admission check proved only that `docker` was on `PATH`; a
Windows Docker Engine was admitted and failed later in `openssl`/container setup.

The fixture now performs `docker info --format '{{.OSType}}'` with a 10-second
timeout before importing the client, making private TLS files, or launching a
container. It admits only a well-formed `linux` server response. Missing CLI,
failed/timed-out engine query, and malformed or non-Linux responses skip in
ordinary mode; `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1` fails each capability
refusal. Once Linux capability is established, setup and actual TLS/provider
failures still propagate as test failures. Product adapter behavior, auth, TLS,
pinned image and provider semantics were not changed.

## Regression and verification evidence

Red context: the captured hosted Windows failure above demonstrates why CLI-only
admission is insufficient. The current environment is Linux, so the Windows
hosted failure was not re-run locally.

Green: all nine cases passed twice in
`test_sealed_postgres_capability_327.py`, first with the strict-provider variable
unset and again with inherited `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1`. Ordinary
refusal tests explicitly clear the inherited strict flag; explicit strict cases
continue to assert failure. Coverage includes Linux admission,
Windows and unavailable/malformed engine responses, strict-mode failures,
missing Docker CLI, timeout, and `OSError`. Refusal cases invoke the actual
fixture and assert its temp-directory factory is untouched and the only process
command is the read-only Docker info preflight. The invocation verifies the
10-second timeout and exact Docker command.

Command, run through RCC 18.19.3 `task script` and the bounded process
supervisor:

```text
/workspace/actions-cloud/bin/rcc task script -r developer/toolkit.yaml -- python /tmp/run_postgres_capability_tests.py
```

The script ran the focused pytest file (9 passed in each mode), Ruff using
`/workspace/actions/devutils/ruff.toml` (passed), and package Isort check (passed).
The supervisor receipt reports `PASS`, command exit 0, no remaining owned
processes, and no adopted children. The separate actual TLS provider suite was
not rerun; existing Linux actual-TLS qualification remains distinct from this
capability-only regression. Full suite and aggregate gates were not run.

## Canonical guide proposal

Proposed exact addition to `actions/docs/skills/repository-operations.md` in
the owned TLS fixture paragraph:

> Before generating TLS files or launching its pinned Linux PostgreSQL image,
> the owned TLS fixture checks the connected Docker Engine with the bounded,
> read-only `docker info --format '{{.OSType}}'` query. Docker CLI presence does
> not establish the server OS. Ordinary optional runs skip when the query is
> unavailable or the server is not Linux; `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1`
> fails instead. After Linux capability is established, actual setup and
> provider failures remain failures.

Evidence is the fixture preflight and its nine passing capability regressions,
including strict-mode and no-downstream-side-effect assertions. The guide itself
was not edited because this lane's assigned write scope is limited to the two
test files and this evidence report; the parent can integrate the exact delta.

Upstream disposition: none. This is a local test-fixture capability admission
correction; no upstream defect was established.

## Documentation improvement receipt

- Canonical file changed or proposed: proposed exact delta for `actions/docs/skills/repository-operations.md` above.
- Durable learning captured: Docker CLI availability does not prove that the connected Engine can run the fixture's Linux image; query the server OS before TLS material or container setup.
- Evidence: hosted Windows fixture failures and nine focused regression cases through the prepared RCC environment.
- Stale or ambiguous guidance removed: proposed language clarifies the earlier qualification statement that described actual owned TLS coverage without its Docker Engine platform prerequisite.
- Remaining uncertainty: the failed Windows hosted run was not rerun locally; the focused tests simulate Engine responses, while Linux actual-TLS qualification is pre-existing evidence.
