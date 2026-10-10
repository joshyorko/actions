# Independent review: controlled v2 compiler archive-cap successor

Verdict: **APPROVE this bounded private fixture proposal with the stated limits.** Reviewed immutable commit `f22fbb66991219dbcc81a5e867da463d4df07dd1`, tree `f83238da39b9350307035f3ec93e28462dfe591f`, parent `0dbe80cb17f8d986838a338d106a9b3723927565`. The two paths remain the compiler module and its contract test. Current module content SHA-256 `34e49c181930944a1347137e5251f3bcb3bb7731e92e1b6ecdd61c765fb0afb4`; test content SHA-256 `b54ea80143e650ff316bb0bc6d73bc2ca0d6d4abe07af5ca4ac805bd3981f001`. Author worktree was clean at review; no source changes made.

## Original finding disposition

The prior REVISE finding on `0dbe80cb` was the lack of a total archive envelope ceiling: 67,100,032 bytes of real staged/measured source emitted a 67,110,848-byte ZIP, exceeding the 67,108,864-byte source payload limit. The successor adds a distinct `MAX_CONTROLLED_ARCHIVE_BYTES = 64 MiB`, preflights the fixed ZIP_STORED envelope before calling the archive builder, and checks emitted length against both the computed size and cap. The source payload and archive bounds are now explicitly separate.

The exact envelope calculation is correct for this fixed profile: 22-byte EOCD plus, per entry, payload bytes + 30-byte local header + 46-byte central-directory header + twice the UTF-8 filename byte count. No ZIP64, explicit directories, extras, member comments, or archive comment are enabled. Python's UTF-8 flag is in the fixed header and does not add a variable-length extra field. The successor includes exact emitted-size checks and tests that exercise a multibyte name and reject one byte over a monkeypatched exact cap before `_make_source_archive` is called.

I reran the real 102-file over-limit source probe from the previous finding against this successor. It used `stage_selected_files` and `read_selected_files` to create an actual measurement, supplied 67,100,032 payload bytes under the 67,108,864 source bound, replaced the archive builder with a sentinel, and observed the expected archive-bound `ValueError` without invoking the builder. Output: `archive_bound_probe: PASS early_rejection payload_bytes= 67100032 configured_source_bound= 67108864 archive_builder_called=False`. Log SHA-256 `01556b03a89cabe2c912d15f4763bdb0592b292545a3b947f66172d2d7132785`; probe script SHA-256 `59c2b1095a4332ced796eedabf91b8f2c81931103442fbbf9242726e2d0b4f7d`.

## Independent tests

Focused command, using the prepared worker-exit venv, explicit immutable source path/cached RFC 8785 package, disabled cache/log plugin, and unique RAM pytest scratch:

```sh
SCRATCH=$(mktemp -d /dev/shm/audit-compiler-successor-luna-XXXXXX)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/dev/shm/actions-controlled-v2-compilation-20261010/action_server/src:/tmp/work/deployment-values-deps/site-packages \
  /workspace/work/community-resume/worker-exit/action_server/.venv/bin/python -m pytest \
  -c /dev/null -p no:cacheprovider -p no:robocorp_log_pytest \
  --confcutdir=/dev/shm/actions-controlled-v2-compilation-20261010/action_server/tests/contract_tests \
  --basetemp="$SCRATCH" \
  /dev/shm/actions-controlled-v2-compilation-20261010/action_server/tests/contract_tests/test_package_compiler.py -q
```

Result: `15 passed in 0.20s`, no skips. Captured output: `successor-focused-tests.log`, SHA-256 `d6f4eedff8361efad1f773f2445ac79fbbcaf9fba29649ae0170101ebf72c3b8`.

The additional independent path/timestamp probe still produces identical source archive, capability manifest, runtime plan and revision preimage from two different source locations and timestamps. It is in `successor-probes.log` along with the real over-limit early-rejection result.

## Remaining scope

The private seam appropriately rejects file sets or bytes that disagree with the declaration/measurement and makes no filesystem acquisition or RCC call. The returned proposal keeps `inspection_status="not_run"`; supplied action metadata and RCC digests remain inputs, not verification. No general package completeness, whole-tree atomic snapshot, compiler trust, executable discovery, provider authenticity, admission, publication, native/RCC execution, or whole #135/#148 acceptance is established. No upstream dependency issue was found.

Canonical guide proposal is at `/workspace/work/controlled-v2-compilation-20261010/documentation-improvement-proposal.md`; it now states the separate 64 MiB archive budget and exact envelope accounting. Upstream disposition: none.
