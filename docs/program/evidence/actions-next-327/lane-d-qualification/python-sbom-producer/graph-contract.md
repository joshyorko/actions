# Producer graph semantics: 29 edges across 15 nodes

Producer commit bcc68f0e is unchanged. Qualification remains FAIL. This is an
evidence-only follow-up; no checker, producer, dependency or release-hook edit.

## Verified supported behavior

[Versioned CLI documentation](https://cyclonedx-bom-tool.readthedocs.io/en/v7.5.0/usage.html)
exposes no extra-selection/marker-filter option for `environment`. Its `poetry`
command supports extras/groups but analyzes project manifests; it cannot replace
measurement of an explicit installed consumer. `--pyproject` supplies PEP 621 root
metadata, not marker-selection context. `--validate` validates document format;
it does not establish selected-profile graph equality.

Installed pinned source `cyclonedx_py/_internal/environment.py` lines 203–207
parses all distribution requirements; lines 226–243 select any requirement target
present in the installed component map, omit self-links, and register edges.
There is no marker evaluation or specifier check in this dependency loop.
Source SHA256: 3e78756a5d0754c6c2818ab6c55ce0f4522b6c981dd2b7d1a906cad9ef5fd6a7.
An independent reconstruction from captured pip metadata matches all 68 exported
dependency nodes exactly, including bootstrap pip. Thus “declaration graph” here
means declared requirements projected onto installed target names, not all possible
declarations, install history, an active profile, or a runtime call graph.

`edge-marker-analysis.json` retains the exact Requires-Dist strings, environment,
selected extras, marker results, activating declared extras and target versions.
All 29 targets are installed and satisfy their specifiers. Every mismatched edge
is inactive for the selected profile. 25 arise from unselected extras; four from
Python <3.11 conditions on consumer Python 3.12.15. No expected active edge is
missing. Active selections are Runtime[data-duckdb], psycopg[binary], pyjwt[crypto].

## Proposed engineering contract (not implemented)

Retain the unmodified schema-validated producer export and its SHA256 as the raw
installed-inventory/declaration projection. Keep the exact active graph gate and
its FAIL receipt as historical evidence. Add an explicitly named two-view
qualification only after integrator approval, with independently enforced rules:

1. Exact installed component/version parity and existing lock/closure checks.
2. Exact raw graph equality to all installed metadata declarations whose targets
   are installed, excluding self-links as pinned producer does. No broad superset
   acceptance: unexplained added edges and missing declaration edges fail.
3. Independently recompute active edges using captured interpreter markers,
   explicit root extras and transitive extra propagation, checking target versions.
   Call this a metadata-resolved selected-profile graph, not observed execution.
4. Explain every raw-minus-active edge by its exact inactive marker(s); require
   every active edge in raw. Retain a deterministic full reconciliation including
   target presence/version, source extras and all matching Requires-Dist entries.
5. Bind raw SBOM, inspection, environment/extras, locks, wheel and reconciliation
   by hashes in the existing release evidence manifest. The active sidecar remains
   ordinary evidence JSON, never mislabeled as producer output or a CycloneDX BOM.

This keeps standard CycloneDX bytes untouched. If a downstream consumer needs a
standard active-profile BOM, produce a separately identified derived CycloneDX
1.6 document using the pinned library, independently schema-validate it and apply
the existing exact active-graph gate. Give the derivative its own identity and
explicit provenance, retaining the raw export. Link the raw SBOM and active JSON
through standard externalReferences (type bom/evidence with hashes), and describe
the measured profile in metadata properties. This is a further allocated producer
change, not permission to filter the existing export in place.

The [CycloneDX 1.6 schema](https://raw.githubusercontent.com/CycloneDX/specification/1.6/schema/bom-1.6.schema.json)
has no conditional marker field on a dependency edge. Component `scope` cannot
encode per-edge activation and must not mark these installed packages optional
merely because one incoming edge is inactive. Keep installed inventory intact;
none of this proves runtime reachability or absence of vulnerabilities.

Required mutation controls for any new two-view gate: unexplained added edge,
removed declaration edge, activated extra without graph change, changed Python
marker environment, wrong installed version, absent target, duplicate/dangling
refs, substituted input hashes, and stale reconciliation. Existing strict tests
stay unchanged. Proposed shared hook remains integrator-owned.

## Documentation / upstream disposition

Exact proposed canonical guide addition: “Preserve raw CycloneDX environment
exports separately from selected-profile dependency evidence. For cyclonedx-bom
7.5.0 the raw graph projects declared requirements onto installed names without
marker evaluation. Validate both views and every difference; schema validity,
installed target presence and component scope do not establish edge activation.”

Evidence: captured metadata, per-requirement marker evaluation and exact 68-node
projection reconstruction. Uncertainty: selected extras are profile inputs, not
recoverable installation history; no runtime call-tracing claim. Upstream defect
not established by supported CLI documentation. No external report authorized
or filed; potential reporting remains draft-only after contract/source review.

## Exact edge inventory

All targets below are installed; all edges are inactive in this selected profile.

| Source | Target (installed version) | Activating extras or marker |
|---|---|---|
| actions-work-items | psycopg 3.3.4 | postgres |
| actions-work-items | redis 5.3.1 | all, redis |
| actions-work-items | requests 2.34.2 | all, yorko |
| cryptography | certifi 2026.7.22 | test |
| cryptography | click 8.4.2 | pep8test |
| cryptography | typing-extensions 4.16.0 | python_full_version <3.11 |
| fastapi-slim | python-multipart 0.0.32 | all, standard, standard-no-fastapi-cloud-cli |
| fastapi-slim | pyyaml 6.0.3 | all |
| fastapi-slim | uvicorn 0.38.0 | all, standard, standard-no-fastapi-cloud-cli |
| httpcore2 | anyio 4.14.2 | asyncio |
| httpx2 | click 8.4.2 | cli |
| jsonschema | idna 3.18 | format, format-nongpl |
| msgspec | attrs 26.1.0 | dev, test |
| msgspec | pyyaml 6.0.3 | dev, test, yaml |
| multidict | typing-extensions 4.16.0 | python_version <3.11 |
| oauthlib | cryptography 46.0.7 | rsa, signedtoken |
| oauthlib | pyjwt 2.13.0 | signedtoken |
| psycopg | anyio 4.14.2 | test |
| pyjwt | typing-extensions 4.16.0 | python_version <3.11 |
| redis | cryptography 46.0.7 | ocsp |
| redis | requests 2.34.2 | ocsp |
| sse-starlette | pydantic 2.13.4 | examples |
| sse-starlette | uvicorn 0.38.0 | examples, uvicorn |
| starlette | python-multipart 0.0.32 | full |
| starlette | pyyaml 6.0.3 | full |
| uvicorn | pyyaml 6.0.3 | standard |
| uvicorn | typing-extensions 4.16.0 | python_version <3.11 |
| uvicorn | watchfiles 1.2.0 | standard |
| uvicorn | websockets 15.0.1 | standard |
