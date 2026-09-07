# Repository-Owned Action Server Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the supported Action Server project templates inside the repository and every built Action Server binary, with published Actions imports, deterministic integrity-checked bundles, safe optional updates, and verified project creation.

**Architecture:** The repository remains the source of truth for template directories and manifest descriptions. A standard-library Python packager creates canonical inner and outer ZIPs plus metadata; the generated bundle and metadata are included as Action Server package data and explicitly collected by PyInstaller. Runtime startup seeds a valid user cache from the embedded bundle, optionally accepts a verified update from the configured public download endpoint, and falls back atomically to the last valid cache or embedded bundle. Project extraction validates every archive member and stages output before exposing it.

**Tech Stack:** Python 3.12, Pytest, `zipfile`, SHA-256, Poetry, PyInstaller, RCC 18.18.1, Go wrapper, YAML/JSON metadata.

## Global Constraints

- Every template `package.yaml` pins `actions-core=1.0.0`.
- The producer-consumer template pins `actions-work-items=0.4.4`.
- Template source imports use `from actions ...`; root files named `actions.py` are not allowed.
- The built Action Server must work without contacting the Sema4AI CDN.
- Remote metadata and bundles are optional updates; hash mismatch, malformed metadata, unsafe archives, or download failure must preserve a valid cache or embedded fallback.
- Bundle bytes and metadata are deterministic for unchanged inputs and generated in sorted path order with fixed ZIP timestamps and permissions.
- Do not publish, upload, push, delete user files, or alter the pre-existing contract-test additions.
- MCP v2 remains the existing stateless `/mcp` contract with no `/sse` compatibility path.

---

### Task 1: Add red contracts for repository templates and embedded bundle behavior

**Files:**
- Modify: `action_server/tests/contract_tests/test_active_contracts.py`
- Modify: `action_server/tests/action_server_tests/test_create_new_project.py`
- Create: `action_server/tests/action_server_tests/test_template_bundle.py`

**Interfaces:**
- Consumes: repository template manifests, embedded resource paths, and `_new_project_helpers` cache/update APIs.
- Produces: failing tests for all template import/collision invariants, deterministic bundle generation, embedded fallback, hash rejection, safe extraction, and package-data inclusion.

- [ ] **Step 1: Restore only the source fixtures needed to make the existing contract meaningful, then add assertions for the four manifest-supported templates.**

Use the committed template manifests as the supported-template list. Keep the existing user-added dependency and collision checks intact, and add checks that every supported template has a source file with an `actions` import and no legacy action-library import.

- [ ] **Step 2: Add a red unit test for the wished-for bundle API.**

The test will call `build_bundle(config_path, template_root, output_dir)` twice and assert byte-identical ZIP/metadata outputs, then mutate one byte in a downloaded bundle and assert `_ensure_latest_templates()` leaves the embedded cache usable.

- [ ] **Step 3: Add red tests for embedded fallback and unsafe archive rejection.**

Patch the network client to fail, call `_ensure_latest_templates()` with an empty temporary cache, and assert metadata/templates are available from embedded resources. Supply a traversal member such as `../outside.py` and assert `_unpack_template()` raises without writing outside the destination.

- [ ] **Step 4: Run the focused tests and record the expected RED result.**

Run:

```bash
rtk pytest action_server/tests/contract_tests/test_active_contracts.py action_server/tests/action_server_tests/test_template_bundle.py action_server/tests/action_server_tests/test_create_new_project.py -q
```

Expected: failure from missing repository-owned template sources and missing bundle/resource APIs, not a test collection error.

### Task 2: Reintroduce and modernize repository template sources

**Files:**
- Restore/modify: `templates/` tracked source, docs, devdata, and packaging metadata
- Rename: `templates/minimal/actions.py` to a non-colliding action module
- Rename: `templates/basic/actions.py` to a non-colliding action module
- Modify: `templates/advanced/src/github/*.py`
- Modify: `templates/data-access-*/**/*.py` where imports or module paths require consistency
- Modify: `templates/workflow-producer-consumer/workflow_actions.py`

**Interfaces:**
- Consumes: existing template behavior and devdata contracts.
- Produces: source trees that resolve the published `actions-core` distribution, contain no `sema4ai.actions` or `robocorp.actions` imports, and have no root `actions.py` module collision.

- [ ] **Step 1: Restore the deleted tracked template files without changing unrelated worktree edits.**

Re-add the existing repository template contents, including binary/data fixtures required by the package examples, then apply only the requested source/import/module-name changes.

- [ ] **Step 2: Rename the two root `actions.py` files and update any README/devdata references.**

Use descriptive module names that do not shadow the installed `actions` package, while preserving the exported action names and generated project behavior.

- [ ] **Step 3: Run the template contract test and focused template tests.**

Run the contract module and each supported template’s local test command where dependencies are available; record unavailable external data-service tests as unverified rather than passing.

### Task 3: Implement deterministic bundle generation and embed the generated assets

**Files:**
- Create: `templates/packaging/build_embedded_bundle.py`
- Modify: `templates/packaging/create-templates-package.sh`
- Modify: `templates/packaging/templates-prod.json`
- Modify: `templates/packaging/templates-beta.json`
- Create: `action_server/src/actions/server/templates/action-templates.zip`
- Create: `action_server/src/actions/server/templates/action-templates.yaml`
- Modify: `action_server/pyproject.toml`
- Modify: `action_server/action-server.spec`
- Modify: `developer/toolkit.py`
- Modify: `developer/tests/test_toolkit_contract.py`

**Interfaces:**
- Consumes: the configured production template IDs and repository template directories.
- Produces: stable outer/inner ZIP bytes, SHA-256 metadata, a checked-in package-data bundle, and an RCC-toolkit build step that regenerates the bundle before PyInstaller.

- [ ] **Step 1: Implement the packager with sorted paths, fixed timestamps, fixed file modes, duplicate/path checks, and atomic output writes.**

Generate one inner ZIP per configured template and an outer `action-templates.zip` containing those inner archives. Write metadata only after hashing the final outer bytes. Support the existing deployment script’s `temp/action-templates.zip`, `temp/action-templates.yaml`, and per-template ZIP output.

- [ ] **Step 2: Replace stale Sema4AI CDN metadata with the public compatibility download endpoint and document that runtime defaults are embedded.**

Keep deployment workflows usable for legacy clients, but make the embedded Action Server bundle independent of that endpoint.

- [ ] **Step 3: Include the generated files in Poetry and PyInstaller package data.**

Add explicit package inclusion and spec-file data collection so source, wheel, onedir, and Go-wrapper distributions all contain the same bundle.

- [ ] **Step 4: Make `developer/toolkit.py build-community` regenerate the bundle before frontend/executable builds and update its contract test.**

Use the repository-scoped RCC environment and the existing package-environment isolation rules.

- [ ] **Step 5: Generate the checked-in bundle and run the new deterministic-generation tests.**

Run the generator twice and compare hashes before proceeding to runtime implementation.

### Task 4: Replace CDN-dependent template handling with embedded, verified fallback/update logic

**Files:**
- Modify: `action_server/src/actions/server/_new_project_helpers.py`
- Modify: `action_server/src/actions/server/_new_project.py`
- Modify: `action_server/tests/action_server_tests/test_create_new_project.py`
- Modify: `action_server/tests/action_server_tests/resources/sample_templates/action-templates.yaml`
- Modify: `action_server/tests/action_server_tests/resources/sample_templates/minimal.zip`

**Interfaces:**
- Consumes: embedded bundle resources, optional configured update URLs, and existing Action Server CLI calls.
- Produces: `ActionTemplatesMetadata`, `_ensure_latest_templates()`, `_get_local_templates_metadata()`, and `_unpack_template()` behavior compatible with the CLI while rejecting invalid updates and archive traversal.

- [ ] **Step 1: Add embedded-resource readers and a shared metadata/bundle validator.**

Validate schema, template IDs, SHA-256, outer ZIP members, inner ZIP members, duplicate normalized paths, absolute paths, `..` traversal, and symlink entries before accepting a cache or update.

- [ ] **Step 2: Seed the cache atomically from embedded assets before attempting optional network refresh.**

If the cache is absent or invalid, write the embedded metadata and bundle through sibling `.part` files and `os.replace`. If a refresh fails, retain the valid cache and log a warning; if the cache is invalid, use the embedded copy.

- [ ] **Step 3: Make remote refresh opt-in/configurable without the stale Sema4AI CDN dependency.**

Use the public compatibility endpoint by default or an explicit `ACTIONS_TEMPLATES_METADATA_URL`/`ACTIONS_TEMPLATES_PACKAGE_URL` override. Require the downloaded bundle hash to match metadata and validate before replacing either cache file.

- [ ] **Step 4: Stage template extraction and preserve existing force/non-force semantics.**

Read the selected inner ZIP from the validated outer bundle, create files only under the requested directory, and fail before writing on invalid members.

- [ ] **Step 5: Run the focused unit and CLI tests and verify GREEN.**

Run the new bundle tests plus existing new-project tests, then run the non-integration Action Server suite.

### Task 5: Build and exercise the community binary and supported templates

**Files:**
- Modify: `docs/skills/repository-operations.md`
- Modify: `action_server/tests/action_server_tests/test_cli.py` if the supported-template assertions need the fourth template

**Interfaces:**
- Consumes: the generated embedded bundle and RCC developer toolkit build.
- Produces: a Linux community Action Server binary, per-template creation/import/start evidence, and MCP v2 proof.

- [ ] **Step 1: Run the RCC toolkit with a repository-scoped `ROBOCORP_HOME`.**

Run the toolkit’s doctor/bootstrap/build path using a temporary repository-scoped home; do not use the user’s global RCC cache.

- [ ] **Step 2: Record binary path/version and list templates from the newly built executable.**

Verify the executable lists every production-supported template without contacting the CDN.

- [ ] **Step 3: Create a fresh project for each supported template.**

For every generated tree, recursively scan Python sources for `sema4ai.actions` and `robocorp.actions`, verify no root `actions.py`, and record the exact scan result.

- [ ] **Step 4: Start each runnable generated project with a finite timeout.**

Use the built binary and a repository-scoped RCC home, stop each process at the timeout, and record exit/timeout plus stderr. Treat expected external-service failures as evidence, not as successful starts.

- [ ] **Step 5: Prove MCP v2 remains active.**

Run the existing focused MCP v2 integration/contract test against the built runtime or binary and verify `/mcp` discover/list behavior and `/sse` absence.

### Task 6: Run final gates and capture durable operations guidance

**Files:**
- Modify: `docs/skills/repository-operations.md`

**Interfaces:**
- Consumes: exact generator/build/test output from Tasks 1–5.
- Produces: evidence-backed repository guidance for regenerating, validating, embedding, updating, and falling back templates.

- [ ] **Step 1: Run affected tests, lint, type checks, and `git diff --check`.**

Use package-configured commands from the Action Server and repository toolkit; report skipped external-service gates explicitly.

- [ ] **Step 2: Update the canonical guide with exact commands and verified invariants.**

Document the bundle path, generator command, hash/fallback policy, PyInstaller inclusion, RCC-scoped build command, finite template-start workflow, and MCP v2 gate. Remove stale claims that the Action Server requires the Sema4AI CDN for templates.

- [ ] **Step 3: Review the final status/diff for exact scope.**

Confirm the pre-existing contract-test additions remain, unrelated changes are preserved, no generated binaries or user caches are tracked outside the intended package/bundle paths, and no publish/push operation occurred.
