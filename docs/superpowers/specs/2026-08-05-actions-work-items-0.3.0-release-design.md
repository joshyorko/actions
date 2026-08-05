# actions-work-items 0.3.0 Release Design

## Purpose

Release the Work Items hardening merged by PR #70 as `actions-work-items
0.3.0` through a separate, reviewable release change. The release must make
the PyPI project page a reliable product and migration guide, prove that
published artifacts come from merged `community` history, and retain the
existing `PYPI_TOKEN_ACTIONS_WORK_ITEMS` credential for this release.

This change prepares publication but does not create a tag or upload to PyPI.

## Release Boundary

The release change includes:

- a synchronized `0.3.0` version across package metadata, runtime metadata,
  changelog, and every lockfile that embeds the local package version;
- PEP 621 package metadata supported by Poetry 2.1.1, replacing deprecated
  `[tool.poetry]` package and extras metadata;
- a PyPI-facing README organized around installation, a complete first
  workflow, supported backends, compatibility, safety guarantees, and
  migration from `robocorp-workitems`;
- a CI verification job for pull requests and `community` changes affecting
  Work Items release inputs;
- a tag-only publication job that validates tag/version equality and merged
  `community` ancestry before publishing the exact verified artifacts;
- canonical release and recovery guidance in `docs/skills/work-items.md`;
- worktree-safe Dev Container verification guidance discovered during the
  release baseline.

It excludes Trusted Publishing configuration, Redis or DocumentDB reliability
claims, service-backed backend CI, unrelated Action Server cleanup, and the
actual release tag.

## Package Metadata

`work-items/pyproject.toml` will use PEP 621 `[project]` metadata for the
static name, version, description, readme, Python requirement, license,
authors, keywords, classifiers, URLs, dependencies, and optional dependencies.
Poetry-specific dependency groups and tool configuration remain under
`[tool.poetry.group.*]` and `[tool.*]`.

The package keeps Python 3.10 as its floor and retains these extras:
`redis`, `docdb`, `documentdb`, and `all`. Both DocumentDB extra names
continue to install `pymongo`. Project links target stable repository and
package paths rather than a mutable branch URL.

The authoritative version is `0.3.0`. Runtime `__version__`, the Work Items
lock, and Action Server's lock entry for the local editable distribution must
match it. Lockfiles are regenerated with Poetry 2.1.1; they are not edited by
hand.

## PyPI Documentation

The README opens with a concise value statement and a support matrix:

- SQLite: supported and release-gated;
- FileAdapter: supported for local, single-process workflows;
- Redis: experimental pending service-backed CI;
- MongoDB/DocumentDB: experimental pending service-backed CI;
- Action Server integration: supported for the merged SQLite management API
  boundary, without implying arbitrary adapter management.

The first runnable example must show the complete lifecycle: initialize or
seed, reserve, create a parent-linked output, and release the input. Every
symbol used by an example is imported, and every example import is used.
Examples must avoid implying automatic Control Room reservation or
byte-for-byte Robocorp compatibility.

Dedicated sections explain:

- safe attachment naming and containment;
- deterministic atomic SQLite reservation;
- arbitrary JSON payload support in the library and the narrower REST
  object-or-null projection;
- public import aliases and migration differences from
  `robocorp-workitems`;
- optional backend installation and maturity;
- where to report issues and how to verify installed version/import aliases.

The built wheel and sdist must pass `twine check --strict`; verification also
inspects wheel metadata to prove that the intended README and `0.3.0` version
were packaged.

## CI and Publication

The Work Items workflow has two responsibilities with an explicit boundary.

The verification job runs for:

- pull requests that change Work Items source, tests, metadata, README,
  lockfiles, the release workflow, or the release gate;
- pushes to `community` changing those paths;
- `actions-work-items-*` tags.

It installs Python 3.12 and Poetry 2.1.1, synchronizes from the committed lock,
runs the repository Work Items release gate, builds the wheel and sdist once,
runs strict Twine checks, validates artifact metadata, and uploads those exact
artifacts for the publication job.

The publication job runs only for `refs/tags/actions-work-items-*`. It:

1. checks out full history;
2. fetches `origin/community`;
3. proves the tagged commit is an ancestor of `origin/community`;
4. proves the tag version equals the package and runtime versions
   (`0.3.0` for this release);
5. downloads the artifacts produced by the successful verification job;
6. publishes those artifacts using `PYPI_TOKEN_ACTIONS_WORK_ITEMS`.

`workflow_dispatch` is removed from the publishing path. Manual reruns of the
same tag remain available through GitHub Actions without introducing a second
version input. Job permissions remain least-privilege: verification needs
`contents: read`; publication receives only the permissions required by the
existing token-based path.

The workflow may reference a `pypi` GitHub environment for approvals, but
repository guidance must state that protection rules are external state and
must be configured in GitHub before relying on them.

## Local Verification and Worktrees

The canonical release gate remains `.devcontainer/bin/verify-work-items`.
Normal checkouts use the documented repository-root bind mount.

A linked worktree stores its Git directory under the parent checkout's common
Git directory. Mounting only the worktree makes the final `git diff --check`
fail even when package gates pass. Worktree verification therefore also mounts
the absolute common Git directory read-only at the same absolute path inside
the container. Guidance must show a command derived from
`git rev-parse --path-format=absolute --git-common-dir`, not a personal path.

The final release gate covers:

- Poetry lock consistency without deprecation warnings;
- Ruff;
- all Work Items tests;
- wheel and sdist builds;
- clean-environment imports for `actions.work_items`, `actions.workitems`,
  and `actions_work_items`;
- runtime and distribution version equality;
- strict Twine rendering checks;
- intended README content in built metadata;
- focused Action Server tests for its local `actions-work-items 0.3.0` lock;
- `git diff --check`.

## Release Sequence and Recovery

1. Merge the 0.3.0 release PR into `community`.
2. Verify the merged commit's required Work Items workflow is green.
3. Create `actions-work-items-0.3.0` on that exact merged `community`
   commit.
4. Confirm the workflow's ancestry, version, artifact, and publication gates.
5. Verify PyPI reports 0.3.0 and install the published wheel in a clean
   environment.

Do not move or reuse a failed release tag. If publication fails before PyPI
accepts artifacts, fix the workflow on `community`, merge the fix, and create
a new release version/tag if artifact identity changed. If PyPI accepted an
artifact, never overwrite it; publish a new patch version.

## Success Criteria

- Poetry 2.1.1 reports no deprecated package-metadata warnings.
- Every authoritative package version and lock reference is `0.3.0`.
- PyPI artifacts pass strict rendering, metadata, alias, and version checks.
- CI publication is impossible from an unmerged feature commit or manual
  version input.
- README support claims match code and service-backed test evidence.
- The release PR does not tag or publish the package.
