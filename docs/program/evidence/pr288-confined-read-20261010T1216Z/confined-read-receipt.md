# Confined selected-file measurement checkpoint

The final platform-typing follow-up is `d1cdc893b2e1a342e2728ec6376aba4882e33425`,
tree `3758146f4f3478f6a84d9d38b96483e5b37d1e6e`, preserving the reviewed reader
checkpoint 29c245d3 described below. It replaces direct Linux-only flag
references with strict typed attribute access and checks required flags before
acquisition. Missing, non-integer, boolean and non-positive flags fail; no zero
or weaker fallback exists. The Linux-only test fixture uses attribute access
too. Three invalid-flag tests and five durable canonical-guide lines accompany
the change. This follow-up makes no filesystem support or public API expansion.

At 29c245d3, prepared configured mypy with `--platform win32` failed with 12
`attr-defined` errors; `--platform darwin` failed with one O_PATH error. Raw
logs are `/workspace/work/source-profile-review/29-mypy-win32-red.log` and
`/workspace/work/source-profile-review/29-mypy-darwin-red.log`. At the final
follow-up, the same focused command with `--platform linux`, `win32` and
`darwin` passes on the two reader/test files. Logs are
`typing-fixed-linux.log`, `typing-fixed-win32.log` and
`typing-fixed-darwin.log` in that same scratch directory. The final source
suite passes 82 tests, comprising 47 reader and 35 policy tests, in
`typing-fixed-source-tests.log`; the 11 Robot checks pass in
`typing-fixed-robot-tests.log`. Ruff check/format, isort and diff-check pass.
Final worktree is clean, with 535 MiB available before the last narrow Robot
verification.

Safe c9 device baseline evidence is also preserved as immutable git-show source
`source_read_c9.py`, SHA-256
`86dd68f56a9766c91f1ffafee49556788a78816e92b5710fd79115d10b319fc8`.
The scratch runner `c9_device_guard.py` loads it and runs the two final device
guards. `c9-device-guard-red.log` records two expected failures because the
requested flags 657408 lack O_PATH 2097152. The guard asserts before invoking
a real read-capable device open, so the proof is safe. The same guards pass at
29c245d3 in `29-device-guard-green.log`, and its complete 79-test source suite
passes in `29-source-tests.log`. All these files live in
`/workspace/work/source-profile-review`.

Implemented private Linux selected-file measurement at local HEAD `29c245d3ff899e41f298915c7f44a1980c5ffaa4`, tree `1455af7d032573e1478ddd5e910bbb777e4cad01`, on `feat/source-confined-read-20261010` in `/tmp/work/actions-worktrees/source-confined-read-20261010`. Parent `c9cb938a7428bdf9b0cc3d0336003a0f9ea049c5` and its tree `cbb4a2b91e6fd92ed7948b0d42759741ee1ae923` remain preserved. The branch starts at accepted pure-inventory commit `e5f4405017d29647c19fa43e909678c56de9be13`; its original worktree and branch remain unchanged.

The entire diff from e5 is three files: a 287-line private reader, 522 lines of filesystem tests, and a 34-line canonical guide addition. No public endpoint/import wiring, compiler, staging, publication, provider, registry, GitHub mutation, Devsy call, reset, force operation, install, or asset download occurred. Final worktree is clean. Disk remained above the 500 MiB floor, with 556 MiB available at the final commit.

## Behavior and scope

`read_selected_files` accepts a caller-owned verified directory descriptor, explicit portable selected file names, and explicit protected names. It validates all names, collisions and protected membership using the accepted pure inventory policy before content reads. It owns a duplicate of the root descriptor and traversal handles, not the caller's descriptor.

Directory traversal uses `O_DIRECTORY | O_NOFOLLOW`. A selected leaf is first pinned with `O_PATH | O_NOFOLLOW | O_CLOEXEC`, then classified with `fstat`. Non-regular types, link counts other than one, and privileged permission bits fail before any readable leaf open. The utility pins a trusted Linux kernel `/proc/self/fd` directory once per call and reopens an owned numeric O_PATH descriptor relative to it with `O_RDONLY | O_NONBLOCK | O_CLOEXEC`. It compares the readable and pinned handles before reading. Missing required Linux features or procfd acquisition/reopening fail without a weaker ordinary-path fallback.

Reads check observed sizes and actual incremental byte counts against the same 50 MiB file and 500 MiB total policy. Metadata observations bind device, inode, type, permission mode, size, mtime_ns, ctime_ns and link count. Parent/name bindings and opened-object observations are checked before and after reads; selected paths are reopened for a final comparison. Per-path descriptors close before the next path is opened, so descriptor use is bounded by path depth rather than the full selected count.

The result separates measured root/directory/file facts from the existing policy-versioned canonical inventory. It proves bounded measurement of the explicit selected files in stable fixtures and rejects observed changes. It does not establish an atomic full-tree snapshot, selected-set completeness, original root pathname, Workspace authorization, compiler inspection, Package Revision, or Runtime Plan. Trusted kernel procfs is an explicit supported-environment assumption. Full filesystem snapshots and broader authorization remain separate gates. Actions #135 and #148 remain open.

## Evidence

Baseline e5 contains no filesystem measurement primitive. The first test run failed 31 tests because `source_read` did not exist; this was feature proof, not a claimed baseline bug. The first c9 implementation passed 36 tests, but independent review correctly identified read-capable device opening before classification as a blocker. Six added regression cases failed against c9 for the intended reasons. The follow-up uses O_PATH classification and procfd reopening; all 44 new tests now pass.

Final commands ran from `/tmp/work/actions-worktrees/source-confined-read-20261010`, except mypy from its `action_server` package directory. Tests used the existing prepared interpreter, not a newly installed environment:

```sh
env PYTHONDONTWRITEBYTECODE=1 TMPDIR=/workspace/work/source-profile-review/tmp PYTHONPATH=action_server/src:/tmp/work/deployment-values-deps/site-packages /tmp/work/multipackage-runtime-acceptance/venv-primary/bin/python -m pytest -q -p no:cacheprovider --basetemp=/workspace/work/source-profile-review/tmp/reader-proc-final --confcutdir=action_server/tests/contract_tests action_server/tests/contract_tests/test_source_read.py action_server/tests/contract_tests/test_source_manifest.py
```

Result: 79 passed in 0.37s, comprising 44 new reader tests and 35 accepted pure-policy tests. Tests cover portable/protected preflight, actual leaf/parent links with external bytes unread, hardlinks, FIFO, directory and privileged-file rejection, mutations of bytes/mode/link count, parent/leaf replacement during open/read, earlier-file mutation during later reads, root FD authority after original name replacement, canonical equality across roots, observed and actual byte limits, chunk/count limits, caller ownership and descriptor cleanup, missing Linux features and procfd support, wrong reopened object, and replacement between O_PATH pinning and procfd reopening. Device tests use a real O_PATH `/dev/null` descriptor; a specific open syscall seam models replacement-to-device without invoking a read-capable driver open.

```sh
env PYTHONDONTWRITEBYTECODE=1 TMPDIR=/workspace/work/source-profile-review/tmp PYTHONPATH=action_server/src:/tmp/work/deployment-values-deps/site-packages /tmp/work/multipackage-runtime-acceptance/venv-primary/bin/python -m pytest -q -p no:cacheprovider --confcutdir=action_server/tests/action_server_tests action_server/tests/action_server_tests/test_api_robots.py -k 'windows_destination_aliases or case_colliding'
```

Result at the final immutable HEAD: 11 passed, 40 deselected in 0.65s.

```sh
/workspace/work/community-resume/worker-exit/action_server/.venv/bin/ruff check action_server/src/actions/server/deployments/source_read.py action_server/tests/contract_tests/test_source_read.py
/workspace/work/community-resume/worker-exit/action_server/.venv/bin/ruff format --check action_server/src/actions/server/deployments/source_read.py action_server/tests/contract_tests/test_source_read.py
/workspace/work/community-resume/worker-exit/action_server/.venv/bin/isort --check-only --profile black action_server/src/actions/server/deployments/source_read.py action_server/tests/contract_tests/test_source_read.py
```

All passed; Ruff reported two files already formatted.

```sh
env PYTHONDONTWRITEBYTECODE=1 TMPDIR=/workspace/work/source-profile-review/tmp PYTHONPATH=src:/tmp/work/deployment-values-deps/site-packages /workspace/work/community-resume/worker-exit/action_server/.venv/bin/mypy --cache-dir=/workspace/work/source-profile-review/reader-mypy-cache --explicit-package-bases --follow-imports=silent src/actions/server/deployments/source_read.py tests/contract_tests/test_source_read.py
```

Result: Success, no issues found in 2 source files.

`git diff --check e5f4405017d29647c19fa43e909678c56de9be13 HEAD` passed. `git status --short` returned no entries at final HEAD.

Independent reviewer `/root/luna_source_profile` reported no remaining blocker at exact commit/tree 29c245d3/1455af7d. Their separate six adversarial cases passed: actual `/dev/null` opened only O_PATH then rejected; regular-to-FIFO substitution rejected without read/block; symlink substitution; hardlink added during read; declared oversize before read; borrowed root ownership. They also independently ran the official 79 source tests. The root agent owns the final integration decision.

Full package suites, RCC outer gates, non-Linux native behavior, complete source snapshots and compiler/provider acceptance were not exercised. Prepared-tool focused diagnostics do not replace release gates.

## Hash receipt

```text
7ea93ca36677493824456c844bc1fbcaa650c2744338ac4017aa81f445c0afc3  action_server/src/actions/server/deployments/source_read.py
d376563b7f11d0ca5ad35d5ff8977a1cfcae5cb187f13d7f9dd3d3125c09f38f  action_server/tests/contract_tests/test_source_read.py
2f3fa567781c001464d05ebaddebb28e6f03b083e355fea1fabd4886ab3adbe2  docs/skills/repository-operations.md
```

Documentation improvement:
- Canonical file changed: `docs/skills/repository-operations.md`, immediately following the pure source-inventory policy paragraph, in the implementation commits.
- Durable learning captured: actual selected-file measurement below a borrowed root FD; safe O_PATH classification before readable opening; required trusted procfs and fail-closed support; incremental limits, metadata/binding observations and owned-FD cleanup; explicit separation from atomic tree snapshots, original pathname and authorization.
- Evidence: final source, 44 new filesystem tests, unchanged 35 policy and 11 Robot tests, and the independent six-case review above.
- Stale or ambiguous guidance removed: the initial c9 paragraph's direct read-capable leaf opening description was replaced with O_PATH/procfd acquisition, preventing that unsafe intermediate sequence from becoming retained operational guidance. Existing Runtime/Robot defaults and race caveats were preserved.
- Remaining uncertainty: full snapshot coherence, root authorization, completeness, staging and compiler/provider/native integration gates remain open.

Upstream disposition: none. The device-opening correction belongs to this newly introduced Actions utility; no maintained dependency defect was found.
