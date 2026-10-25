# Installed a51 claimed Task evidence

Source `ea3448e2b40741c5a21369c24cc20e84b8258809`, Runtime1.1.0a51/Core1.1.0a8. Target-local compiler artifact `sha256:0a0e5fee81bc3d747aa685d634880e94e344643e942a70733b4280af6d89a8a7`. This directory copies only bounded sanitized receipts; no credentials, configs, datadirs, raw artifacts or server logs. `hashes.json` binds copied bytes to original evidence paths. Producer paths are provenance, not portable download locations.

| Gate | Observed result |
| --- | --- |
| Installed public claimed Task success | PASS: Task completed/isError=false, queue DONE, actual RCC exit0, four authorized artifacts. |
| Installed public claimed Task deliberate failure | PASS: Task completed/isError=true, business state failed, queue FAILED, actual RCC exit1, four authorized diagnostic artifacts. |
| Replay/restart | PASS: exact retained Task/queue/Run/artifact reads, counts2Runs/2Attempts/2intents/2Taskreceipts unchanged after restart. |
| Terminal cleanup | PASS: four graceful Runtime stops; both execution receipts no live/zombie descendants/errors; enclosing supervisor PASS. |
| First live-cancel trial | FAILED during launch observation; cancellation NOT_RUN. Nested TimeoutError retained. Runtime-stop assertion also failed due separate shutdown metadata race. Outer supervisor cleanup must not turn inner failure into PASS. |
| RCC-only cwd probe | PASS at narrow probe scope: wrapper cwd was launch source; Python cwd was compiler holotree materialization; same process group. Supervisor PASS/no descendants. Not Task/cancellation acceptance. |
| Observer v2 | SOURCE_REVIEW_CLEAR, actual execution NOT_RUN at evidence assembly. Inert tests reported4passed, not rerun by this lane. |

The first live observer required Python cwd equal source, so the actual RCC cwd observation explains why that predicate could not find the observed execution. Do not relax matching to arbitrary Python processes: the reviewed replacement requires exact Runtime ancestry, wrapper executable hash/source launch identity, Python executable identity and prepared materialization, PID birth identity and shared process group, with bounded timing. Source-review hash `31346584e411451798f198d0fc68eebeaa01e66c8ab981fcc05d031aa5d34303` is retained in observer-v2-source-review.json. A subsequent v2 trial requires its own receipt and must not overwrite the first failure.

Observed Task completion is distinct from business success. None of these receipts qualifies two-principal isolation, terminal live cancellation, browser/ChatGPT, producer/child outputs, whole-release readiness or the still separate a50 failure. Read-only SQL counts are instrumentation; public authoring/claim/invoke/artifact APIs establish the installed path.

## Canonical proposal

Append to docs/skills/provenance-observability.md: “RCC may preserve its wrapper's launch-source cwd while executing Python from a holotree materialization. A live-execution observer must bind exact launch/Run/Attempt identity to verified wrapper and Python executable, PID birth identity, ancestry and process group; cwd equality alone is insufficient. A failed launch observer leaves cancellation NOT_RUN. Keep a narrow RCC observation probe, inert observer review and actual installed cancellation receipts separate.”

Documentation improvement: this evidence directory records actual installed terminal success/failure and retained first observer failure; proposed canonical delta replaces the incorrect same-cwd assumption. Evidence is the copied cwd observation and terminal/failure receipts. Remaining uncertainty: actual observer-v2 trial, resulting cancellation lifecycle and next-candidate shutdown correction. No execution/services performed while assembling evidence. Upstream disposition: none; owned observer and shutdown integration issues, no authorized external mutation.
