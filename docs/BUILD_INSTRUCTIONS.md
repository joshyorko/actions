# Action Server build instructions

## Canonical source build and installation

Use Josh's RCC fork v18.19.3 and the checked-in developer toolkit from the
repository root on `community`. See [CONTRIBUTING.md](../CONTRIBUTING.md) for
installation and the v18.18.1 N−1 compatibility lane. RCC supplies the outer
Python, Node, Go, Poetry, and Invoke toolchain; Poetry owns package dependencies
and committed lockfiles. Do not bootstrap with ad hoc pip/uv installs.

```bash
rcc run -r developer/toolkit.yaml --dev -t Doctor
rcc run -r developer/toolkit.yaml --dev -t Bootstrap
rcc run -r developer/toolkit.yaml --dev -t ToolkitTest
```

After these checks, build and install the community executable:

```bash
rcc run -r developer/toolkit.yaml --dev -t InstallCommunity
```

`InstallCommunity` replaces the `action-server` executable resolved on PATH.
Inspect that target before running it. If none exists, the fallback directory
must already be on PATH: `~/.local/bin` on Linux/macOS or
`%LOCALAPPDATA%/Programs/Actions/bin` on Windows. The task does not elevate
privileges. It atomically replaces the target and reports permission failures.

The task invokes the existing package-local `build-frontend` and
`build-executable --go-wrapper --version community-local` tasks. It checks the
built binary with `new --help`, installs it, then checks the installed target
with `version` and `new --help`. Keep `local` in developer build versions so
the Go wrapper refreshes changed same-version payloads.

Outputs are relative to `action_server/`:

- `dist/final/action-server` (Linux/macOS) or `dist/final/action-server.exe` (Windows).
- `frontend/dist/index.html` for Runtime and `frontend/dist-canvas/` for Canvas,
  with per-root artifact manifests and SBOMs.
- `src/actions/server/_static_contents.py` for embedded frontend content.

These checks prove build/install startup, not live server or release acceptance.
Do not treat a failed `start` without a package as a passing runtime test.

## Verification boundaries

Choose the gate for the change; a source build does not replace these gates.

| Gate | Command and scope |
|---|---|
| Toolkit contracts | `rcc run -r developer/toolkit.yaml --dev -t ToolkitTest`: gateway Ruff and pytest contracts only |
| Portable Python | `rcc run -r developer/toolkit.yaml --dev -t Test`: package gates, excluding Work Items service tests and Action Server integration tests |
| Measured Python coverage | `rcc run -r developer/toolkit.yaml --dev -t Coverage`: the same five portable package suites with a pytest-cov floor and complete `src/**/*.py` inventory check |
| Static Python checks | Toolkit `Lint` and `Typecheck`; `CheckAll` combines Doctor, lint, typecheck, and portable tests |
| Frontend full tests | Toolkit `FrontendTest`: `npm ci` followed by `npm run test`; separate from shipping quality gates |
| Work Items services and packaging | `.devcontainer/bin/verify-work-items`: full pytest, lock/lint, wheel/sdist and clean-wheel checks; requires healthy `TEST_REDIS_URL` and `TEST_MONGODB_URI` |
| Dev Container | `.devcontainer/bin/smoke` inside the repository Dev Container as non-root: pinned-tool checks, bootstrap, and Work Items release gate |

### Measured Python coverage

The dedicated `Coverage` task measures pytest-cov line coverage for `actions`,
`actions-http-helper`, `devutils`, `work-items`, and `action_server`, then
aggregates covered executable statements over all five package `src/` trees.
The committed `.coverage-thresholds.json` sets the minimum from the first
complete passing measurement; the current recorded floor is 53.38%. This is a
line-coverage floor, not branch coverage or a claim about every Python process
started by a test.

Coverage JSON reports must include every maintained `src/**/*.py` file,
including namespace-package modules that a test may not import. Missing suites,
reports, source files, or a result below the floor fail the task. The Work Items
portable suite excludes `persistent_backend_service`, and the Action Server
suite excludes `integration_test`; those remain separate service/integration
verification. The Action Server command keeps its regression snapshots strict
and uses the active RCC Python for its wheel test through
`ACTIONS_RUNTIME_TEST_PYTHON`.

The `coverage-gate.yml` workflow runs this gate on Linux for pull requests and
pushes to `community`, after toolkit contract checks and package bootstrap. It
uploads per-package coverage JSON and a summary receipt even on failure. When
running locally, preserve those JSON files to distinguish `BLOCKED` setup from
test failures. Only an intentional baseline change should use
`developer/coverage_gate.py --record-baseline`; normal CI never rewrites the
threshold. Test-launched Python processes outside pytest-cov's managed workers
are not measured by this gate.

### Frontend shipping gates

In the prepared RCC toolchain or repository Dev Container, from
`action_server/frontend`:

```bash
npm ci
npm run test:quality
npm run build:runtime
npm run build:canvas
npm run validate:artifacts
```

Use the checked-in public manifest and lockfile. Do not globally install Vite
or add SBOM dependencies during onboarding. The historical all-tree frontend
test suite is separate from the shipping `test:quality` gate. Static artifact
validation does not replace real-browser verification.

### Dev Container verification

The Dev Container is a separate, repository-owned environment with Node 22;
the RCC toolkit pins Node 20.19.3. Both satisfy the frontend engine requirement.
The container smoke is a Work Items release gate, not a full Action Server
binary build gate; its image does not include Go or jq. Follow
[repository operations](skills/repository-operations.md) for host-side container
setup, service orchestration, and headless verification. Service tests skipped
or not run remain unverified.

## Setup failures

If Doctor or Bootstrap fails, retain the diagnostic and fix that boundary.
Use `rcc robot diagnostics -r developer/toolkit.yaml --json` and
`rcc ht vars -r developer/toolkit.yaml` to inspect RCC resolution. Do not hide
failures with pip fallbacks or install missing tools into the host environment.

The authoritative task wiring is in `developer/toolkit.yaml` and
`developer/toolkit.py`. `.github/workflows/developer_toolkit.yml` checks primary
and N−1 RCC pins across Linux, macOS, and Windows; its Linux lanes also bootstrap,
run portable tests, and execute `InstallCommunity`. Release publishing is a
separate workflow, `.github/workflows/actions_runtime_binary_release.yml`.
