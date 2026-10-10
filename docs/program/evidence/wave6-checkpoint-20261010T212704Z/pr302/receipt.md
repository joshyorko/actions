# PR302 portability refresh checkpoint

This receipt records a local branch refresh only. No remote branch was updated.

## Refs and merge

- Before refresh: PR302 head `e8e8a9db1c762b31fb4c4f625168dc7337235483`, tree
  `0392a8b0e5976bb489b53a198240b0d561ee3ad9`.
- Fetched `refs/pull/302/head` to `refs/remotes/origin/pr/302`; it still equals
  the starting head above.
- Fetched `refs/heads/integration/community-release-20261008` to
  `refs/remotes/origin/integration/community-release-20261008`; it equals the
  accepted PR304 merge `19380993febaa71238eaee3026b5c808773283ff`, tree
  `a8fe00af1858077273912d0b590f0f7a662c83d5`.
- Fetched `refs/pull/304/head` to `refs/remotes/origin/pr/304`; it is
  `73605934c1c948895410a5abaed6c225a396e038`, with the same accepted PR304
  tree `a8fe00af1858077273912d0b590f0f7a662c83d5`.
- Normal merge commit: `d649c90112ee03c46f8b88c973849d7203f7e64a`, tree
  `bbc33916748d02e24fe37ce843594a1d8f67067d`; ordered parents are the exact
  starting PR302 head followed by accepted merge `19380993...`.
- Merge was clean. The merged verifier pins `actions-core==1.0.2` and
  `actions-http-helper==1.0.3`. The Windows expected-path assertions remain
  `str(Path(...))`, and preserve the exact argv order and provider assertion.
  PR304's runtime-floor tests and guide changes are present.

## Verification

The supported RCC environment was activated with
`source /workspace/actions-cloud/activate.sh`; `ACTIONS_RUNTIME_TEST_PYTHON`
was unset. Tests ran through `rcc --no-build task script --robot
developer/toolkit.yaml` using prepared interpreter
`/workspace/work/actions-mk3-pr302/action_server/.venv/bin/python` (Python
3.12.15) and subject `PYTHONPATH=/workspace/work/actions-mk3-pr302-refresh/action_server/src`.
The prepared and subject manifests are byte-equal (`cmp -s` exit 0):

| File | SHA-256 |
|---|---|
| `action_server/pyproject.toml` | `be4011d3915e8838249546c70ae30420dadfb0d08c19b59970d8980332c7573f` |
| `action_server/poetry.lock` | `5d6acb65ba220211d1da020c78c51a5ea89465f2bbedc99aaf72319b862914e5` |
| `developer/setup.yaml` | `8674d6b55439fae5ac284fa92d7db8016e3589fafbf2d34e066e29345efa016a` |

Focused command:

```sh
source /workspace/actions-cloud/activate.sh
unset ACTIONS_RUNTIME_TEST_PYTHON
rcc --no-build task script --robot developer/toolkit.yaml -- env PYTHONPATH=/workspace/work/actions-mk3-pr302-refresh/action_server/src /workspace/work/actions-mk3-pr302/action_server/.venv/bin/python -m pytest -q /workspace/work/actions-mk3-pr302-refresh/action_server/tests/action_server_tests/test_rcc_runtime_adapter.py::test_publish_artifact_details_preserves_one_pinned_rcc_payload_and_provider /workspace/work/actions-mk3-pr302-refresh/devutils/tests/test_runtime_registry_floor_canary.py /workspace/work/actions-mk3-pr302-refresh/devutils/tests/test_runtime_release_workflows.py::test_published_runtime_floor_install_pins_exact_public_core_and_helper
```

Result: 24 passed in 2.03 seconds. This exercised the exact path string,
argument order, and provider assertion, plus the PR304 runtime floor canary and
exact dependency install contract. Full output is `focused-gates-green.log`,
SHA-256 `d27fb7cb5a9c169712b895b619797ee0f03994c306a2aad894912b935d71a743`.

The first attempt returned 24 setup errors because the isolated checkout lacked
the ignored pinned RCC file at Action Server's default path. No tests ran in
that attempt; full output is `focused-gates.log`, SHA-256
`57283f49b050b53a782eb5b61eb4e176168d470baa27e8815f9aa1065bf91a83`.
After confirming the prepared binary's SHA-256 was the pinned
`7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`, I copied
those bytes to the worktree's ignored default RCC path. This was no install or
download; the ignored file is excluded from the commit. The final worktree has
no tracked changes.

An import-origin check through the same RCC gateway confirmed Python 3.12.15,
the prepared interpreter path above, and the adapter module under this refreshed
worktree. Output is `source-origins.log`, SHA-256
`5a375e286a1b61e339259244d78774e05aaa3f718db1713c92d9fa8f2948105e`.

## Scope and disposition

PR302's own delta relative to its prior head is the existing `str(Path(...))`
test correction. The normal integration merge also carries PR304's accepted
floor pins/tests/docs and the other changes already present in that accepted
integration commit. `git diff --check` passed. No additional guide edit was
needed. No actual artifact publication/admission occurred; no upstream defect
was opened.
