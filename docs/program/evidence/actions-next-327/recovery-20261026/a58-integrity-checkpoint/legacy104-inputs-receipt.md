# Verified public inputs for the Runtime 1.0.4 recovery gate

## Result

The missing published Linux/Python 3.12 Runtime 1.0.4 wheel is available from the canonical published PyPI release and matches the a26 retained wheel SHA-256 exactly. Its exact installed-smoke companion versions are also staged from canonical PyPI and verified. No files were installed or executed.

- Runtime: `actions_runtime-1.0.4-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl`, 14,444,908 bytes, SHA-256 `ab0925ddfbc804d4790b5bd839461310b851c3dedf5f4781e4b4c8472bcf5eba`.
- Core: `actions_core-1.0.3-py3-none-any.whl`, 103,809 bytes, SHA-256 `8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265`.
- HTTP Helper: `actions_http_helper-1.0.3-py3-none-any.whl`, 14,690 bytes, SHA-256 `46ed7ce0e0d3e2e05456d937b5b24bc9dfa0d7d4b98f8119b9fdf00d4fa7e9f9`.
- Work Items: `actions_work_items-0.4.4-py3-none-any.whl`, 62,717 bytes, SHA-256 `488163817f3a2cb969744c1ad7332dc775318d0e755029639fd51d0bffe4ffc0`.

Each downloaded file's local SHA-256 and byte count matched the corresponding official PyPI JSON metadata. Runtime's digest also exactly matches `legacy_wheel_sha256` in `recovery-a26/installed-restore/qualification.json`. The other three wheel hashes match retained release evidence: Core 1.0.3 is recorded in `cloud-foundry-boundary-20261022.json` and `cloud-foundry-storage-20261023.json`; Helper 1.0.3 is in those records; Work Items 0.4.4 is in the pinned Runtime release lock.

## Exact installed baseline and compatibility

`docs/program/evidence/actions-next-327/installed-smoke-receipt.json` records the actual installed consumer set as Runtime `1.0.4`, Core `1.0.3`, HTTP Helper `1.0.3`, and Work Items `0.4.4`. The same receipt records the old Runtime wheel SHA-256 as `a8cb07c01aa6b20947ef4483526fa1d6aa1bcb99abcd5235f04743cff1457e29`; that is a different build artifact from the locally rebuilt a26 candidate wheel. The a26 installed-restore qualification explicitly retains the public Runtime wheel digest `ab0925dd...f5eba` but does not record Core's exact version; the older installed-smoke receipt resolves it as `1.0.3`.

The canonical Runtime release commit recorded in `restore-20261020.json` is `d222f94edca26953c1506ab258adc458ded17c56`. Its Action Server manifest declares Core `^1.0.2`, HTTP Helper `^1.0.3`, Work Items `^0.4.4`, and Python `>=3.12,<3.14`. Its historical lock records Core source `1.0.2` with `develop = true`, Helper 1.0.3, and Work Items 0.4.4; this is the release source dependency floor, not the exact later installed-smoke consumer tuple. The actual installed-smoke receipt pins Core 1.0.3, which is also the retained published Core wheel used here.

Official Runtime 1.0.4 PyPI metadata declares `actions-core>=1.0.2,<2.0.0`, `actions-http-helper>=1.0.3,<2.0.0`, and `actions-work-items>=0.4.4,<0.5.0`. Core does not declare a direct Work Items dependency; the Runtime's published constraints join these package versions. Therefore Core 1.0.3 / Helper 1.0.3 / Work Items 0.4.4 is a version-compatible and repository-recorded installed baseline. The declared Core floor remains 1.0.2.

The a26 legacy qualification remains limited: its recorded Runtime `1.0.4` / Work Items `0.4.4` consumer refused schema version 6 as newer than its supported version 5 and preserved bytes; it then restored and restarted from a pre-upgrade backup. This is safe-refusal/rollback evidence, not proof of full Runtime restore across newer schemas.

## Official metadata and download URLs

URLs below were copied from the returned official PyPI release JSON, not constructed from names or digests. PyPI release metadata identifies `joshyorko` as owner for each of these releases.

- Runtime metadata: https://pypi.org/pypi/actions-runtime/1.0.4/json
  - Official wheel URL: https://files.pythonhosted.org/packages/94/d3/4b019821c0333af2b21a0ce8765e5551166e77749c1452604ab6c5653d0e/actions_runtime-1.0.4-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl
  - Metadata filename, size, SHA-256, and `requires_python` matched: CPython 3.12 Linux x86_64 manylinux wheel; 14,444,908; `ab0925ddfbc804d4790b5bd839461310b851c3dedf5f4781e4b4c8472bcf5eba`; `<3.14,>=3.12`.
- Core metadata: https://pypi.org/pypi/actions-core/1.0.3/json
  - Official wheel URL: https://files.pythonhosted.org/packages/25/b9/86adaaf08f60deb47c749f8dc2b59a0c672b9278daf917304bffd613ba90/actions_core-1.0.3-py3-none-any.whl
  - Metadata filename, size, SHA-256, and `requires_python` matched: `py3-none-any`; 103,809; `8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265`; `<4.0,>=3.10`.
- HTTP Helper metadata: https://pypi.org/pypi/actions-http-helper/1.0.3/json
  - Official wheel URL: https://files.pythonhosted.org/packages/53/3b/cefc0608e6ec71697c60c68ede2efa306fd7d50b1736c4b6b094b3424dc6/actions_http_helper-1.0.3-py3-none-any.whl
  - Metadata filename, size, SHA-256, and `requires_python` matched: `py3-none-any`; 14,690; `46ed7ce0e0d3e2e05456d937b5b24bc9dfa0d7d4b98f8119b9fdf00d4fa7e9f9`; `<4.0,>=3.10`.
- Work Items metadata: https://pypi.org/pypi/actions-work-items/0.4.4/json
  - Official wheel URL: https://files.pythonhosted.org/packages/87/0b/8f417d65e6e1fd85c158847f8858a1015c31042b24905cfb147d0a5d68b0/actions_work_items-0.4.4-py3-none-any.whl
  - Metadata filename, size, SHA-256, and `requires_python` matched: `py3-none-any`; 62,717; `488163817f3a2cb969744c1ad7332dc775318d0e755029639fd51d0bffe4ffc0`; `<4.0,>=3.10`.

Total staged bytes: 14,626,124. Workspace free space remained 18 GiB (32 GiB total; 13 GiB used) after download, above the requested 10 GiB floor.

## Limits

Only the four exact installed-smoke baseline wheels are staged. No transitive dependency closure was fetched; no package installation, import, execution, tests, GitHub artifact access, authentication, or credential changes occurred. In particular, no operation was made against the forbidden GitHub artifact `12653743795` or run `40331092012`.

## Canonical documentation improvement proposal

- Canonical guide: `docs/skills/repository-operations.md`.
- Proposed durable delta: when reconstructing an installed-release baseline, derive package constraints from the immutable release manifest and pinned lock, then use the retained installed-consumer receipt to distinguish actual companion versions from the declared floor. Cross-check published Runtime `Requires-Dist`, and verify each downloaded public wheel against official PyPI digests and any retained wheel hash before staging. Keep safe-refusal/rollback evidence separate from a full restore claim.
- Evidence: release commit `d222f94edca26953c1506ab258adc458ded17c56`; `installed-smoke-receipt.json`; a26 qualification/restore receipts; PyPI JSON/file digests; local staged-file hashes and byte counts above.
- Stale or ambiguous guidance removed: none; proposal only in this read-only lane.
- Remaining uncertainty: none for the four wheel identities. Full dependency closure, installation, execution, and the 1.0.4-to-newer-schema restore behavior were outside this task.

Upstream disposition: none. No upstream defect was found.
