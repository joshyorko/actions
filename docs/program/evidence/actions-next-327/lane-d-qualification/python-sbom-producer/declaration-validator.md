# Independent declaration validator

Adds only `action_server/scripts/qualify_declared_graph_327.py` and dedicated
`devutils/tests/test_declared_graph_327.py`. API:
`explain_declaration_graph(sbom, inspection, qualification)` accepts parsed raw
CycloneDX, captured pip inspection and the separately validated selected-profile
qualification. It returns evidence only, with `release_admission: not evaluated`.
The caller must obtain qualification through the existing lock/closure validator;
this API does not independently validate lockfiles or artifact hashes.

Exact observed graph must match the pinned producer's installed declaration
projection, including explicit leaf nodes and bootstrap pip. Inventory, references,
node and edge uniqueness are checked. Every raw-minus-active requirement must
have a false marker under the selected profile; explanations retain original
Requires-Dist strings, selected extras and installed target version/specifier
results. Inactive version mismatch is reported as evidence, not confused with an
active constraint failure. Inputs are not mutated. No producer/gate call site or
existing test was changed. Original bcc68f0e and its failed receipt stay intact.

Validation through existing package-local Poetry/RCC preparation and writable
cache environment:

```bash
cd devutils
poetry run pytest tests/test_declared_graph_327.py \
 tests/test_consumer_sbom_graph_327.py tests/test_consumer_inventory_327.py \
 --junitxml=/workspace/lane-d/receipts/declaration-tests.xml
poetry run ruff check ../action_server/scripts/qualify_declared_graph_327.py \
 tests/test_declared_graph_327.py
poetry run isort --check-only tests/test_declared_graph_327.py
```

23 tests passed. Actual retained export: 68 declaration nodes, 29 explained edges,
active_graph_equal=false. Seven mutation negatives cover added edge, missing
edge, dangling reference, duplicate node, wrong version, activated extra and
changed Python environment. Mutation controls are synthetic changes to captured
real evidence, not new installed-consumer runs. Stdout/XML retained compressed.

Integration: optional independent evidence API only; the subsequently approved dual-evidence integration is documented in
../python-sbom-dual/README.md. Rollback removes these dedicated files and
evidence. No migration or dependency change. No native/platform execution claim.

Canonical guide delta proposed to integrator: “Use declaration projection
validation as independent evidence, never as a replacement for selected-profile
lock closure or exact active-graph validation. Reject unexplained differences;
retain original requirement markers and distinguish evidence validation from
release admission.” Learning: exact declaration parity is reproducible without
editing raw SBOM or weakening active tests. Evidence: 23 tests and retained real
producer export. Uncertainty: profile inputs do not prove install history or
runtime reachability. Upstream disposition unchanged: no established upstream
violation, no external report or upload.
