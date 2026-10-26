# Owned Core and Robot source checkpoint — installed acceptance pending

The source checkpoint containing this receipt introduces Core 1.1.0a6 and Runtime 1.1.0a43. No a43 wheel or installed acceptance is claimed here. Frozen a41 remains FAILED; a42 direct protocol acceptance remains PASS and official basic-host browser acceptance remains BLOCKED. The exact a42 obtainable bundle and supported browser recipe remain in ../browser-handoff/README.md.

| Gate | Result and limit |
| --- | --- |
| Generated installed a42 | PASS: public authoring, actual RCC, authorized success/failure artifacts, restart and rollback; separate from UI host |
| Official host browser | BLOCKED: supported Chromium sandbox startup fails; no security override used |
| Owned Core source | PASS: 448 tests with isolated official truststore selector; logging/redaction and attributed viewer migration; configured lint/type checks |
| Native TLS | PASS: seven isolated Linux checks, one official namespace provider; Windows/macOS unverified |
| Robot receipt/Task join | PASS: 421 joined SQLite/PostgreSQL tests without skips; latest nine public SQLite tests pass; installed a43 pending |
| Claimed Robot Work Items | OPEN: admission, lease renewal and atomic completion still needed |
| Templates / consumer inventory | PASS: 24 tests; embedded basic scaffold rebuilt with Core a6 and no browser dependency |
| Owned docs adapter | PASS: 333 devutils tests and byte-identical 11-file API generation comparison; Core validation retains 13 pre-existing style failures |
| Full Runtime | INCOMPLETE: interrupted after 3 failed, 290 passed, 9 skipped; all three causes corrected and focused gates pass; full rerun required |
| Independent clients / Dakota | OPEN: no owner-launched Dakota dispatch or external publication |

Runtime full-suite failures were the expanded universal Canvas resource inventory and two retained Core 1.0.2 preload imports. Exact resource inventory expectations now include Canvas. Legacy preload selection only occurs when the owned logger module is absent; internal owned import errors propagate. Three compatibility tests and both actual retained-child showcase gates pass. The type checker requires an explicit optional-import annotation because the current consumer intentionally does not install that legacy distribution.

Robot cleanup now verifies owned process groups and signals before every descendant snapshot. Public admission selects Robot receipt versions, strict SQL-only retained validation precedes artifact resolution even with zero logical requirements, and Task cancellation/activation/preparation guards remain. Independent final review found no confirmed blocker; this does not qualify claimed Work Items or installed execution.

Dependency closure preserves Apache/MIT attribution, logging semantics, secret constructor exclusions and bytecode cache independence. Core uses official truststore; Runtime/Core no longer declare the retired logging or truststore distributions. Current active development locks replace Git documentation forks with the attributed owned adapter and official checker. Retired orphan locks are historical, not active packages. Scaffold and default endpoint corrections preserve explicit compatibility choices. Clean installed namespace/RECORD verification is still required for a43.

All helper documentation proposals are incorporated in docs/skills/repository-operations.md: owned logging and redaction, namespace collision verification, process ownership, Robot public receipt joins, explicit endpoint/acquisition behavior, owned documentation discovery and legacy child preload boundaries. Work Item proposal remains a plan, not implemented guidance. No helper report is treated as installed qualification.

Next exact engineering gate: build clean committed-source a43/Core a6 wheels, install under the refreshed lock, verify retired distributions absent and exact wheel members, then execute public generated and Robot success/failure through genuine RCC with target-local preparation. Full Runtime and official sandboxed browser remain separate gates.

Upstream disposition: none. No external repository, publication or deployment mutation.
