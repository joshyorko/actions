# Clean installed Python consumer and existing SBOM boundary

Exact Runtime artifact: retained da928b69 production-source a38 Linux wheel,
SHA256 `34f5b7c1db29d4def4ba84214d225f6b82d037fa39e3b819eab6fe1ff15898ce`.
This does NOT qualify the frozen combined Canvas candidate or newer DB follow-ons.
Candidate Core/Work Items/HTTP Helper wheels were built package-locally through
prepared RCC 18.19.3/Poetry 2.1.1; their hashes and source lock hashes are retained.
No version/lock/workflow changes or public publication occurred.

## Existing supported exporter, not a replacement framework

The current supported CycloneDX producer is frontend `cyclonedx-npm` via
`sbom:runtime`/`sbom:canvas`, using `--package-lock-only --output-reproducible`.
Those are npm lock graphs including optional/build dependencies, not resolved
Python environments. Source/locked-toolchain inspection found no installed
Python SBOM exporter. The actual clean installed CLI `--help` succeeds and exposes
no SBOM command. Historical `consumer-sbom.cdx.json` is CycloneDX 1.6 with 68
components and no dependency edges; it names Runtime 1.0.4/Core 1.0.3. It must
not be relabeled as a38 evidence. No new CycloneDX generator was invented.

## Executed clean consumer

`prepare.py` verifies cached dependency-wheel SHA256 against Runtime poetry.lock
before admission to an owned wheelhouse. Locally built Actions wheels are clearly
separated from those lock-archive authorities. It writes exact version constraints.
From prepared package Poetry, a new venv was created at
`/workspace/lane-d/clean-sbom-consumer`. Then:

```bash
/workspace/lane-d/clean-sbom-consumer/bin/python -I -m pip install \
 --no-index --find-links /workspace/lane-d/resolved-wheelhouse \
 --constraint /workspace/lane-d/consumer-constraints.txt \
 'actions-runtime[data-duckdb]==1.1.0a38' \
 --report /workspace/lane-d/receipts/consumer-install-report.json
/workspace/lane-d/clean-sbom-consumer/bin/python -I -m pip inspect
/workspace/lane-d/clean-sbom-consumer/bin/python -I -m pip check
```

Install passed offline. `pip check`: **No broken requirements found**. Pip inspect
reports 68 distributions: **67 Runtime dependency-graph packages plus bootstrap pip**.
The dedicated reader validates all dependency versions against the lock, traverses
active requirement markers and transitive extras, rejects missing/unlocked/duplicate
or extraneous packages, and records resolved dependency edges. Selected extras:
Runtime `data-duckdb`, psycopg `binary`, PyJWT `crypto`. Actual installed providers:
DuckDB **1.4.1**, psycopg/psycopg-binary **3.3.4**. Imports resolve inside the fresh
consumer; real in-memory DuckDB `SELECT 42` passes. No PostgreSQL service was
started for this gate; import/closure is not PostgreSQL engine acceptance.

From prepared `devutils` package Poetry:

```bash
poetry run python ../action_server/scripts/qualify_consumer_inventory_327.py \
 --inspect /workspace/lane-d/receipts/consumer-inspect.json \
 --lock ../action_server/poetry.lock --expected-runtime 1.1.0a38 --extra data-duckdb \
 --sbom ../docs/program/evidence/actions-next-327/consumer-sbom.cdx.json \
 --output /workspace/lane-d/receipts/consumer-qualified-final.json
```

Resolved lock/graph checks pass. **SBOM comparison rejects, exit 1**, retaining the
resolved receipt: historical CycloneDX components do not match actual consumer.
Initial diagnostic version recorded rejection but exited zero; the final qualifier
corrects that exit status. The retained historical file was neither edited nor
uploaded. Even matching components would not qualify SBOM graph edges, licenses,
vulnerabilities, signatures or complete binary contents.

Focused tests: **21 passed** across consumer inventory and corrected wheel binding.
Consumer controls cover transitive extras, undeclared extras, missing/unlocked/
duplicate packages and missing/stale/duplicate CycloneDX components.

## Exact next shared-scope proposal; no shared edit applied

If Python CycloneDX export is required, allocate a separately reviewed locked
CycloneDX Python producer under `developer` toolchain/task ownership, then connect
its environment export to the existing Runtime release preparation evidence.
Review exact producer/version/schema and dependency changes before implementation.
Keep npm lock SBOMs unchanged and bind Python SBOM to the selected wheel, profile,
resolved consumer, lock and install archive hashes. No such tool/dependency or
workflow addition is authorized or implemented by this qualifier.

Canonical-guide delta proposed to integrator:

> Frontend package-lock CycloneDX and installed Python consumer inventories are
> different scopes. Require a fresh profile-specific pip inspection, lock-version
> and archive-hash checks, active-marker/transitive-extra closure, and component
> comparison before admitting a Python consumer SBOM. Reject stale SBOM components
> with a nonzero gate result. Do not call dependency declarations or a historical
> component list a current resolved SBOM; absent exporter/graph proof remains open.

Evidence: pip inspect/install report, cached-wheel lock hashes, resolved edges,
provider probe, CLI help and rejection receipt. Removed ambiguity: frontend SBOM
exports or old consumer components qualify current Python resolution. Remaining:
reviewed Python exporter, current CycloneDX dependency graph/contents, Windows,
macOS, native/image inventories and later combined candidates.
Upstream disposition: none; missing producer integration is a local capability gap.
Rollback removes dedicated qualifier/tests/evidence only; no production state.

Full affected devutils suite: **297 passed, zero skips**. Changed-file Ruff,
formatter, Isort and diff checks pass. Existing index commits remain unchanged.
