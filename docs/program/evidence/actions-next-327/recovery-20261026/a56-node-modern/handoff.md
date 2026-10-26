# a56 Node modern-auto synchronous claimed generic gate

Disposition: PASS for this candidate and operation profile. This is one unmodified-installed a56 run; it does not explain or supersede the earlier a53 `modern-auto` denial, and it does not qualify legacy/default negotiation or detached Task mode.

## Exact candidate and setup

- Runtime wheel: `actions_runtime-1.1.0a56-cp312-cp312-linux_x86_64.whl`, SHA-256 `f06526ab99c8df7a769a03c67efb771f0bdcf4fbeb00caa74afc85b0c035f046`; clean consumer reports runtime `1.1.0a56`, Core `1.1.0a8`, Work Items `0.5.0a2`. Companion wheel hashes are in `receipt.json`.
- Source checkout: commit `88846b55e3b455eb44378bd5ba43bb146706661d`, tree `a65449200ec36981b6ad4002147f19cf8da8a265`.
- Prepared RCC artifact digest: `sha256:ab46f17f4b1ec8d620a3111ad103eff36f78515df5b4db88d1739f5b1e0a6a24`; RCC 18.19.3.
- Node `v20.19.3`, SDK `@modelcontextprotocol/client 2.0.0`, Undici `6.21.2`; SDK entry hash `af3ec9fcf3a70fb4681e9b3c11aa18a7ce9aca36fed9f138a6e704043695d414`, type hash `309cc5f76da5abff0be678d958aba0e875e52909f5f6f0544a45a34ac596cc9c`.
- The task-local copy retained the exact source profile (SHA-256 `883eccd1c2b234311a9442fbcb53c2341a4255bef1b7cacf7c7458cb6634051f`) and byte-identical saved pass/fail Canvas fixtures. Workspace is `35264a6f-41e5-459a-8b7f-79ff3c9a7289`; pass/fail apps and deployment revisions are recorded in `sync-pass.json` and `sync-fail.json`. Source fixture and synthetic grants/profile were unchanged. Task-local `ACTIONS_HOME`, `ROBOTS_HOME`, datadir and empty cwd; loopback HTTP; same `http://localhost:8080` CORS origin; no auth/grant/origin changes.
- Disk preflight: 19,358,085,120 bytes free (>10 GiB).

## Result

The direct SDK client auto-negotiated protocol `2026-07-28`, listed both tools, and successfully called `canvas_get` for both saved apps. The synchronous generic claimed Robot pass completed with item `DONE`; fail completed with item `FAILED`. Both cases replayed enqueue idempotently, claimed the exact item, passed terminal receipt/claim/cleanup/publication-fence assertions, and returned four authorized artifacts (`robot-stdout.log`, `robot-stderr.log`, `robot-output.xml`, `rcc-receipt.json`) whose sizes/digests were verified. Robot XML was parsed by Python `xml.etree.ElementTree`; one `Selected` test had `PASS`, the other `FAIL` with the expected synthetic failure reason. The runtime then stopped gracefully and restarted on the same task-local datadir; all four artifacts, run and item for each case were read and compared unchanged. Both Node phases logged client close, transport close and `beforeExit` code 0, and exited naturally.

The outer pidfd supervisor returned exit 0 after 82.2 seconds, with `remaining_owned: []` and `adoptees_reaped: []`. Full receipts, sanitized stage logs, runtime logs, controller, client, Robot XML and case receipts are retained in this directory. The test-only instrumentation delta from the earlier diagnostic client was removal of `async_hooks/createHook`, custom `Promise.race` deadlines and custom SDK fetch wrapper; this client used direct SDK methods with SDK timeout options and Node's native `fetch`. No auth or server code was instrumented or altered.

## Comparison and limits

The original `/workspace/327-probes/node-generated-luna/modern-auto` harness used the same saved pass/fail fixtures and copied profile identity, but targeted the a53 installed consumer and its earlier diagnostic Node client. This gate targets the separately installed a56 candidate and removes client-side tracing/deadline/fetch wrappers. Both candidate version and instrumentation therefore differ; the success demonstrates the a56 profile works, but cannot identify why the earlier a53 boundary returned a tool error. No further attempt is authorized in this lane.

## Documentation improvement proposal

Canonical file: `docs/skills/repository-operations.md`.

Proposed exact durable delta, adjacent to the existing Node qualification notes:

> A candidate-specific installed Node execution qualification can close only its recorded client/profile row when the locked SDK is run unmodified with its stated negotiation mode and native transport, both synchronous generic pass and fail reach terminal claimed Robot states, all four authorized artifacts are digest-checked, strict Robot XML status is parsed, and run/item/artifacts remain readable after a graceful runtime restart. Record SDK/runtime/source pins and natural client/transport exit separately. This result does not qualify another Runtime candidate, legacy/default negotiation or detached Task mode, and does not explain an earlier failure under a different candidate or diagnostic harness.

Evidence: `receipt.json`, `supervisor-receipt.json`, `node-execute.jsonl`, `node-restart.jsonl`, both `sync-*.json`, and both Robot XML outputs in this directory. This is durable acceptance-boundary guidance, not a run diary. No stale guidance is removed; existing text that says diagnostic wrappers do not qualify uninstrumented execution remains correct.

Upstream disposition: none. The probe found no verified upstream defect; the earlier denial remains un-attributed.
