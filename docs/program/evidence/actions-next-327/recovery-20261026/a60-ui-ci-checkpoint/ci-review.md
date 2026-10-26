# Native/browser CI and MCP patch review

Reviewed the four requested files in `/workspace/actions` against `7b35422e30114a9a7561ab60b3f345990fe3ddb1`. This was a read-only review; no tests or artifact downloads were performed.

## Findings

No dependency error, validation/authority weakening, or new evidence-attribution issue found in this diff.

- The generator places the source-bound published-Core browser gate after frontend build, OAuth catalog generation, and explicit Playwright Chromium installation, but before Go wrapper/build, portable tests, and native integration tests. The checked-in generated workflow reflects that order. The source-clean assertion in `test_canvas_template_runs_through_runtime_and_real_browser` and source identity, runtime, browser, JUnit, and receipt checks are unchanged by the reviewed four-file diff. This is an ordering correction, not an acceptance relaxation (`.github/workflows/_gen_workflows.py:1089-1115`; generated YAML: `.github/workflows/actions_runtime_tests.yml:98-109,374-380`; admission controls in `developer/tests/test_canvas_published_workflow.py:39-48`).
- The added order controls require frontend/OAuth/browser preparation before the gate and gate-before-build/portable/native stages. The existing generated-workflow comparison still binds the YAML to the generator. This guards the source-bound measurement from later stages that may mutate tracked fixtures.
- MCP resource inventory now includes `ui://action-canvas/v1/canvas.html` only when the runtime platform is Linux, where the existing private provider is enabled; macOS and Windows require the custom resource only. Positive and negative helper cases cover missing/extra resources for the three CI platform identifiers. The live integration test continues to read both custom resource forms, assert custom tool/prompt behavior, and make missing/wrong bearer requests fail (`action_server/tests/action_server_tests/mcp/test_mcp_integration.py:10-44,248-288,462-496`). No Linux private-provider setting or auth-negative assertion was changed.
- The assignment reports historical macOS/Windows failures caused by expecting the Canvas URI where the observed inventory contained only the custom resource. The new assertion matches that reported platform boundary. It does not establish that the exact CI checkout mutation which caused the Ubuntu published-browser failure has been identified; the assignment explicitly says its path is unknown. I therefore make no claim about that path or a reproduced CI run.

## Documentation improvement

- Canonical file changed or proposed: `docs/skills/repository-operations.md` (exact proposed addition near the existing source-bound browser guidance).
- Durable learning captured: “For a source-bound Runtime/browser CI gate, finish required frontend/OAuth preparation and explicit browser installation first, then run the gate before build/test phases that can regenerate tracked inputs. Preserve the tracked-clean source check and all source/receipt predicates when changing step order. Platform inventory assertions must follow the existing provider boundary: the private Canvas resource is expected only on Linux; retain custom-resource and authentication-negative checks on other platforms.”
- Evidence: Reviewed the generator and generated step sequence; the added order controls require these before/after relationships. The MCP integration helper encodes Linux Canvas-resource presence and custom-only inventories for macOS/Windows, while the live integration retains custom resource reads and auth-negative calls. Assignment-provided CI observations report the corresponding Mac/Win mismatch and the Ubuntu clean-source-guard failure.
- Stale or ambiguous guidance removed: None proposed. Do not record a specific Ubuntu-mutated path because none is known from the reviewed evidence.
- Remaining uncertainty: No tests were run in this read-only lane, and the exact tracked path affected by the historical Ubuntu failure remains unknown. The source-clean guard is still intentionally strict.

Upstream disposition: none
