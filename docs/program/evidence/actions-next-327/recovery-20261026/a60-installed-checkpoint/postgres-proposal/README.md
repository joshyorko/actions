# Corrected PostgreSQL sealed-scan proposal

Status: **proposal only and not approval-ready under a strict all-path cleanup
requirement; no PostgreSQL or Docker setup action was run**. This document
describes one bounded qualification run for review and does not request or
authorize execution. The image-side timeout applet is present, but its exact
option behavior is not verified; more fundamentally, the task-owned internal
Docker network has no autonomous TTL/removal. A host crash or Docker daemon
outage prevents a guarantee that both container and network absence will be
verified on every path. If all-path verified network removal is mandatory,
the proposal remains blocked.

## Purpose and boundary

If separately approved, exercise only the installed `PostgreSQLSealedScan`
component against the existing task-owned synthetic sealed CSV and Parquet
objects, then compare its typed two-row results with the already retained
`DuckDBSealedScan` results. This is a component check for the PostgreSQL
engine-read path. It does not qualify Package/capability binding, admission,
Run/Attempt execution, workers, paging/export/cost, expiry, or the overall Data
row. Do not read a full row or package, or send data to an external service.

## Target and runtime envelope

The only permitted image target in this proposal is the already-present exact
image `postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81`
(observed image ID `sha256:319d040b5d68e3e5b98a238f0b5d375b4b4d9c5b3a6a9afb0308a8bcf0de72a5`).
Any future run must use explicit `--pull=never`; a missing or mismatched image
is a stop condition. No tag resolution or pull is in scope.

The scan client is the installed host-side PostgreSQL adapter. It requires
TLS `verify-full`, and the existing owned fixture binds its listener on
`127.0.0.1` with an ephemeral host port. Therefore `--network=none` is not an
acceptable substitute: it does not provide the required host TCP/TLS path.
Propose one task-unique user-defined Docker bridge network created with
`--driver bridge --internal --label actions.owner=<unique-task-id>` and no
static subnet, aliases, or additional attached containers. Attach the one
task-owned container to it and publish only `127.0.0.1::5432`. The internal
bridge is intended to block container egress while the host reaches the
loopback-published TLS endpoint; this host-to-published-port behavior has not
been exercised here. Under any later approval, failure to connect with the
adapter's unchanged `verify-full` settings is a stop condition. Do not switch
to the default bridge, host networking, a wildcard bind, or weaker TLS to make
the test pass. Network creation/removal and the published loopback port must be
named in the approval because they are mutations.

Use a unique container name and ownership label, `--rm`, `--restart=no`,
`--read-only`, `--memory=256m`, `--cpus=1`, `--pids-limit=64`,
`--stop-timeout=5`, a 64 MiB tmpfs for `/var/lib/postgresql/data`, and a
16 MiB `noexec,nosuid` tmpfs each for `/tmp` and `/var/run/postgresql`. No
persistent volume is allowed. Candidate watchdog design: put the image's
existing `/usr/bin/timeout` BusyBox applet at PID 1 as the outer command, with
a 180-second duration, a TERM timeout signal, and a 5-second KILL grace; it
would supervise the existing `docker-entrypoint.sh postgres` command. Confirm
the exact BusyBox option syntax against the pinned image before assembling an
approved launch. If the watchdog exits immediately or its syntax is
unsupported, stop before database setup. Configure `--rm` so Docker removes
the container when PID 1 exits. This could bound container lifetime after
host-supervisor `SIGKILL` while Docker remains operational, but neither the
watchdog behavior nor resulting container removal has been exercised here;
the later run must verify both.
Mount only the synthetic input objects and one private task-local TLS
directory read-only. Keep all new durable proposal/evidence files under this
proposal directory and below 5 MiB total. Generated certificate/password
material belongs only to a later approved, private temporary run directory;
it must be mode-restricted, removed in cleanup, and never copied into this
proposal or a report.

## Explicit credential and database-security scope

A future approval must explicitly include all of the following setup changes;
the earlier rejection remains in force until such approval is granted:

* Generate a fresh one-run bootstrap administrator password and a distinct
  fresh `scan_reader` password only during the approved run. Do not reuse any
  existing test, application, or operator credential. Keep values in memory
  and a private temporary file only as required by the pinned image entrypoint
  and local secret resolver. Never print, log, put them in argv, retain them in
  receipts, or include them in approval/report text. Do not emit unfiltered
  `docker inspect` output that may contain environment values.
* Generate a private one-run local CA and server key/certificate for
  `verify-full`, with server SANs `DNS:localhost` and `IP:127.0.0.1`,
  `serverAuth` use, and a one-day validity. Keep the CA private key and server
  key in the mode-0700 temporary directory with mode-0600 key files; mount the
  server cert/key read-only into the container, copy only those files into
  container tmpfs for PostgreSQL, and give the CA certificate to the host
  resolver. Do not make or use a client certificate. Remove all key material
  during verified cleanup. No certificate was generated for this proposal.
* Create one task database named `sealed_scan`; its owner remains the bootstrap
  administrator. Create one login `scan_reader` with `NOSUPERUSER NOCREATEDB
  NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT CONNECTION LIMIT 1` and a
  generated `VALID UNTIL` set to five minutes after the approved run's start.
  `VALID UNTIL` prevents later password authentication after expiry; it does
  not revoke an already-open session, so the operation timeout and container
  cleanup remain necessary.
* Revoke all database privileges on `sealed_scan` from `PUBLIC`, grant only
  `CONNECT` on that database to `scan_reader`, and revoke all privileges on
  schema `public` from `PUBLIC` and `scan_reader`. Grant no table, sequence,
  function, temporary-table, or schema-creation privileges. The adapter sends
  typed `VALUES` batches, sets `search_path=pg_catalog`, and does not need
  `SELECT` grants on user tables.
* Set `scan_reader`'s `temp_file_limit=0` and
  `default_transaction_read_only=on`. The adapter also begins a read-only
  transaction and sets bounded query/lock deadlines. After bootstrap, disable
  future password login for the bootstrap administrator (`ALTER ROLE postgres
  NOLOGIN`) and close its setup connection. These are explicit SQL security
  changes, not implicit fixture details.

The exact SQL scope, in conceptual parameterized form, is: create the database;
create the role with the attributes, generated password, connection limit, and
expiry above; revoke database/schema `PUBLIC` privileges; grant only database
`CONNECT`; set the two role defaults; disable bootstrap administrator login;
close the setup session. There are no package-provided SQL files to execute and
no request for broadening this scope. Any required change beyond these listed
operations needs separate review.

The exact image's entrypoint supports the generic `POSTGRES_PASSWORD_FILE`
path: it defines `file_env()` for `${VAR}_FILE` and calls
`file_env 'POSTGRES_PASSWORD'`. This was established by read-only inspection of
the final OCI layer, without executing the image. The internal-bridge
host-to-published-port path has not been validated. If it is unavailable under
the exact Docker daemon, stop and return the capability gap; do not substitute
a weaker transport.

## Supervision and cleanup contract

A future approved host supervisor must impose a 180-second wall-clock limit,
handle ordinary exit, timeout, `SIGINT`, and `SIGTERM`, and run cleanup from a
`finally` path. Record the exact created container/network IDs and unique
ownership labels. Cleanup may stop/remove only an object whose ID and ownership
label both match this run. With `--rm`, normal container exit should remove the
container; the finalizer must still query the exact object, distinguish
“already absent” from Docker/API failure, request stop then forced removal if
needed, and verify absence. Before removing the dedicated network, verify its
ownership label and that no container remains attached; then remove it and
verify absence. Any failed verification is a cleanup failure, not a clean
receipt.

For host-process `SIGKILL`, the in-image PID 1 watchdog plus `--rm` is the
candidate container-lifetime bound if the BusyBox invocation behaves as
expected and Docker remains operational. This runtime behavior remains
unverified. It does not autonomously remove the dedicated Docker network. A
host crash or Docker daemon failure can interrupt the watchdog or leave
container state uncertain; network removal after host death is not
guaranteed. On every handled host exit, still perform the ownership- and
ID-checked container and network removal described above. The five-minute
role password expiry rejects later password authentication but does not
terminate an existing session. Report any failed absence check as cleanup
failure.

Read-only streaming of the exact existing OCI image confirmed an executable
`/usr/local/bin/docker-entrypoint.sh` in manifest layer 9; its `file_env()`
supports `${VAR}_FILE` and is called for `POSTGRES_PASSWORD`. The same final
filesystem has `/usr/bin/timeout` linked to executable `/bin/busybox`, whose
static bytes include the `timeout` applet name. No image code was executed.
Exact BusyBox option syntax and runtime timeout/`--rm` behavior remain a
prelaunch verification item; do not claim those as observed qualification.
The bounded in-memory OCI read followed the index to manifest
`sha256:867997d7d24be56008cd3c6dd58f5246915557dd7ab615b5f4cf5444792e59f6`,
whose config digest is the inspected image ID
`sha256:319d040b5d68e3e5b98a238f0b5d375b4b4d9c5b3a6a9afb0308a8bcf0de72a5`;
it streamed 11 layers (294,926,848 archive bytes; 292,095,173 layer-member
bytes) without writing the image archive or extracting paths to disk.

## Stop conditions and evidence status

Stop before any setup action if image identity differs/is absent, network
creation is not explicitly approved, internal-network loopback publishing
cannot preserve `verify-full`, the private credential transport is not
supported, limits prevent initialization, or any cleanup check fails. Do not
retry the denied command, generate credentials/certificates, create the
network/container/database/role, or run SQL as part of proposal review.

Evidence available now is limited to the retained denial receipt, installed
source and test contracts, the existing DuckDB component receipt, Docker CLI
help, and read-only metadata for the pinned local image. There is no PostgreSQL
execution result, successful TLS connection, network compatibility result,
credential-transport result, or cleanup test in this proposal.

## Exact canonical-guide delta proposed

Propose adding the following paragraph to
`actions/docs/skills/repository-operations.md` under “Strict retained-source
DuckDB scan component”, immediately before “Actual owned TLS fixture
qualification”:

> A local PostgreSQL fixture start is a separately scoped mutation even when
> its image is digest-pinned and its port is loopback-only. Approval must name
> generated bootstrap/reader credentials, database role attributes and
> `VALID UNTIL`, database/schema revocations and grants, role limits, exact
> image with pull policy, network mode and published bind, mounts/resource
> bounds, and ownership-checked cleanup. A host-installed `verify-full` TLS
> client requires a reachable TCP endpoint; `--network=none` does not establish
> that path. An internal bridge plus loopback-published port is a candidate
> isolation design whose reachability must be verified under approved scope;
> do not silently fall back to default/host networking or weaken TLS. A host
> finalizer handles only exits it can run for. A pre-existing image-side
> watchdog plus `--rm` can bound a container after host-process death only
> while Docker remains operational; it cannot autonomously remove the host's
> task network. Demonstrate the watchdog in the exact pinned image before
> claiming this coverage. Password expiry blocks future authentication but
> does not close existing sessions. Report cleanup limits explicitly.

This is proposed documentation, not an applied canonical-guide edit. The
existing source test proves the adapter fixture's `verify-full` loopback
configuration and connect-only privilege assertions; Docker CLI help lists
network/publish/pull controls; bounded streaming inspection of the preexisting
pinned OCI image proves the password-file entrypoint path and static timeout
applet presence. The denied action proves that role/password/grant and
security-setting changes require explicit scope. None of this verifies
internal-bridge reachability, BusyBox timeout runtime behavior, container
auto-removal, or network cleanup after host death.

Upstream disposition: none.
