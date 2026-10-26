# Independent source-only review

Disposition: no blocking defect found for the parent-authorized independent PUBLIC rebuild instructions. This is not approval to export the previously denied archive and not evidence that a build or transfer succeeded. No RCC, build, import, server, PG or transfer was executed during review. Only scripts, dependency metadata and source-hashes in this folder were read.

Verified boundaries:

- prepare-public-producer.py accepts candidate-base, fresh compiler-root and fresh export-root; it has no previous-cache/archive input. It reads the already obtainable a44 candidate wheel/source identities, copies only the exact owned Core wheel and verification script, and invokes standard RCC18.19.3 env publish with a fresh HOME/ROBOCORP_HOME/tmp. No producer trust is read or copied.
- The compiler path is exactly /tmp/actions327-a44-offline-v1/compiler, absent initially, with no symlink ancestors. Initial reserve is4.25GiB, compiler allocation cap2GiB, running free floor1GiB; bounds are sampled, not a proof of an unsampled peak. Export is on the same filesystem and separate from compiler root. Logs/timeouts/owned child cleanup remain bounded. These are this explicit managed profile's guards, not a relaxation of the original strict recipe.
- qualify-export.py compares exactly26 conda name/version/build/sourceURL/SHA records and19 Python name/version/METADATA hashes to PUBLIC-DEPENDENCIES.json. It verifies87 Core payload members against the exact owned a44 wheel and checks both expected catalog identities, fixed-root paths and relative internal links. Python METADATA hashes are explicitly not third-party wheel payload hashes; retain that scope.
- Qualification precedes supported holotree export. Only the newly generated archive's measured SHA/size populate target validator/preparation scripts. The validator permits only expected catalog entries and content-addressed library entries, bounds decompressed size/catalog JSON, rejects archive traversal and escaping links; no trust directory is permitted.
- Target template requires its own absent fixed root, verifies generated archive pin/layout before strict holotree import, then env publish --no-build creates target-local preparation/trust. It verifies the exact Core wheel and child context isolation again. No trust copying or network/security override is introduced.

Static evidence: all five Python files parsed with ast.parse without execution; PUBLIC-DEPENDENCIES inventory contains26 conda and19 Python entries; all six source-hashes.json entries matched at review. README was being finalized independently; review applies to hashed scripts/manifest inspected, not future edits. Failed identity, budget, dependency or catalog validation must stop the new build; never substitute the denied archive as fallback.

Documentation improvement — proposed exact canonical addition to docs/skills/repository-operations.md:

“An authorized independent public rebuild must have no input path to a denied artifact. Recreate the environment in a fresh owned root with standard preparation, verify declared public dependency identities and exact owned wheel payloads before supported export, then derive archive pins from that new output. Targets verify the exported catalog/library boundary and create their own trust. Public Python METADATA equality is not wheel-payload equality; sampled capacity guards and source review are not completed build or transfer evidence.”

Evidence: prepare-public-producer.py, qualify-export.py, validate-public-cache.template.py, prepare-offline-managed.template.py, verify-core.py, PUBLIC-DEPENDENCIES.json and source-hashes.json. Remaining uncertainty: actual public resolution may drift and fail closed; real capacity/build/target materialization remain NOT_RUN. No shared source or canonical guide mutated.

Upstream disposition: none. No external defect or mutation established.
