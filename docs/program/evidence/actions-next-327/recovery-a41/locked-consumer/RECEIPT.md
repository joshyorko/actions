# Frozen-lock installed consumer qualification

Outcome: PASS for dependency closure, installed identity/member bytes and basic
MCP compatibility. This is not vendor-independent, SBOM-graph, full Canvas,
current Task-protocol, provider execution or installed-recovery qualification.

Consumer: `/workspace/actions-327-a41/locked-consumer`.
Existing `/workspace/actions-327-a41/installed-v2/consumer` and its evidence were
preserved. No source edits, commits, pushes, lock upgrades, cache deletion, root
package installs, optional Runtime extras or RCC environment publication occurred.

## Exact inputs

Frozen source: `f905c3888ecb448dbce80ce57a9b59ff041eb148`.
Frozen Runtime lock was byte-compared to that commit's `action_server/poetry.lock`:
SHA-256 `62da89cf1c47f2aaa2c3f1b6545e300775ec70d7396f4d5d348c3e9a2d006588`.
Constraints exactly matched 70 unique main-group normalized names/versions:
SHA-256 `f6b5c33159199d4ee16863b3b156543d93792244d9e208976f7c639929042ca4`.
Both raw files are retained here.

Exact existing wheels, verified against installed-v2/evidence/wheels.json:

- Runtime 1.1.0a41: `fcf70e1f1cc3b91409dd8600622161085281f968b868373d5b62df10e0c4a661`.
- Core 1.1.0a5: `0c1421f7b7cd0db447c82e58458107c92f22051b29eb128c8b765219b863a3ec`.
- Work Items 0.5.0a2: `72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb`.

## Installation and resource evidence

Used the prepared RCC toolkit Python to create only the new venv, then installed
those three wheels with `pip install --no-cache-dir -c <verified constraints>
--report <owned report>`. The supervisor enforced a 6.5GiB starting reserve,
5.5GiB live floor, 12MiB log bound and 600-second deadline.

Install completed in 58.306 seconds; starting free space 7,785,250,816 bytes,
minimum observed 7,608,123,392 bytes, final 7,630,815,232 bytes. No limits triggered.
`pip check`: No broken requirements found. Raw pip install report and local inspect
are retained; no optional Runtime extras were requested.

## Qualification

Called `qualify_consumer_inventory_327.qualify(inspect, frozen_lock, '1.1.0a41', [])`
in prepared Poetry tooling. The exact qualifier snapshot SHA-256 is
`ab5da82fdacd91a930b4245ebdc5cc2cfa1322643bafc1b002c79a9a136fc6e4`.
It accepted **66 active distributions**, with pip alone excluded as bootstrap.
Transitive declared extras were `psycopg[binary]` and `pyjwt[crypto]`; Runtime
extras remained empty. MCP and mcp-types are both exactly **2.0.0**.

Installed wheel byte equality passed for **328 Runtime**, **58 Core**, and **29
Work Items** members. These counts include metadata; only pip-rewritten RECORD
was excluded. Every member path resolved under the new consumer. Imports of
`actions.server`, `actions`, `actions.work_items`, and `mcp` likewise resolved
under the new consumer, with Python isolated mode and no source overlay.

CLI `action-server version` returned `1.1.0a41`. The initial incorrect invocation
`action-server --version` returned exit 2; its log, first qualification receipt and
first hash manifest are preserved, and the corrected subcommand has a separate
log. No dependency or source change was made to correct this command syntax.

An actual installed Runtime `McpServerSetupHelper` and installed MCP 2.0.0 client
completed in-process ASGI `initialize`, negotiating **2025-11-25**, and returned an
empty tool catalog. No network listener, credentials, native Canvas database,
workload, RCC execution or job scheduler was started. Raw initialize response is
retained in `mcp-initialize.json`.

Final compact receipt: `qualification.json`, SHA-256
`5830b6048c596a4fd69078b5cdbbf849833675deec9fa4db7794dcce229d050f`.
All raw evidence and execution harness hashes are in `SHA256SUMS.json`.

## Documentation and remaining scope

Upstream disposition: none.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Exact delta: documentation-delta.md / documentation-PROPOSAL.patch (patch check
  and whitespace check passed against root without applying it).
- Durable learning: bind constraints to frozen candidate lock; constrain versions
  without requesting inactive/optional packages; qualify active graph separately
  from pip check; keep qualifier tooling outside consumer; distinguish full-wheel
  member counts and CLI version subcommand; keep basic MCP smoke evidence scoped.
- Evidence: inputs.json, install-supervisor.json, dependency-closure.json,
  installed-bytes.json, cli-version-subcommand.log and mcp-initialize.json.
- Stale/ambiguous guidance removed: no paragraph removed; proposed durable guard
  against using earlier handoff constraints for a new frozen candidate.
- Remaining uncertainty: no independently generated CycloneDX graph comparison,
  vendor-independence audit, full Canvas flow, current Task-protocol, provider job
  execution, installed recovery or release-wide acceptance was performed here.

No remaining blocker for this delegated dependency-closure task.
