# A57 source-locked consumer inventory and SBOM gate

This is a new isolated CPython 3.12 consumer for A57. Candidate source: commit `bde511d2ba6318d0b100547cc6e777e53b9ebc80`, tree `58e3beed765765e13724928d26acefb729d8aeab`. The source `action_server/poetry.lock` SHA-256 is `00de76d27a833b63225ce37b5d633b83a761d00bad63f315eaeec77dc9de4c53`. Main-group lock constraints (68 unique package/version pins) SHA-256: `ce77892478fff64afbd8cb71885c3832097e2514858bbe5223fe1d241d423758`.

Candidate wheel hashes were checked before install and again by the existing wheel inventory producer:

| Wheel | SHA-256 |
|---|---|
| Runtime 1.1.0a57 | `07a144f6200ea6bce8d52e14244aef2889e2c15cd52472a758381648fb693efa` |
| Core 1.1.0a8 | `42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f` |
| Work Items 0.5.0a2 | `72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb` |

`pip install` used those three explicit candidate wheels with constraints derived from the source A57 lock. Public dependencies resolved to locked versions; `pip check` passed. The installed profile selects no Runtime extras (`[]`); this is the base Runtime profile. The active transitive closure includes `psycopg[binary]` and `pyjwt[crypto]`. The optional Runtime `data-duckdb` extra and full-provider extras are not qualified by this profile. Retained evidence includes the install report/log, `pip inspect`, pip-check result, source lock/constraint hashes, and a machine-readable ready receipt.

The existing developer Poetry environment lacked `cyclonedx-bom`, so only the declared `devutils` SBOM group was synced with `poetry install --only sbom --no-root --sync` to a new task-local Poetry environment. The pinned producer version 7.5.0 was verified there; the repository’s existing `.venv` and the A57 delivered consumer were not changed. Prepared-tool logs and supervisor receipts retain the task-local environment identity. Disk was 18 GiB free before and after the operations, above the 10 GiB campaign floor.

The existing `produce_consumer_sbom_327.py` completed. It confirmed the installed Runtime files match the exact wheel (excluding pip-rewritten RECORD), generated a reproducible validated CycloneDX 1.6 inventory, and captured pip inspection before/after without consumer metadata changes. Receipt: `sbom-output/receipt.json`. SBOM SHA-256: `e3e7165e5f18e99c1d853e846ac65e1acf58f918df1cfe3e2308bf220219230b`. Runtime lock SHA in that receipt matches the source lock above. The resolved active graph contains 64 distributions; its Runtime extra selection is empty, with transitive `psycopg[binary]` and `pyjwt[crypto]` recorded separately. SBOM output is declared dependency inventory, not the active dependency graph.

The existing `qualify_consumer_inventory_327.py` strict check was then run against the generated SBOM and source lock. It exited 1 and retained `strict-qualification.json`: component names/versions matched the locked resolved inventory, but exact dependency-edge equality failed with `CycloneDX graph differs from active resolved dependencies`. The producer reconciliation explains 29 inactive declaration edges (25 from unselected distribution extras and four Python-version markers not active on CPython 3.12). These raw edges are part of CycloneDX 7.5.0's declared installed-environment projection; they are not evidence of active edges. Keep the strict failure intact. No filtering, gate relaxation, dropped dependency, or alternate SBOM is used.

The preparation attempt that initially rejected the already-created task-local evidence directory, the failed Poetry path probe while RCC's active virtualenv was visible, and the producer invocation with `-I` (which hid its sibling qualifier modules) are preserved in their supervisor logs. Corrected commands were rerun under the same outer-host supervisor; successful receipts show exit zero and no surviving owned processes. The strict qualifier's exit 1 is the substantive retained result.

The unrelated older A57 consumer, its constraints/wheels, and Library bundle were untouched. No Runtime service, execution, Library upload, publication, host acceptance, or deployment was performed. The only platform qualified here is Linux CPython 3.12.

## Canonical documentation proposal and upstream

Propose adding a short operational note to `docs/skills/repository-operations.md` next to the frozen-lock consumer gate: “Retain a CycloneDX environment export as the raw declared inventory. For cyclonedx-bom 7.5.0, declared requirements projected onto installed components can include inactive extra/marker edges; preserve the strict active-edge comparison failure and reconciliation. A fresh lock-consistent consumer and matching components do not make the raw declaration graph an active-profile SBOM.” Evidence: this exact A57 lock-bound consumer, 7.5.0 producer receipt, strict qualifier exit 1 and 29-edge reconciliation, plus the existing a38 graph contract which records the same producer behavior. No canonical file was edited.

Upstream disposition: none. The observed behavior matches the pinned producer’s documented declaration projection; no upstream defect was established.
