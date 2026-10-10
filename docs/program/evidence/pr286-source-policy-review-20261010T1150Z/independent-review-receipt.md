# Independent supplied-source inventory review

Verdict: approve the bounded pure supplied-inventory policy prerequisite at commit `e5f4405017d29647c19fa43e909678c56de9be13`, tree `16c81059bff80b6d85606d45ac7d46a88cdce597`. No remaining blocking findings in this scope. Actions #135 and #148 remain open; this is no filesystem admission, compiler, source-artifact digest, Package Revision, or Runtime Plan acceptance.

Reviewed original commit `a6aa25412b8b40e5f93d6fee397fbd76283ba6b5`, tree `85680ddd86e3ff0ed7466703407ee1b5306474cd`, against base `2286d8e21f73a704b1fe8acd1127e09a160efd64`. The final working tree was clean before and after verification. The review lane made no source edits, GitHub mutations, resets, installs, or large asset downloads. Scratch artifacts are confined to `/workspace/work/source-profile-review`; disk remained above the 500 MiB floor, ending at 576 MiB available.

The original revision eagerly materialized every supplied entry before checking per-file or total bytes. Two sentinel generators proved that an oversized first file and a cumulative-byte violation both consumed their generator tail before rejection. A generator allocating 3,000 fresh 32 KiB contents caused 98,884,075 bytes of peak traced allocation before rejection with `MAX_FILE_BYTES=1`. The owner corrected this in the final commit by iterating bounded entries and applying validation immediately. Both sentinels now raise the intended `ValueError` without touching the tail, and the same allocation case peaks at 67,932 bytes. The fixed tests cover both regressions.

Initial Ruff check reported E721 on the exact-type guards; initial Ruff format check rejected `_portable_paths.py`. Final focused Ruff checks both pass. The final proposal records `sourcePolicyVersion: 1` and adds canonical documentation with the caller's acquisition responsibilities.

## Independent evidence

All commands below were run from `/tmp/work/actions-worktrees/source-policy-20261010` unless a package cwd is stated. Common test environment was `PYTHONDONTWRITEBYTECODE=1 TMPDIR=/workspace/work/source-profile-review/tmp PYTHONPATH=action_server/src:/tmp/work/deployment-values-deps/site-packages`, using `/tmp/work/multipackage-runtime-acceptance/venv-primary/bin/python`.

- `git rev-parse HEAD HEAD^{tree}` returned the final commit and tree above; `git status --short` returned no entries before and after verification.
- `git diff --check 2286d8e21f73a704b1fe8acd1127e09a160efd64 e5f4405017d29647c19fa43e909678c56de9be13` passed.
- `python -m pytest -q -p no:cacheprovider --confcutdir=action_server/tests/contract_tests action_server/tests/contract_tests/test_source_manifest.py`: 35 passed in 0.24s.
- `python -m pytest -q -p no:cacheprovider --confcutdir=action_server/tests/action_server_tests action_server/tests/action_server_tests/test_api_robots.py -k 'windows_destination_aliases or case_colliding'`: 11 passed, 40 deselected in 0.58s.
- `/workspace/work/community-resume/worker-exit/action_server/.venv/bin/ruff check action_server/src/actions/server/_portable_paths.py action_server/src/actions/server/_api_robots.py action_server/src/actions/server/deployments/source_manifest.py action_server/tests/contract_tests/test_source_manifest.py`: exit 0.
- Same Ruff binary, `format --check` on those four files: 4 files already formatted, exit 0.
- In the `action_server` package cwd, prepared venv `mypy --cache-dir=/workspace/work/source-profile-review/mypy-cache --explicit-package-bases --follow-imports=silent src/actions/server/_portable_paths.py src/actions/server/deployments/source_manifest.py tests/contract_tests/test_source_manifest.py`, with package `PYTHONPATH=src:/tmp/work/deployment-values-deps/site-packages`: Success, no issues found in 3 source files. An earlier attempt without `--explicit-package-bases` failed on duplicate module names and is not counted as a source failure.
- `python /workspace/work/source-profile-review/adversarial_review.py`: 34 independent adversarial checks passed, including file/directory conflicts in both orders, prefix collisions, duplicate names, invalid Unicode, traversal, reserved names, invalid modes, protected input mismatches, inclusion/order/content/exec-mode canonical behavior. 10,000 deterministic sampled nonempty components matched the original Robot predicate and NFC/case collision key. Exact maximum component 255 UTF-8 bytes, depth 64, path 4,096 bytes and 10,000 files were accepted; 10,001 files were rejected. The 10,000-file canonical proposal was 1,140,037 bytes and accepted, so no one-MiB canonical cap mismatch exists in this boundary.

## Hash receipt

SHA-256 values measured from the final executed working tree:

```text
e1d5ad71aa1a96b0c3356e61a31f8372023d5b155151b3e09998023ebe29c3b1  action_server/src/actions/server/_api_robots.py
b314bc34b5beed588c26b7236b0deab1d340e3580bd6c1dce0849502a2c44aad  action_server/src/actions/server/_portable_paths.py
4fb8d376d1b4aa06d301dedaeee67a2916561c7d10b8f1dadd657870b37b2b43  action_server/src/actions/server/deployments/source_manifest.py
bf2fda7f482db2f8a6bb9ea8bf520ecf55ef4a7a6ebec336356b6b20d23617f1  action_server/tests/contract_tests/test_source_manifest.py
690aabcbbf53e73270486fd117a11944dd905d1834803090876e2c82c83f969e  docs/skills/repository-operations.md
d816c1fe2303a66270067eda2f52d935702db194a21529c1428118a54afb920d  /workspace/work/source-profile-review/adversarial_review.py
75034a468e4642c93329297ad7daeea26b4cd7a4fc654a3ab3e05c3affda01f8  private git-show source_manifest_a6aa254.py
```

Full package suites, RCC-based acquisition/execution, hostile filesystem confinement/coherent snapshots, native platform behavior, and compiler/provider publication were not exercised. The sparse checkout lacks the RCC binary/source collection needed for the outer gate. Prepared-tool focused diagnostics do not replace package release gates. The pure boundary assumes ordinary caller-supplied Python values; it is not an untrusted Python-object execution sandbox.

Upstream disposition: none. The corrected resource-bounds defect belongs to Actions; no maintained dependency defect was found.

Documentation improvement:
- Canonical file changed or proposed: accepted the owner's exact addition in `docs/skills/repository-operations.md` at the final commit, immediately after the executable-source checkpoint guidance.
- Durable learning captured: supplied-inventory validation consumes entries incrementally, records sourcePolicyVersion 1, and validates declared bytes/kinds/names without measuring physical files. It documents the supported count/byte/path limits and the caller's selected-set completeness, no-follow confinement, actual object classification, source/staging coherence and staged-inventory duties.
- Evidence: source implementation and 35 focused tests at the final commit; independent lazy-generator, boundary and canonical checks described above.
- Stale or ambiguous guidance removed: no previous contradictory paragraph removed; the addition closes the missing distinction between a pure canonical inventory proposal and measured acquisition/snapshot/compiler evidence. Existing Runtime/Robot path-race caveats remain valid.
- Remaining uncertainty: full source acquisition/profile integration and compiler/native/provider gates remain unverified and outside this prerequisite. No issue closure is recommended.
