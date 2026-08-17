# Community Product Surface Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove active Data Server/Data Package and enterprise/private-tier product surfaces while retaining public Runtime, Canvas, MCP v2, and exactly four offline community templates.

**Architecture:** Contract tests first define the allowed public surface and approved history/legal exclusions. Runtime and build cleanup then remove product-only APIs and lanes, after which template delivery becomes embedded-only and its generated production bundle is regenerated deterministically. Cross-package, frontend, binary, offline-template, and MCP gates prove the retained system.

**Tech Stack:** Python 3.12, Pytest, Poetry 2.1.1, RCC 18.18.1, TypeScript/Vite/Vitest, deterministic ZIP/YAML generation, GitHub Actions.

## Global Constraints

- Retain production template IDs `minimal`, `basic`, `advanced`, and `workflow-producer-consumer` only.
- Preserve Runtime and Canvas as separate frontend roots using one public manifest and lockfile.
- Preserve stateless MCP v2 `/mcp`; do not add `/sse` compatibility.
- Retain historical changelogs and legally required notices.
- Keep Canvas template #127 and MCP v2 showcase #126 out of this branch.
- Do not hand-edit generated template archives or metadata.
- Keep issue #125 as the sole writable lane and preserve unrelated staged reports and `.clawpatch` data.

---

### Task 1: Add public-surface absence and inventory contracts

**Files:**
- Modify: `action_server/tests/contract_tests/test_active_contracts.py`
- Modify: `action_server/tests/action_server_tests/test_frontend_topology_contract.py`
- Modify: `action_server/tests/action_server_tests/test_template_bundle.py`

**Interfaces:**
- Consumes: repository source/docs/workflows, template manifests, embedded metadata.
- Produces: explicit failures for active Data Server/DataContext, hosted template transport, private-tier, vendoring, credential, and product-only surfaces.

- [ ] **Step 1: Add failing static boundary cases.**

Extend the active-surface scanner to cover `actions/src`, Action Server tests/build helpers, `.github/workflows`, active docs, and template source. Exclude only changelogs, licenses/notices, archived superpowers plans/specs, and explicitly historical guides. Assert the active tree contains none of:

```python
FORBIDDEN_PRODUCT_SURFACE = (
    "DataServerTool",
    "DataContext",
    "x-data-context",
    "data-access-query",
    "data-access-native",
    "data-access-kb",
    "NPM_TOKEN",
    "npm.pkg.github.com",
    "@sema4ai/",
    "--tier=enterprise",
    "source=vendored",
    "source=registry",
)
```

- [ ] **Step 2: Add failing embedded-only template assertions.**

Assert project helpers contain no remote metadata/package URL or `actions_http.get`, production metadata equals the four literal IDs, and checked-in YAML matches those IDs.

- [ ] **Step 3: Run the focused RED gate.**

Run:

```bash
rtk pytest action_server/tests/contract_tests/test_active_contracts.py action_server/tests/action_server_tests/test_frontend_topology_contract.py action_server/tests/action_server_tests/test_template_bundle.py -q
```

Expected: failures naming existing active product-only files and hosted template update code.

- [ ] **Step 4: Commit the contracts.**

```bash
rtk git add action_server/tests/contract_tests/test_active_contracts.py action_server/tests/action_server_tests/test_frontend_topology_contract.py action_server/tests/action_server_tests/test_template_bundle.py
rtk git commit -m "test: define public community surface"
```

### Task 2: Remove Data Server and DataContext compatibility

**Files:**
- Delete: `templates/data-access-query/`
- Delete: `templates/data-access-native/`
- Delete: `templates/data-access-kb/`
- Delete: `action_server/tests/action_server_tests/test_data_package.py`
- Delete: `action_server/tests/action_server_tests/resources/data_package/`
- Modify: `action_server/src/actions/server/_common/tools.py`
- Modify: `action_server/tests/action_server_tests/common_tests/test_tools.py`
- Modify: `actions/src/actions/_action_context.py`
- Modify: affected `actions/tests/**` context tests found by symbol search
- Modify: `action_server/src/actions/server/_actions_run.py`
- Modify: `action_server/pyproject.toml`
- Delete: `action_server/docs/guides/18-data-packages.md`
- Modify: `action_server/docs/guides/21-call-action.md`

**Interfaces:**
- Consumes: `BaseTool`, `ActionContext`, `InvocationContext`, `RequestContexts`.
- Produces: Action Server and Actions Core with no Data Server downloader, Data Package fixture, DataContext accessor, or active `x-data-context` contract.

- [ ] **Step 1: Run the Task 1 absence tests and record their Data-surface failures.**
- [ ] **Step 2: Delete the three unshipped template trees and Data Package test/fixture tree.**
- [ ] **Step 3: Remove `DataServerTool` and its downloader tests while retaining all generic tool download behavior.**
- [ ] **Step 4: Remove `DataContext`, `_data_context`, and `RequestContexts.data_context`; keep Action and Invocation context decryption/masking unchanged.**
- [ ] **Step 5: Remove active guide/comment/mypy-exclusion references; retain changelog provenance.**
- [ ] **Step 6: Run focused Actions and Action Server tests.**

```bash
rtk test poetry run pytest tests -q
rtk test poetry run pytest tests/action_server_tests/common_tests/test_tools.py tests/action_server_tests/test_cli.py -q
```

- [ ] **Step 7: Commit the breaking removal.**

```bash
rtk git add -A actions action_server templates
rtk git commit -m "refactor: remove data server compatibility"
```

### Task 3: Remove private-tier and vendored-product build surfaces

**Files:**
- Delete: `action_server/build-binary/tier_selector.py`
- Delete: `action_server/build-binary/vendor-frontend.py`
- Delete: `action_server/tests/build_system_tests/test_tier_selector.py`
- Delete: `action_server/tests/integration_tests/test_enterprise_registry.py`
- Delete: `action_server/tests/integration_tests/test_enterprise_vendored.py`
- Delete: `action_server/tests/integration_tests/test_enterprise_isolation.py`
- Delete: `action_server/tests/integration_tests/test_community_isolation.py`
- Delete: `.github/workflows/vendor-integrity-check.yml`
- Modify: `action_server/build-binary/build_artifact.py`
- Modify: `action_server/build-binary/tree_shaker.py`
- Modify: `action_server/build-binary/artifact_validator.py`
- Modify: build-system and contract tests that import tier selection or assert enterprise names
- Modify: `.github/workflows/frontend-build-unauthenticated.yml`
- Modify: `.github/workflows/copilot-setup-steps.yml`
- Modify: `action_server/tests/integration_tests/test_ci_matrix.py`
- Modify: `action_server/tests/integration_tests/test_tier_logging.py`
- Modify: `action_server/tests/integration_tests/test_json_output.py`
- Modify: `action_server/tests/integration_tests/README.md`
- Modify: `action_server/tests/quickstart_tests/README.md`
- Modify: `docs/BUILD_INSTRUCTIONS.md`
- Modify: `docs/COMMUNITY_UI_SPEC.md`
- Modify: `.github/copilot-instructions.md`

**Interfaces:**
- Consumes: one public frontend manifest/lock, Runtime/Canvas build tasks, generic artifact integrity helpers.
- Produces: one public build vocabulary with no tier selector, private registry credential, vendored package updater, enterprise artifact contract, or upsell lane.

- [ ] **Step 1: Run the Task 1 static boundary gate and record private-tier failures.**
- [ ] **Step 2: Delete product-only selector/vendor code, tests, and workflow.**
- [ ] **Step 3: Convert artifact naming/validation to the actual single public artifact names used by live release workflows; update every direct consumer atomically.**
- [ ] **Step 4: Retain generic manifest/import validators but rename messages away from enterprise-tier language and keep rejection of private packages/registries.**
- [ ] **Step 5: Remove obsolete credential fallbacks, tier matrices, quickstart scenarios, and active product comparison docs.**
- [ ] **Step 6: Run focused build-system and contract tests.**

```bash
rtk test poetry run pytest tests/build_system_tests tests/contract_tests/test_artifact_naming.py tests/contract_tests/test_import_guards.py tests/contract_tests/test_artifact_validator_import.py -q
```

- [ ] **Step 7: Commit the public-only build cleanup.**

```bash
rtk git add -A action_server .github docs
rtk git commit -m "refactor: remove private tier build surfaces"
```

### Task 4: Make embedded templates the sole runtime authority

**Files:**
- Modify: `action_server/src/actions/server/_new_project_helpers.py`
- Modify: `action_server/tests/action_server_tests/test_template_bundle.py`
- Modify: `action_server/tests/action_server_tests/test_create_new_project.py`
- Regenerate: `action_server/src/actions/server/templates/action-templates.zip`
- Regenerate: `action_server/src/actions/server/templates/action-templates.yaml`

**Interfaces:**
- Consumes: deterministic production bundle and existing safe archive validators.
- Produces: embedded-only cache seeding/listing/extraction with no network transport and exact four-template metadata.

- [ ] **Step 1: Add/confirm RED tests that fail if any network client or hosted URL remains.**
- [ ] **Step 2: Remove metadata/package download logic and seed invalid/missing cache exclusively from embedded resources.**
- [ ] **Step 3: Preserve SHA-256, normalized path, traversal, duplicate, and symlink validation before cache acceptance or extraction.**
- [ ] **Step 4: Regenerate production assets with the authoritative command.**

```bash
rtk proxy python templates/packaging/build_embedded_bundle.py --config templates/packaging/templates-prod.json --template-root templates --output-dir action_server/src/actions/server/templates
```

- [ ] **Step 5: Generate into two temporary directories and compare every output byte.**
- [ ] **Step 6: Run template bundle/create/list/offline tests.**

```bash
rtk test poetry run pytest tests/action_server_tests/test_template_bundle.py tests/action_server_tests/test_create_new_project.py tests/action_server_tests/test_cli.py -q
```

- [ ] **Step 7: Commit embedded-only delivery and generated assets.**

```bash
rtk git add action_server/src/actions/server/_new_project_helpers.py action_server/tests/action_server_tests/test_template_bundle.py action_server/tests/action_server_tests/test_create_new_project.py action_server/src/actions/server/templates
rtk git commit -m "refactor: use embedded community templates only"
```

### Task 5: Update canonical guidance and close static boundary gaps

**Files:**
- Modify: `docs/skills/repository-operations.md`
- Modify: `CLAUDE.md`
- Modify: `action_server/frontend/README.md` only if source evidence exposes a contradiction
- Modify: Task 1 contract files for any newly discovered active roots

**Interfaces:**
- Consumes: verified post-cleanup source and exact commands.
- Produces: one canonical public-only operations contract and a static scan that distinguishes active code from retained history/legal evidence.

- [ ] **Step 1: Document exact production template IDs, explicit production generator command, and the beta-default shell-wrapper warning.**
- [ ] **Step 2: Document embedded-only template authority, absence of DataContext/Data Server, and retained Runtime/Canvas/MCP v2 boundaries.**
- [ ] **Step 3: Remove stale enterprise/private registry/vendoring instructions from canonical and compatibility guidance.**
- [ ] **Step 4: Run repository-wide static scans; classify every remaining match as approved history/legal, generic non-product vendoring, or a blocker.**
- [ ] **Step 5: Run documentation and focused contract gates, then commit.**

```bash
rtk git add docs/skills/repository-operations.md CLAUDE.md action_server/tests/contract_tests/test_active_contracts.py
rtk git commit -m "docs: define public community boundaries"
```

### Task 6: Verify exact candidate and prepare independent review

**Files:**
- No planned source changes; repairs require a new RED regression and separate commit.

**Interfaces:**
- Consumes: Tasks 1-5 exact candidate.
- Produces: green cross-package, frontend, binary/offline-template, MCP, static-scan, and diff evidence for exact-SHA review.

- [ ] **Step 1: Run affected package suites, lint, type checks, and RCC CheckAll.**
- [ ] **Step 2: Run `npm ci`, `npm run test:quality`, `npm run build:runtime`, and `npm run build:canvas`.**
- [ ] **Step 3: Run retained MCP v2 focused and lifecycle tests.**
- [ ] **Step 4: Run `InstallCommunity`, list the exact four templates from the built executable, create each template offline, and verify generated sources use only public dependencies.**
- [ ] **Step 5: Run deterministic bundle comparison, repository-wide static scan, `rtk git diff --check`, and inspect the complete base diff.**
- [ ] **Step 6: Record candidate SHA and request independent exact-SHA scope/code review.**
- [ ] **Step 7: Repair only validated blockers with regression evidence, repeat full gates, and obtain fresh exact-SHA review.**

No push, merge, or publication occurs until authorized by the active factory brief and the candidate has exact-SHA evidence.
