# CI correction review receipt

Scope: read-only review of `.github/workflows/_gen_workflows.py`, generated and manual workflow deltas, `developer/tests/test_runtime_ci_fixture_327.py`, and the listed Action Server fixtures/tests. No tracked files changed and no full suites run.

## Concrete finding

- **Coverage gate can silently omit provider-backed Action Server tests.** `.github/workflows/coverage-gate.yml:55-56` runs `rcc ... -t Coverage` without provisioning the owned PostgreSQL service or setting `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1`. `developer/coverage_gate.py:18-24` measures Action Server with `-m 'not integration_test' -n auto`; `_suite_environment` at lines 138-147 inherits the workflow environment and only validates `ACTIONS_RUNTIME_TEST_PYTHON`. The newly changed provider fixtures skip when their DSN or Docker is absent unless strict mode is set; e.g. `test_knowledge_execution.py:58-62` and `test_sealed_postgres.py:30-34`. The coverage workflow can therefore succeed and emit coverage without those provider tests running.
- **Narrow fix:** put the same pinned, owned PostgreSQL startup before `Measure portable package suite coverage`, export both required DSN variables and `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1` through `GITHUB_ENV`, and remove the exact container in an `if: always()` cleanup step after coverage. Keep this service limited to the Linux coverage job. Add a small contract assertion that the coverage workflow runs with provider strict mode and the owned PostgreSQL lifecycle, so later edits cannot restore silent skips.

## Review findings

- The normal Action Server portable CI invocation is covered: generator `ActionServerTests.run_tests()` puts the owned PostgreSQL service around `inv test-not-integration`, and generated `actions_runtime_tests.yml` contains those steps. Startup pins the image digest, binds to loopback on an ephemeral port, checks readiness, records the exact container ID before readiness polling, masks the DSN, and sets strict mode. Cleanup uses the recorded ID and `always()`.
- The ordinary no-Docker and no-DSN outcomes are skips, while strict CI mode turns them into failures. The platform-specific output-store coverage remains Linux-only; the added skip preserves that boundary.
- The reviewed workflow diff only adds Windows `core.longpaths` checkout configuration and the Linux-owned PostgreSQL lifecycle. No publisher, authentication, credential, workflow permission, or release gate was removed or relaxed in the scoped diffs.
- The provider lifecycle tests cover valid Bash, successful setup and exact-ID cleanup, failed readiness retaining the ID for cleanup, and fail-closed cleanup-listing errors. The capability fixture covers missing Docker/DSN skip versus strict failure.
- `git diff --check` completed without output. Parent-provided evidence: Shell stub 3 tests passed, Toolkit 193 passed, and Runtime lint/type 659 passed. No full suites were run as requested.

## Documentation improvement proposal

- **Canonical file proposed:** `docs/skills/repository-operations.md`, in the existing Action Server PR gate discussion near line 2624.
- **Exact delta:** append: “The measured Python coverage gate also invokes the Action Server portable suite (`developer/coverage_gate.py`, `-m 'not integration_test' -n auto`). Provider-backed tests skip when their owned PostgreSQL DSN or Docker is absent unless `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1`; provision the pinned owned PostgreSQL service and set strict mode around coverage measurement, then clean up the owned container with an always-running step. Otherwise coverage may pass while omitting those provider tests.”
- **Durable learning captured:** CI coverage executes the portable Action Server provider tests in a separate workflow, so the normal runtime workflow's service setup does not cover it; strict mode and owned service provisioning must accompany coverage as well.
- **Evidence:** `.github/workflows/coverage-gate.yml:55-56`; `developer/coverage_gate.py:18-24,138-147`; `action_server/tests/action_server_tests/test_knowledge_execution.py:58-62`; `action_server/tests/action_server_tests/test_sealed_postgres.py:30-34`.
- **Stale or ambiguous guidance removed:** none (proposal only).
- **Remaining uncertainty:** hosted workflow execution of the corrected coverage job remains unverified.

Upstream disposition: none.
