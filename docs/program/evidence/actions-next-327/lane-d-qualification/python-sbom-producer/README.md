# Installed Python SBOM producer — qualification blocked

This follow-on implements the approved optional devutils producer allocation on
parent `fffc12834ba10eb8d9f5ee976b7e7c03b1b1d216`. The earlier proposal directory
records the pre-allocation state. No release hook, Runtime dependencies, version,
workflow, signing or publication changed.

## Interface and integration

Run from devutils with the prepared RCC 18.19.3 / Poetry 2.1.1 toolchain:

```bash
export PATH=/workspace/lane-d/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin:$PATH
export POETRY_CACHE_DIR=/workspace/lane-d/cache/poetry
export XDG_CACHE_HOME=/workspace/lane-d/cache
poetry lock
poetry install --with sbom
poetry run python ../action_server/scripts/produce_consumer_sbom_327.py \
 --consumer-python /workspace/lane-d/clean-sbom-consumer/bin/python \
 --runtime-wheel /workspace/lane-d/wheels/actions_runtime-1.1.0a38-cp312-cp312-linux_x86_64.whl \
 --expected-sha256 34f5b7c1db29d4def4ba84214d225f6b82d037fa39e3b819eab6fe1ff15898ce \
 --expected-runtime 1.1.0a38 --runtime-lock ../action_server/poetry.lock \
 --extra data-duckdb --output-dir /workspace/lane-d/producer-qualified
poetry run pytest tests --junitxml=/workspace/lane-d/receipts/producer-full.xml
poetry check --lock
```

Output directory must be absent with an existing parent. Producer is separate
from the explicit installed consumer. Inputs are the candidate wheel, caller
expected SHA/version, matching Runtime lock, selected extras and consumer Python.
Wrapper captures fresh isolated pip inspection before/after, verifies 319 wheel
members installed under consumer prefix (excluding pip-rewritten RECORD), retains
both locks with hashes, unmodified standard output `python-consumer.cdx.json`,
resolved graph, subprocess stdout/stderr and `receipt.json`. Timeout output is
retained. Exit zero requires strict component and active dependency graph parity;
any failure retains its receipt and exits nonzero. Use a fresh directory to retry.
Caller-supplied digest is not a signature or source authority. These before/after
observations are not an atomic snapshot against a hostile concurrent mutator.

Integrator owns the final release-preparation hook. Do not admit this failed
receipt into a release: the graph contract decision below is pending. Rollback
this isolated commit to remove optional tooling/wrapper/tests; no schema or
consumer environment migration is involved.

## Actual evidence

- PASS: pinned cyclonedx-bom 7.5.0 generated and schema-validated CycloneDX 1.6 JSON;
  68 components and 68 dependency nodes including bootstrap pip. Producer uses
  `environment`, explicit consumer Python, `--output-reproducible --validate`.
- PASS: actual consumer inventory/lock closure of 67 Runtime packages, selected
  DuckDB and psycopg binary/pyjwt crypto extras; before/after metadata unchanged,
  both installed wheel payload checks passed (319 members).
- FAIL: strict graph qualification exits 1. Fifteen package nodes have extra
  declared optional/inactive edges; no expected active edges are missing.
  `edge-differences.json` records every mismatch. The producer document is retained
  unchanged. No filtering or synthetic graph replacement was applied.
- PASS: 307 devutils tests; XML/stdout retained. Three new wrapper controls verify
  explicit format/target, no output overwrite and wrong producer version rejection.
  Existing synthetic graph mutation controls remain synthetic, not producer proof.
- PASS: Poetry lock validation, ruff check and isort check of new tests. Lock
  comparison removed no prior package/version pair; all 36 newly introduced
  package/version alternatives belong only to the optional sbom group.
- Tooling note: attempted `poetry run black` was unavailable; repository-provided
  `ruff format` succeeded. No host formatter/dependency fallback was installed.

Artifact source remains original da928b69e0558917c3e88af9297ddfd3bec818e8 Runtime
1.1.0a38 wheel, NOT the frozen first combined candidate or this newer source.
The actual SBOM digest is in receipt.json. SBOM is Python-only: it does not cover
embedded RCC/Go/native/OS dependencies. Native Linux tools and local Docker are
available but no native/image SBOM gate ran here. Windows/macOS native gates are
unavailable and require real authorized runners; no emulation pass claimed.

## Pending contract and upstream disposition

The local strict checker describes active selected dependencies. The supported
producer emits a broader declaration graph. This is a concrete integration
contract mismatch, not established evidence of an upstream bug. Integrator must
decide whether to retain the raw declaration SBOM plus independently checked
active graph, or require another supported export mode. Do not silently weaken
exact graph checks to obtain a green receipt. No external issue/upload authorized
or performed. Any eventual upstream issue remains a draft until source/contract
analysis establishes a defect and publication is authorized.

## Exact canonical-guide delta proposed to integrator

Append to the repository-operations release qualification guide:

> Produce the Python consumer SBOM using the optional devutils sbom group and
> an explicit separate installed consumer interpreter. Retain the raw validated
> CycloneDX document, wheel/input digests, lock snapshots, selected extras, and
> before/after installed inspection. Schema validity and component equality do
> not prove active dependency graph parity: cyclonedx-bom 7.5.0 environment output
> can include inactive optional edges. Preserve nonzero graph qualification and
> resolve that contract before release admission; never rewrite raw SBOM edges
> to manufacture a passing receipt. Python SBOM evidence excludes native/OS
> components and does not substitute for native platform acceptance.

Learning/evidence: actual 68-node producer export and 15-node differences retained
here. Uncertainty: broader graph may be intentional upstream declaration behavior;
no violation of upstream documentation has been established.
