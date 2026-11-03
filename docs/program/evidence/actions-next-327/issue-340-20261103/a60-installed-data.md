# Installed a60 immutable Data Package/Run

The retained a60 Runtime wheel `actions-runtime-1.1.0a60` SHA-256
`b4b039a47091eb2808c51ea9c3b8117c0c0f4d700c066d87dfe0321b7bcec0b7`
was built from source `642c6d3f62c2d271d33459553ef560a10f283f1f`, tree
`1ed445d6a3d77ef51ca705789a62bb7638a07897`. Its separate locked
`data-duckdb` consumer and candidate module origins were checked by the harness.
The prepared RCC 18.19.3 receipt and package manifest matched their retained
SHA-256 values `62b36982a64f5985f2f5d9798abbfb0be228861534f9784ce532cd2efafcc5d0`
and `a17d5208f646fa6741ce99cbeca6a1dd37c5cbc0bb752b8c6087b0bdbf823807`.

A supervised real-compiler and generated-RCC test passed: **1 passed in 35.82s**.
It compiled and admitted one immutable Package with CSV and Parquet logical
requirements, registered both sealed DuckDB providers, selected them in one
Deployment, admitted and executed an ordinary standalone Run through the
existing guarded logical publication adapter, and read back four authorized
sealed outputs. Both scans returned the expected synthetic rows; the test
checked the Package and Runtime Plan identities, one Run and Attempt, output
hashes and sizes, and refusal of a duplicate execution on the same fence.
The Run was `8bc41be4-92fc-4093-8737-4ca20e518a41`; Attempt
`986f8ff6-5d34-4705-92d7-27d3723f92d5`, epoch 1, succeeded. The synthetic
`generated-action-result.json` was 306 bytes, SHA-256
`fd994dd80a10a79958a8d459a5a91b8a320d65b0b8b8ed878c6a2fe204b96660`.

The corrected harness SHA-256 is
`03b5b5ba0847398c4413195ecf6189471defeae9b9c458d11260a96029a64747`;
the passing log SHA-256 is
`da765d68f3c1409032d732c15b8466ac2a614ec492377e8756a397cf2a2ad11a`.
Both are retained locally under
`/workspace/327-probes/a60-data-run-standalone-20261103/`. The outer
pidfd/subreaper supervisor returned PASS, command exit 0, and no remaining
owned processes. The capacity guard recorded minimum 12,483,379,200 bytes
free, above the unchanged 10 GiB floor plus 48 MiB guard.

Two earlier attempts remain failures. The original harness
`0f0ccc79a5e182999bda66a3abfe0dd7a883be89dec5017d0f90c804e8e31530`
stopped on the second provider setup because it omitted the current catalog CAS
pointer; no Package/Run test ran. A first corrected harness
`9e2662781e95c71bde7f1f9e6e729d00a68f78a31238c6c26758019ade480a75`
completed provider setup and real compilation but failed before generated-action
launch because it passed the bare output service without the logical-domain
publication guard. The successful harness previews the current catalog pointer
for each configuration and uses normal `StandaloneActionExecution` admission
and its guarded output adapter. It keeps the test assertions intact and uses a
fresh synthetic fixture root; earlier fixture state was retained.

This is Linux installed-component evidence for the stated a60 bytes and source.
It does not qualify #340's subsequent source changes, PostgreSQL parity,
restart/recovery, actual ChatGPT, or full release acceptance. The test's local
SQLite authorizations are disposable synthetic fixture data; no operator
credential, PostgreSQL role or security setting was created.

Upstream disposition: none; the two failures were harness composition errors.
