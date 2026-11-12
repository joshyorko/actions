# Final review: package compiler workspace materialization

Reviewed the dirty `package_revision_compiler.py` and
`test_compiler_materialization_327.py` in `/workspace/actions`, using the
caller/platform classification in
[`windows-scope-current-luna.md`](windows-scope-current-luna.md). This was a
read-only review; I did not edit source, tests, or canonical documentation and
did not rerun any suites. The supplied logs record the focused change from
**3 failed, 2 passed** in `/tmp/327-compiler-platform-red.log` to
**45 passed, 1 skipped** in `/tmp/327-compiler-platform-green.log`.

## Findings

**No security or contract regression found in the reviewed change.**
`_write_source_snapshot()` now resolves a callable `fchmod` before it creates
any entries on non-Windows platforms. The actual mode-setting call remains on
the owned descriptor and failures propagate; the descriptor is closed in the
existing `finally` block (`package_revision_compiler.py:1054-1080`). On
Windows, it skips applying POSIX permission bits to the temporary workspace
files. It still writes each exact snapshot byte string, while source modes
remain canonical POSIX identity data in the snapshot and deterministic archive
(`source_manifest.py` mode contract; `package_revision_compiler.py:1176-1188`).
The code does not infer Windows ACLs from `0644`/`0755` or add a `chmod`
fallback.

The platform split is consistent with the reviewed caller classification:
this materializer is on the ordinary package compilation path, while the
separately reviewed Linux-only runtime/extraction paths do not establish a
Windows workspace-mode contract. The patch leaves exclusive creation,
conditional `O_NOFOLLOW`, path containment, snapshot bytes, archive identity,
and the executor call sequence unchanged (`package_revision_compiler.py:827-839,
1054-1080`). No path escape or reduced source/archive validation is introduced.

The new facade tests cover the critical boundaries: Windows-like mode with no
`fchmod` preserves source bytes and archive mode metadata; absent or
non-callable POSIX `fchmod` fails before entry creation; an operational
`fchmod` failure propagates and closes the opened descriptor; and native POSIX
workspace modes remain exact where that assertion is supported
(`test_compiler_materialization_327.py:24-98`). The tests avoid changing the
process-global `os.name`, which would interfere with `pathlib` behavior.

No code-level blocker remains. **Native Windows execution remains unverified**:
the Windows branch is exercised with an OS-capability facade on this host, not
by a Windows interpreter or a pinned Windows RCC compile receipt. Therefore
the evidence supports the documented workspace-byte/archive contract, but does
not establish successful end-to-end RCC builds on Windows. The supplied
focused run's single skip is the existing platform-specific case; no new
unsupported-platform suite skip was added.

## Canonical documentation proposal

No canonical guide was edited in this read-only lane. Add this paragraph to
[`repository-operations.md`](../actions/docs/skills/repository-operations.md)
immediately after the existing platform-specific API guidance under
“Windows type-checking of platform-specific APIs” (after the Dakota RCC
candidate paragraph):

> The package revision compiler keeps normalized POSIX `0644`/`0755` modes in the canonical source snapshot and deterministic archive on every host. Its temporary Windows build workspace guarantees exact source bytes; it does not claim that those POSIX mode values establish Windows ACLs. Keep descriptor `fchmod` on POSIX and fail before creating entries if that required callable is unavailable. Do not add a Windows `chmod` fallback. Windows capability-facade tests establish the branch behavior, while an exact native Windows RCC receipt is still required to claim end-to-end Windows compilation.

Evidence: `source_manifest.py` declares the normalized POSIX mode identity;
`package_revision_compiler.py:827-839,1054-1080,1176-1188` shows the ordinary
compiler materialization path, platform split, and deterministic archive;
`test_compiler_materialization_327.py:24-98` covers the platform and descriptor
boundaries; supplied red/green focused logs show the regression and result.
This would extend the existing guide's warning about POSIX mode bits versus
Windows ACLs to the distinct public compiler materializer and record its exact
cross-platform contract. No stale guidance was found that requires removal.

## Receipt

Upstream disposition: none. This is Actions-owned compiler behavior; no
upstream defect was found and no external target was authorized.

Documentation improvement:
- Canonical file changed or proposed: exact paragraph proposed for `actions/docs/skills/repository-operations.md` under “Windows type-checking of platform-specific APIs.”
- Durable learning captured: canonical source/archive modes remain POSIX identity values on every host; Windows materialization guarantees bytes without asserting ACL or workspace mode semantics; POSIX requires callable descriptor `fchmod` before creation.
- Evidence: source, regression, and supplied log references above.
- Stale or ambiguous guidance removed: none identified; proposal distinguishes this public compiler path from the existing Dakota RCC candidate guidance.
- Remaining uncertainty: the facade test and supplied focused suite do not prove native Windows RCC compilation; an exact Windows receipt is still required for that claim.
