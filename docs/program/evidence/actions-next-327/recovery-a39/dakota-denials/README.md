# Frozen a39 installed HTTP denial gate

All five required observations are retained: correct bearer initialize 200; missing bearer 403; wrong bearer 403; authenticated foreign Host 421; authenticated foreign Origin 403. Bodies and exact sanitized request/launch arguments are in the receipts. MCP initialize used protocol 2025-11-25 on /mcp with Accept application/json, text/event-stream.

Runtime/Core/WorkItems wheel hashes match frozen a5eaa1cb clean-e2e identity. All 400 non-metadata installed wheel package files were byte-compared (319 Runtime, 55 Core, 26 Work Items). Import origin is the frozen consumer. No source package override, new dependency, RCC build/job, guard override, tunnel, public listener or existing datadir was used.

The first harness assumed missing bearer would return401; it observed403 and exited. Preserve that failed assertion. The continuation selected only the remaining three cases against a second fresh owned loopback datadir. Both servers terminated without forced kill and logged completed lifespan shutdown. Aggregate observations satisfy the denial gate; no retroactive initial-harness PASS.

Commands executed:

```sh
/workspace/actions-327-a39/installed-combined/consumer/bin/python /workspace/a39-denial-gate/verify.py
/workspace/actions-327-a39/installed-combined/consumer/bin/python /workspace/a39-denial-gate/remaining/verify.py
```

Drivers generate fresh synthetic bearer in memory and pass it only to their owned server/request. Delivered files contain no bearer, headers carrying bearer values, private datadir or server logs. Reproduction must use fresh directories: scripts refuse existing evidence directories. Initial driver intentionally retains its original401 expectation. Use documented observed403 for future harnesses.

This closes cloud HTTP denial observations only. Dakota still requires actual installed ChatGPT Desktop connection/MCP Apps support verification, compatible Host/Origin headers, screenshots, and scoped temporary setup cleanup preserving Executor. No READY or actual-host claim.

Upstream disposition: none. No confirmed upstream defect; initial401 expectation was a harness assumption.

Integrator evidence guard rejected the credential-like JSON field name authorization even though values were synthetic test labels only. Published receipts use credential_case; no guard relaxation or token transfer occurred. The original helper delivery stays local; root hashes describe the published sanitized representation.
