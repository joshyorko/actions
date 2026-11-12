# Windows fixture portability final review

Reviewed `/workspace/actions` at HEAD `a90d6cdb8af8b07bf534953903f157d003a4d322`, read-only, for the requested scope: `.gitattributes`, `test_datadir_restore.py`, `test_logical_preparation.py`, `test_generated_failure_cleanup.py`, `test_generated_result_serialization.py`, `test_robot_cleanup_race_327.py`, and `test_robot_runtime_profile.py`.

## Disposition

No findings in the requested delta. The fixture changes distinguish POSIX-only execution mechanics from portable security/decision behavior, and retain positive and negative assertions in portable tests.

- Datadir restore’s POSIX `O_NOFOLLOW` requirement is checked by the helper that creates the manifest-backed fixture, and by the SDK containment case. That skips only tests that need this fixture. The standalone explicit-offline/absent-target refusal test remains runnable everywhere. The restore suite retains tamper, path, metadata, copy-integrity, source-preservation, and cleanup rejection assertions on capable hosts.
- Logical preparation’s bound helper test is skipped only without POSIX `O_NOFOLLOW`. Unbound helper serialization continues on every OS. The `0600` mode check is made only on POSIX, where these mode bits express the asserted contract.
- Generated failure cleanup marks the real owned process-group/pipe scenario POSIX-only. Its extracted receipt/cleanup decision test remains cross-platform and still covers valid receipt acceptance plus missing, wrong artifact, wrong exit, invalid trust, and uncertain cleanup rejection. Thus fixture mechanics are skipped without removing validation of the gate.
- Robot cleanup race marks only owned-group signal mechanics POSIX-only. The nonowned-group refusal case remains portable by allowing `killpg`/`getpgid` to be absent on the host while asserting no signal occurs. Runtime profile retains its valid configuration and malformed/duplicate/oversized/relative-path rejection cases; its changes are formatting and use a platform-native absolute temporary path.
- `.gitattributes` adds `text eol=lf` for the pinned schema JSON. The current file and `HEAD` both hash to `bf30afb7ac251e3e22c037b7a685f60ef6603031b5484c0d08b1fa0bbe86d460`; `git check-attr` reports `text: set`, `eol: lf`, and `git ls-files --eol` reports `i/lf w/lf`.

The requested scope contains no production-source edit. `git diff --check` for the scoped files is clean. Per task context, Linux focused tests passed via RCC (27 process, 26 logical, 27 restore, and 1 pinned-wire case); I did not rerun them. Actual Windows CI remains pending, so Windows execution is not yet established.

## Canonical documentation proposal

Canonical file: `docs/skills/repository-operations.md`, in the existing paragraph beginning “For deliberately POSIX-only APIs, retain production refusal guards and test refusal separately from POSIX success mechanics.”

Proposed exact addition after that sentence:

> Put platform admission at the fixture or test that consumes the POSIX capability, rather than at module scope. Keep pure receipt, trust, cleanup-result, and refusal decisions portable by testing them with platform-neutral fakes; keep real process-group, signal, and descriptor mechanics in capability-gated tests. Assert POSIX permission bits only on POSIX, and do not treat them as Windows ACL evidence.

Evidence: the reviewed datadir, logical-helper, generated-failure, and Robot cleanup tests preserve their portable decision/refusal cases while gating only `O_NOFOLLOW` or owned process-group mechanics. The schema fixture also demonstrates keeping pinned raw bytes stable with a narrow `eol=lf` attribute; its HEAD and working-tree SHA-256 values match. This is a proposal only; the canonical guide was not edited in this read-only lane. No stale or contradictory guidance needs removal. Remaining uncertainty is actual Windows CI behavior.

Upstream disposition: none.
