# A57 source-locked `data-duckdb` consumer gate

New isolated CPython 3.12 consumer, candidate A57 source commit `bde511d2ba6318d0b100547cc6e777e53b9ebc80`, tree `58e3beed765765e13724928d26acefb729d8aeab`. It uses the source `action_server/poetry.lock` SHA-256 `00de76d27a833b63225ce37b5d633b83a761d00bad63f315eaeec77dc9de4c53`, the same 68 main-group lock constraints as the base profile (SHA-256 `ce77892478fff64afbd8cb71885c3832097e2514858bbe5223fe1d241d423758`), and the same three immutable candidate wheels:

- Runtime 1.1.0a57: `07a144f6200ea6bce8d52e14244aef2889e2c15cd52472a758381648fb693efa`
- Core 1.1.0a8: `42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f`
- Work Items 0.5.0a2: `72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb`

The only selected Runtime extra is `data-duckdb`. Public dependency resolution used the inherited proxy/CA environment and exact lock-derived constraints. Install and `pip check` passed. The consumer contains DuckDB 1.4.1 and MCP/MCP Types 2.0.0; `pip check` reports no broken requirements. `consumer-ready.json` records 66 installed distributions including pip and the selected profile.

The existing task-local CycloneDX 7.5.0 Poetry tool environment from the base profile was reused read-only. The existing SBOM producer completed, verified the installed Runtime files against the exact wheel (excluding pip-rewritten RECORD), and captured stable before/after consumer metadata. Its validated reproducible CycloneDX 1.6 raw installed inventory has SHA-256 `e26c7894830fc06ff357aace38c47067c64ccd3c7167a00746355da814e21092`. Receipt: `sbom-output/receipt.json`; source lock identity matches the A57 lock above.

The producer’s lock-aware active closure contains 65 distributions (excluding pip). Selected extras are Runtime `data-duckdb`, transitive `psycopg[binary]`, and transitive `pyjwt[crypto]`. The DuckDB package component is present at locked 1.4.1. The SBOM is the raw declared environment inventory; it is not the active profile graph.

The existing strict qualifier wrote `strict-qualification.json` and exited 1 on `CycloneDX graph differs from active resolved dependencies`. Component names and versions match the resolved lock-qualified closure. The SBOM graph includes 29 additional inactive target edges: 25 from unselected extras and 4 from Python-version markers inactive on CPython 3.12. The full exact Requires-Dist reconciliation remains in `sbom-output/declaration-reconciliation.json`. Preserve this strict failure. No filter, derived BOM, extra removal, or gate relaxation was applied; the integrated contract keeps raw declaration and selected active views separate.

The A57 delivered base consumer, its constraints/wheels, and Library bundle were not modified. No Runtime server, Actions execution, provider service, test suite, RCC/native package, aggregate QA, build, host UI, publication, or deployment was run. Disk remained at least 17 GiB free, above the 10 GiB floor. The preparation and producer supervisors passed with no surviving owned processes; strict-qualifier supervisor retained the expected command exit 1 and no surviving owned processes.

## Canonical documentation proposal and upstream disposition

No new canonical rule is needed beyond the prior A57 base-profile evidence: `docs/skills/repository-operations.md` already requires same-lock constraints and separates the raw export from active closure. Proposed evidence addition to that guide’s frozen-lock section: record that the `data-duckdb` profile must be qualified independently with the selected extra passed to the same active-closure checker; the raw CycloneDX edge projection still needs its complete inactive-edge reconciliation. Evidence: the base profile and this second A57 profile both used the exact lock and producer, each resolved cleanly, and each retained a strict raw-edge mismatch, while this profile adds the explicitly locked DuckDB 1.4.1 component and Runtime extra. No canonical file was edited.

Upstream disposition: none. The raw graph behavior matches the pinned producer contract; no upstream defect was identified.
