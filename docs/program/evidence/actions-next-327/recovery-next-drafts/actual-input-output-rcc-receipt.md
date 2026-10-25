Separate scratch-only opt-in test patch, one new test_generic_input_output_rcc.py; no existing tests changed. SHA256 in identity.json. Depends on frozen producer-app patch and prior input/reopen dependencies.

Verified: pytest --collect-only collected eight provider/mode combinations; Ruff and Isort passed. No RCC executed, no prepared cache opened by collection, no package install, no source/shared root modifications. Explicit ACTIONS_GENERIC_INPUT_OUTPUT_REAL_RCC=1 enables real compiler and PinnedGenericRccRunner; required receipt and RCC environment variables have no fallback. Select -k duckdb to retain SQLite/PostgreSQL and remove redundant data-query variants (four genuine executions). Parent owns exclusive RCC cache and strict PostgreSQL environment.

The test targets a real generated output-enabled package compiled with PinnedRccPackageBuildExecutor, immutable activation and explicit grants. Consumer lists/selects exact normalized input, separately submits and executes; producer uses standalone inputs without synthetic input. Full child snapshot/fence/digest/parent, terminal Attempt, read-only app child projection, retained replay counts and sealed artifact reads are asserted. The initial scaffold uses the existing fixture setup; target package compiler/execution never uses synthetic completion. Reopen is explicitly same-service projection, NOT service reconstruction or process restart. Root installed harness owns genuine restart and browser acceptance.

Execution remains unverified. No pass claim for RCC, SDK output behavior, artifact contents or installed process restart is made by collection. Upstream disposition: none.

Documentation improvement:
- Canonical file proposed: docs/skills/work-items.md, add the paragraph below once integrating this test.
- Durable learning: distinguishes executable opt-in real-package app acceptance from synthetic boundary coverage and process restart.
- Evidence: source test inspection, eight collected cases, static lint/import checks; no actual execution.
- Stale/ambiguous guidance removed: do not call same-instance canvas_get a restart test.
- Remaining uncertainty: all actual executions and installed restart remain parent-owned pending gates.

Exact proposed paragraph:
“test_generic_input_output_rcc.py is an opt-in app acceptance harness enabled with ACTIONS_GENERIC_INPUT_OUTPUT_REAL_RCC=1 and the canonical prepared receipt/RCC paths. It builds real consumer/producer packages and checks explicit selection/submit/execute, child provenance, artifact reads and terminal replay on both SQL providers. Its canvas_get reopening uses the same service instance and is not a process-restart qualification. Collection or static checks establish harness availability only; record actual RCC results separately and retain installed CLI restart/browser acceptance as distinct gates.”
