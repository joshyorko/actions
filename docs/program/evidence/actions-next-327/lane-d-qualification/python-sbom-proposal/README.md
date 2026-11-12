# Smallest Python SBOM producer allocation proposal

No producer/dependency/workflow installation or edit has been made. Existing
commits remain stable. The only implemented follow-on is the dedicated reader's
graph validation plus its synthetic mutation tests.

## Proposed producer and exact dependency scope

Use maintained `cyclonedx-bom==7.5.0`, CLI `cyclonedx-py`, in an optional Poetry
`sbom` group in **devutils/pyproject.toml**; regenerate **devutils/poetry.lock**
through pinned Poetry 2.1.1. The package's declared Python range is >=3.9,<4;
use `python = ">=3.9,<4"` on this optional tool dependency to retain devutils'
existing broader Python declaration. Do not add it to Runtime dependencies or
the inspected clean consumer. Resolve and review all transitive hashes in the
lock before installation; no ad hoc host pip tool is needed.

Proposed TOML (not applied):

```toml
[tool.poetry.group.sbom]
optional = true

[tool.poetry.group.sbom.dependencies]
cyclonedx-bom = { version = "7.5.0", python = ">=3.9,<4" }
```

Published wheel SHA256:
`a3020e225107214a66cb9c79ae83e3a71640a06d4ff3a0e2f9cb0d238f7061fd`.
Producer metadata retrieved read-only from PyPI is retained. This is a proposed
pin, not proof that its dependency graph or generated output passes our gates.

Versioned command, after allocation and prepared package-local group install:

```bash
poetry run cyclonedx-py environment /absolute/clean-consumer/bin/python \
 --spec-version 1.6 --output-format JSON --output-reproducible --validate \
 --output-file /absolute/owned-evidence/python-consumer.cdx.json
```

Run from devutils so producer dependencies stay outside the consumer. Do not pass
Runtime's Poetry-only pyproject via `--pyproject`: that option expects PEP 621.
Do not use `--short-PURLs`, disable validation, or fabricate optional edges when
output differs. The actual generator must pass component and active-extra graph
comparison against pip inspection. Preserve its unmodified output and diagnostics.

References: [7.5.0 CLI documentation](https://cyclonedx-bom-tool.readthedocs.io/en/v7.5.0/usage.html),
[versioned PyPI metadata](https://pypi.org/pypi/cyclonedx-bom/7.5.0/json).

## Dedicated wrapper/test scope and integration hook

After allocation, add only
`action_server/scripts/produce_consumer_sbom_327.py` and
`devutils/tests/test_consumer_sbom_producer_327.py` initially. The wrapper takes
explicit consumer interpreter, retained pip inspect, wheel digest, lock digest,
profile and absent output directory; invokes the pinned producer; validates
components and dependency edges with the existing dedicated qualifier; and binds
output bytes to those inputs in a receipt. Never import the target environment's
packages into the producer process or call a service/publication API.

Proposed shared hook, separately allocated:
`action_server/scripts/runtime_release_button.py::prepare`, immediately before
its final `result['files']` inventory construction, admits validated
`evidence/python-consumer.cdx.json` and its source/profile/input binding receipt.
The existing complete file manifest then covers their digests. Do not edit the
publisher or create a separate manifest authority. Any eventual workflow task
installation in `.github/workflows/runtime-release-prepare.yml` remains integrator
owned; no version/credentials/signing/publication change is requested.

## Graph readiness work actually executed

`compare_cyclonedx_graph` now requires unique component refs, explicit package
dependency nodes, no dangling/duplicate edges and exact active resolved edges.
The CLI's eventual positive result requires both components and graph, rather
than component equality alone. Bootstrap pip is explicitly outside the Runtime
graph. A metadata application-root node can be distinct but cannot substitute
for package dependency nodes.

Seven synthetic controls use the captured real 67-package expected inventory:
positive graph, missing selected DuckDB edge, extra edge, dangling ref, duplicate
component ref, missing leaf node and duplicate node. **15 focused tests pass**
with the previous eight inventory tests. Synthetic CycloneDX objects exist only
inside tests and are NOT exported/current producer SBOM evidence. Optional
provider identities and real installed dependency receipts remain in the preceding
consumer-closure directory.

## Native/platform reality

| Gate | This environment |
|---|---|
| Linux x86_64 wheels, installed consumer, SQLite, bounded PostgreSQL | Real execution available; prior receipts identify what passed. |
| Linux PyInstaller/native Go wrapper | Tools available: PyInstaller 6.16.0, Go 1.23.6, RCC 18.19.3; native build not run in this slice. Frontend node_modules/build roots absent in this checkout, so prepared frontend build is prerequisite. |
| Local Linux containers | Docker daemon reports linux/x86_64. Owned PostgreSQL ran. Local image build is possible after inputs are provisioned, not yet release-image qualification. |
| Repository container recipe | Only `.devcontainer/Dockerfile` found; includes pinned GHCR uv stage. This is a developer image, not proof of homelab distribution without mandatory GHCR. |
| Windows x64/macOS arm64 native build/start/history | No native runners here. Requires respective authorized runners/CI; emulation/cross-compilation is not a native pass. |
| Signing/notarization, production auth/host acceptance, publication | Operator/explicit authorization gates; no credentials or services used. |

23 GiB available at inspection. RCC version checks must retain task-owned
ROBOCORP_HOME; an initial omitted override produced read-only-home diagnostics,
then the supported override returned 18.19.3 without errors. No policy was relaxed.

## Canonical-guide delta for integrator

> Keep the Python CycloneDX producer in a separate locked tool environment, target
> the exact clean consumer interpreter, and retain raw validated output. Compare
> both component inventory and explicit dependency edges against profile-specific
> installed metadata, including transitive extras. Synthetic graph tests establish
> validator behavior, never producer acceptance. Bind the accepted SBOM and receipt
> through the existing release manifest; absent native runners remain unverified.

Evidence: versioned producer docs/metadata, real 67-package inspection and synthetic
mutation controls. Removed ambiguity: component equality implies graph completeness,
or available build tools imply native qualification. Uncertainty: actual 7.5.0
export behavior (especially selected extras), resolved producer lock, current
native/image acceptance. Upstream disposition: none; awaiting local allocation.

Full affected devutils suite: **304 passed, zero skips**. Ruff, formatter, Isort
and diff checks passed for the two changed Python files. Producer/shared dependency
and release-hook actions are pending allocation, not denied or executed.
