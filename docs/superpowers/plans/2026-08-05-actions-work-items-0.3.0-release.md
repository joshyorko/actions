# actions-work-items 0.3.0 Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare a reviewable `actions-work-items 0.3.0` release with warning-free PEP 621 metadata, exact artifact verification, polished PyPI documentation, and tag-only publication from merged `community` history.

**Architecture:** Keep Poetry 2.1.1 and committed Poetry locks authoritative. Extend the existing repository release gate so local development and GitHub Actions build and verify the same wheel/sdist once, then make the tag-only publication job consume those exact artifacts after checking tag version and `community` ancestry.

**Tech Stack:** Python 3.12, Poetry 2.1.1, PEP 621, Bash, GitHub Actions, Twine, unittest, pytest, Ruff.

## Global Constraints

- Prepare version `0.3.0`; do not create a tag or publish to PyPI.
- Retain `PYPI_TOKEN_ACTIONS_WORK_ITEMS`; do not introduce Trusted Publishing.
- Python 3.10 remains the package floor.
- Preserve `redis`, `docdb`, `documentdb`, and `all` extras.
- SQLite is release-gated; FileAdapter is local/single-process; Redis and DocumentDB remain experimental.
- Publication is tag-only and must prove the tagged commit is in `origin/community`.
- `workflow_dispatch` must not publish.
- The exact verified wheel and sdist are the artifacts published.
- Every implementation and review lane returns the repository documentation-improvement receipt.

---

### Task 1: Make 0.3.0 metadata and artifacts authoritative

**Files:**
- Modify: `work-items/pyproject.toml`
- Modify: `work-items/src/actions/work_items/__init__.py`
- Modify: `work-items/poetry.lock`
- Modify: `action_server/poetry.lock`
- Modify: `.devcontainer/bin/verify-work-items`
- Modify: `.devcontainer/tests/test_contract.py`
- Modify: `docs/skills/work-items.md`

**Interfaces:**
- Consumes: Poetry 2.1.1 and the existing `verify-work-items` release gate.
- Produces: PEP 621 project metadata at version `0.3.0`; an optional explicit artifact-directory argument to `verify-work-items`; verified wheel and sdist files retained at that path for CI.

- [ ] **Step 1: Add failing static contracts**

Extend `.devcontainer/tests/test_contract.py` to assert:

- `work-items/pyproject.toml` uses `[project]`, `requires-python = ">=3.10,<4.0"`, stable project URLs, and PEP 621 optional dependencies;
- runtime `__version__` is `0.3.0`;
- `verify-work-items` accepts zero or one artifact-directory argument;
- the gate derives expected version from Poetry rather than a hardcoded version;
- the gate runs `twine check --strict` and inspects built metadata/README markers;
- the gate retains an explicitly supplied artifact directory and cleans only internally created temporary artifacts.

- [ ] **Step 2: Run static contracts and confirm failure**

Run:

```bash
python -m unittest discover -s .devcontainer/tests -p 'test_*.py' -v
```

Expected: failure on missing PEP 621 metadata, version `0.3.0`, and artifact-gate behavior.

- [ ] **Step 3: Migrate metadata and bump runtime version**

Move static package metadata and dependencies to `[project]`. Keep only
`packages = [{include = "actions", from = "src"}, {include =
"actions_work_items", from = "src"}]` under `[tool.poetry]`, and retain the
existing Poetry dev dependency group and Ruff/pytest configuration.

Set stable URLs:

```toml
[project.urls]
Homepage = "https://github.com/joshyorko/actions"
Repository = "https://github.com/joshyorko/actions"
Documentation = "https://github.com/joshyorko/actions/tree/community/work-items"
Issues = "https://github.com/joshyorko/actions/issues"
```

Set `actions.work_items.__version__ = "0.3.0"`.

- [ ] **Step 4: Extend the release gate**

Implement `.devcontainer/bin/verify-work-items [artifact-directory]`:

- reject more than one argument with usage and exit 2;
- create and clean a temporary artifact directory when no argument is given;
- create but never delete the caller-supplied artifact directory;
- reject a non-empty caller-supplied artifact directory;
- derive expected version with `poetry version --short`;
- run lock check, Ruff, all tests, and one Poetry build;
- run `poetry run twine check --strict` on wheel and sdist;
- inspect wheel `METADATA` with stdlib `zipfile` and `email.parser`,
  asserting name, expected version, Markdown content type, and the README
  heading `## Backend Support`;
- install the built wheel into a clean venv and assert all three public aliases
  plus runtime/distribution version equality;
- finish with `git diff --check`.

Add Twine to the Work Items dev dependency group so strict rendering checks are
lock-controlled.

- [ ] **Step 5: Record the new artifact contract**

Update the canonical Work Items guide with the optional retained-artifact
directory, PEP 621 metadata authority, strict Twine/metadata checks, and the
fact that the gate rejects a non-empty destination.

- [ ] **Step 6: Regenerate both affected lockfiles with Poetry 2.1.1**

Inside `actions-devcontainer:test`, run `poetry lock` in `work-items/` and
`action_server/`. Do not edit lockfiles manually. Confirm both local
`actions-work-items` entries resolve to `0.3.0`.

- [ ] **Step 7: Run Task 1 verification**

Use a writable temporary artifact directory and the linked-worktree common Git
metadata mount:

```bash
common_git_dir=$(git rev-parse --path-format=absolute --git-common-dir)
artifact_dir=$(mktemp -d)
docker run --rm --user vscode \
  -v "$PWD:/workspaces/actions" \
  -v "$common_git_dir:$common_git_dir:ro" \
  -v "$artifact_dir:/artifacts" \
  -w /workspaces/actions actions-devcontainer:test \
  .devcontainer/bin/verify-work-items /artifacts
```

Also run:

```bash
python -m unittest discover -s .devcontainer/tests -p 'test_*.py' -v
git diff --check
```

Expected: all static contracts, Ruff, 47 or more tests, warning-free Poetry
check, strict Twine checks, metadata checks, clean-wheel aliases, versions, and
diff check pass.

- [ ] **Step 8: Commit**

```bash
git add work-items/pyproject.toml work-items/src/actions/work_items/__init__.py \
  work-items/poetry.lock action_server/poetry.lock \
  .devcontainer/bin/verify-work-items .devcontainer/tests/test_contract.py \
  docs/skills/work-items.md
git commit -m "build(work-items): prepare 0.3.0 artifacts"
```

### Task 2: Publish a complete PyPI product guide

**Files:**
- Modify: `work-items/README.md`
- Modify: `work-items/docs/CHANGELOG.md`
- Modify: `.devcontainer/tests/test_contract.py`
- Modify: `docs/skills/work-items.md`

**Interfaces:**
- Consumes: Task 1's `## Backend Support` artifact metadata contract and version `0.3.0`.
- Produces: the exact long description packaged into the 0.3.0 wheel/sdist and a release changelog entry.

- [ ] **Step 1: Add failing PyPI documentation contracts**

Add static assertions that the README contains:

- `## Backend Support`;
- a table naming SQLite, FileAdapter, Redis, MongoDB/DocumentDB, and Action
  Server with evidence-accurate maturity;
- `## Quick Start`, `## Safety and Determinism`, and
  `## Migrating from robocorp-workitems`;
- one complete seed/reserve/output/release example;
- public alias/version verification;
- no unused `ExceptionType` import in the payload example.

Assert the changelog starts with `## 0.3.0 - 2026-08-05`.

- [ ] **Step 2: Run static contracts and confirm failure**

Run the static unittest command from Task 1. Expected: failure on missing README
structure and changelog version.

- [ ] **Step 3: Restructure the README**

Keep existing accurate API and adapter details while reorganizing the page:

1. value statement and installation;
2. backend support matrix;
3. complete quick start;
4. payload, files, failure, adapter, and Action Server guides;
5. safety and determinism guarantees backed by merged code/tests;
6. compatibility and migration differences;
7. API/import/version verification and issue links.

Every example import must be used. Do not describe Redis or DocumentDB as
production-supported, and do not imply Action Server manages arbitrary
adapters.

- [ ] **Step 4: Write the 0.3.0 changelog entry**

Summarize attachment confinement, deterministic atomic SQLite reservation,
exact JSON preservation, Action Server shadowing resistance and producer
integration, Ruff cleanup, Dev Container/release gate, and documentation.
Explicitly retain experimental backend status.

- [ ] **Step 5: Record PyPI documentation invariants**

Update the canonical Work Items guide to require an evidence-accurate backend
support matrix, complete lifecycle example, used imports, Robocorp migration
boundaries, and strict rendering checks for future releases.

- [ ] **Step 6: Verify built rendering**

Run the static contracts and the Task 1 release gate with an explicit artifact
directory. Confirm strict Twine checks and wheel metadata README marker pass.

- [ ] **Step 7: Commit**

```bash
git add work-items/README.md work-items/docs/CHANGELOG.md \
  .devcontainer/tests/test_contract.py docs/skills/work-items.md
git commit -m "docs(work-items): publish 0.3.0 guide"
```

### Task 3: Enforce merged-community tag publication

**Files:**
- Modify: `.github/workflows/work_items_release.yml`
- Modify: `.devcontainer/tests/test_contract.py`
- Modify: `docs/skills/work-items.md`

**Interfaces:**
- Consumes: Task 1's retained artifact-directory interface and Task 2's built long description.
- Produces: CI verification for PR/`community` changes and tag-only token-based publication of the exact verified artifacts.

- [ ] **Step 1: Add failing workflow contracts**

Assert the workflow:

- has pull-request, `community` push, and `actions-work-items-*` tag triggers;
- has no `workflow_dispatch`;
- pins Poetry to `2.1.1` and Python to `3.12`;
- references these immutable action revisions with version comments:
  - checkout: `fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09` (`v5`);
  - setup-python: `a26af69be951a213d495a4c3e4e4022e16d87065` (`v5`);
  - upload-artifact: `ea165f8d65b6e75b540449e92b4886f43607fa02` (`v4`);
  - download-artifact: `d3f86a106a0bac45b974a628896c90dbdf5c8093` (`v4`);
- invokes `verify-work-items` with an explicit artifact directory;
- uploads and downloads the same named artifact;
- gates publication on an `actions-work-items-*` tag;
- verifies tag version and `origin/community` ancestry;
- publishes with `PYPI_TOKEN_ACTIONS_WORK_ITEMS` and no OIDC permission.

- [ ] **Step 2: Run static contracts and confirm failure**

Run the static unittest command. Expected: failure on the legacy manual
deployment workflow.

- [ ] **Step 3: Implement verify and publish jobs**

Create:

- a `verify` job with `contents: read`, full checkout, Python 3.12,
  Poetry 2.1.1, Work Items lock sync, the retained-artifact release gate, and
  artifact upload;
- a `publish` job needing `verify`, guarded by
  `startsWith(github.ref, 'refs/tags/actions-work-items-')`, using environment
  `pypi`, full checkout, ancestry and tag/version checks, artifact download
  to `work-items/dist`, and `poetry publish --no-interaction` configured
  with the existing token secret.

Use workflow path filters covering Work Items, Action Server's local lock,
release scripts/tests, this workflow, and canonical Work Items guidance.

- [ ] **Step 4: Update canonical release and recovery guidance**

Document:

- the PR/`community` verification lane and tag-only publication boundary;
- exact pre-tag sequence and the immutable `actions-work-items-0.3.0` tag;
- GitHub environment protection as external configuration, not a repository
  guarantee;
- never moving/reusing accepted artifacts or release tags;
- the worktree-safe common-Git-directory Docker mount;
- the strict Twine, metadata, alias, version, and ancestry gates.

Remove the stale claim that only the earlier build/import checks comprise the
release gate.

- [ ] **Step 5: Verify workflow and release gate**

Run:

```bash
python -m unittest discover -s .devcontainer/tests -p 'test_*.py' -v
bash -n .devcontainer/bin/verify-work-items
git diff --check
```

Then run the full retained-artifact release gate in the Dev Container. Confirm
the workflow contains no publish-capable manual path and no unpinned action.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/work_items_release.yml \
  .devcontainer/tests/test_contract.py docs/skills/work-items.md
git commit -m "ci(work-items): gate 0.3.0 publication"
```

### Task 4: Final cross-package release verification

**Files:**
- Modify only if verification reveals a release-blocking defect in the files already owned by Tasks 1-3.

**Interfaces:**
- Consumes: all release commits.
- Produces: reviewed, push-ready 0.3.0 release branch with no tag or publication.

- [ ] **Step 1: Run the complete release gate from the linked worktree**

Run static contracts, shell syntax, the retained-artifact Dev Container gate,
focused Action Server Work Items loader tests/Ruff, strict Twine checks, and
`git diff --check`.

- [ ] **Step 2: Inspect exact artifacts**

Record SHA-256 digests for the wheel and sdist. Inspect wheel `METADATA`,
`RECORD`, top-level import packages, version, long-description content type,
and README support markers. Confirm no credentials, datadirs, generated logs,
or queue artifacts are present.

- [ ] **Step 3: Review release diff and GitHub state**

Compare `origin/community...HEAD`, verify only intended release files changed,
and confirm no tag named `actions-work-items-0.3.0` exists locally, remotely,
or on PyPI.

- [ ] **Step 4: Commit only evidence-backed corrections**

If verification changes tracked files, commit a focused correction. Otherwise
leave the verified tree clean and proceed to final whole-branch review.
