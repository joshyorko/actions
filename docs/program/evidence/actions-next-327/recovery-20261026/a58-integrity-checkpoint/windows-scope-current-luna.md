# Windows Runtime 390 scope audit

Read-only scope audit of the Windows `build (windows-py3.12-devmode)` result
recorded in [the Runtime 390 diagnosis](windows-runtime390-207300bf.md). No
source, test or canonical guide was edited, and no suite was rerun. The 151
failures and 16 errors remain failures; this note does not claim a pass.

## Acceptance boundary

The current release acceptance matrix calls for combined current suites, old
aliases, and API/runtime behavior in #327/#328 ([`actions-next-release-327.md`
L486-L508](../actions/docs/program/actions-next-release-327.md#L486)). It names
the shared Runtime control plane as MCPv2, catalog/resources, HTTP/CLI and
process execution, while distinguishing the private provider as Linux-only
([same matrix, L727-L730](../actions/docs/program/actions-next-release-327.md#L727)).
The #328 foundry handoff also states that every accepted lane belongs to the
same release and no requirement is silently parked ([`actions-next-foundry-71.md`
L6-L15](../actions/docs/program/actions-next-foundry-71.md#L6)). Thus the
Windows matrix cell remains acceptance evidence for public/common behavior;
it does not convert explicitly Linux-only private filesystem or provider
implementations into cross-platform APIs.

## Classification from call paths

| API or failure family | Scope conclusion | Evidence and minimum response |
|---|---|---|
| Package revision source compilation (`_write_source_snapshot`) | Public compiler path; Windows behavior is required by the combined package/runtime acceptance when its contract supports Windows. It writes normal staged files and applies the source mode at [`package_revision_compiler.py` L1054-L1071](../actions/action_server/src/actions/server/deployments/package_revision_compiler.py#L1054). | The missing `os.fchmod` causes real contract failures, not an explicitly POSIX-only guard. Preserve the intended mode semantics with an appropriate Windows implementation/conditional behavior; add a narrow platform contract before changing code. Do not skip the compiler module. |
| Provider catalog private filesystem writes | Linux-only private provider, explicitly called out by the acceptance matrix at L730. `_put` requires directory-descriptor/no-follow POSIX operations and uses `fchmod` at [`provider_catalog.py` L331-L360](../actions/action_server/src/actions/server/foundry/provider_catalog.py#L331). | Keep the production admission boundary. Test the documented unsupported-platform outcome on Windows; gate only Linux-provider behavioral tests at that capability boundary. Windows mypy still needs typed platform boundaries, not whole-job suppression. |
| RCC package extraction (`rcc_execution`) | This operation needs owner review before calling it public cross-platform. The extractor currently writes entries with portable-path checks and optional `O_NOFOLLOW`, then calls `fchmod` at [`rcc_execution.py` L1205-L1223](../actions/action_server/src/actions/server/foundry/rcc_execution.py#L1205); #327/#328 require Runtime execution generally but separately name the Linux private provider. | Do not skip the whole execution surface or weaken extraction protections. First trace every caller and the supported Windows RCC execution contract; then make mode handling capability-aware or document/guard a genuinely POSIX-only sub-operation. This is a remaining contract question, not authority to change scope. |
| Discovery file publication | Public discovery/runtime startup path appears cross-platform: it uses `mkstemp`/replace and already treats `fchmod` as optional, with directory fsync separately omitted on Windows at [`discovery.py` L514-L532](../actions/action_server/src/actions/server/foundry/discovery.py#L514). | This caller itself is already tolerant of absent `fchmod`; inspect the exact 99-failure stack sites before attributing failures here. Preserve current atomic replace and portable behavior. |
| Offline datadir restore | Explicit POSIX-only operator flow. `capture_offline_manifest` rejects absent `O_NOFOLLOW` with “explicit offline POSIX backup required” at [`_datadir_restore.py` L106-L116](../actions/action_server/src/actions/server/_datadir_restore.py#L106). | Keep the production guard. Gate the POSIX mechanics tests narrowly and add/retain a Windows test for the current refusal. Do not skip adjacent restore contracts that can run portably. |
| Offline local authorization | Explicit POSIX private-ownership API; it rejects Windows at [`_local_authorization.py` L588-L599](../actions/action_server/src/actions/server/_local_authorization.py#L588). | Keep the guard and assert its unsupported-platform error on Windows. Gate only tests that exercise the POSIX success semantics; avoid module-wide skipping if it would hide that refusal test. |
| Owned TLS PostgreSQL fixture | Tests require a pinned Linux image: [`test_sealed_postgres.py` L28-L45, L100-L125](../actions/action_server/tests/action_server_tests/test_sealed_postgres.py#L28). CLI presence is insufficient; the observed daemon is a Windows engine and reports no matching Linux manifest. | Before image launch, check Docker server OSType/capability. Skip only when an ordinary run lacks a Linux engine; under strict required-provider mode, fail. Keep database behavior tests enabled when a Linux-capable engine is available. |
| Generated execution cleanup | POSIX owned process-group cases are explicitly labeled POSIX; one case has a Windows skip at [`test_generated_failure_cleanup.py` L166-L172](../actions/action_server/tests/contract_tests/test_generated_failure_cleanup.py#L166), while the failing receipt-cleanup case at L74-L112 invokes the same POSIX-oriented lifecycle. | Review runtime support and gate only cases whose assertion depends on POSIX process-group/pipe behavior, with a separate Windows-supported lifecycle test if that behavior is promised. The existing partial skip is evidence of inconsistent fixture admission, not grounds to disable module coverage. |

The mypy errors for `O_DIRECTORY`, `O_NOFOLLOW`, `getuid`, `getpgid`,
`killpg`, and similar members do not independently establish a runtime Windows
defect. POSIX-only modules should use checked platform boundaries and typed
helpers/stubs, consistent with the canonical guide's Linux-only reader rules
([`repository-operations.md` L3504-L3525](../actions/docs/skills/repository-operations.md#L3504)).
Cross-platform modules should retain Windows typing without suppressing the job.

## Smallest useful follow-up proofs

1. Split the 99 `fchmod` failures by exact top stack frame and caller contract;
   prioritize package compiler cross-platform mode preservation, and classify
   provider catalog as Linux-only. Resolve RCC extraction scope from its callers
   before assigning a fix.
2. Add a Windows refusal assertion for each explicitly POSIX-only operator API,
   while skipping only its POSIX-success fixture path.
3. Admit the owned PostgreSQL fixture using the daemon's Linux-container
   capability, preserving strict-provider failure and all database assertions
   on capable engines.
4. For cleanup, tie each case to its required process primitive and retain all
   platform-neutral receipt/ownership checks.
5. Rerun the same hosted Windows static/type and focused runtime proof only after
   the scope fixes; preserve the original aggregate as a failed receipt and
   never convert historical Linux/macOS results into Windows acceptance.

## Canonical documentation proposal

Propose a durable clarification in
[`docs/skills/repository-operations.md`](../actions/docs/skills/repository-operations.md),
near L2188-L2199, replacing the generic “Shared Linux-only fixtures check
their own platform” guidance with:

> For a platform matrix job, classify each failing call path against the named
> product contract before skipping it. Keep public Runtime/compiler/CLI/API
> paths enabled on every platform promised by the release matrix. For a
> deliberately POSIX-only operator API, retain its production refusal guard,
> gate only the POSIX-success fixture path, and assert the refusal on Windows.
> Shared fixtures must inspect the actual capability they need (including
> Docker server OSType for Linux images), because Docker CLI presence and a
> module-level pytest mark do not establish that capability. In strict
> required-provider mode, missing capability is a failure. Do not treat a
> Windows typecheck error as proof that a POSIX-only runtime path is supported;
> express the platform boundary explicitly while keeping the matrix typecheck.

Evidence: current acceptance matrix L486-L508 and L727-L730; datadir restore
guard L106-L116; local authorization guard L588-L599; provider catalog POSIX
operations L331-L360; Docker fixture launches a Linux digest L100-L125; and
the diagnosis records the Windows-engine manifest error and missing-POSIX
mypy findings. This wording removes the ambiguity between “combined current
suites” on Windows and intentionally Linux-only APIs without treating all
reported failures alike. No canonical documentation changed in this read-only
lane.

Upstream disposition: none. The evidence points to Actions call paths and
fixture capability admission; no maintained upstream defect is established.

Documentation improvement:
- Canonical file changed or proposed: proposed exact delta for `docs/skills/repository-operations.md` near L2188-L2199.
- Durable learning captured: distinguish public matrix-promised call paths from deliberately POSIX-only APIs; inspect actual Docker server OSType; keep strict provider mode failing.
- Evidence: cited current #327/#328 acceptance rows, source guards/call sites, existing cleanup skip and Windows runtime report.
- Stale or ambiguous guidance removed: none edited; proposal clarifies the ambiguity between generic combined suite acceptance and Linux-only implementation guards.
- Remaining uncertainty: the promised Windows contract for `foundry.rcc_execution` extraction needs owner/caller review; the 99 failures need exact stack-site partitioning before fixing.

## Caller and helper review addendum

The source trace resolves the RCC extraction question at the product boundary.
`GeneratedRccExecution.execute` extracts a compiled immutable source archive
before checking the prepared manifest and RCC artifact identity
([`rcc_execution.py` L398-L412](../actions/action_server/src/actions/server/foundry/rcc_execution.py#L398)).
However, its contract tests explicitly classify the private filesystem Package
storage path as Linux-only with a module-level Linux mark
([`test_foundry_rcc_execution.py` L221-L228](../actions/action_server/tests/contract_tests/test_foundry_rcc_execution.py#L221)).
Robot supervision separately rejects any non-Linux x86_64 host before
execution ([`robot_execution.py` L347-L388](../actions/action_server/src/actions/server/foundry/robot_execution.py#L347)); Robot validation also consumes the same extractor at
[`robot_validation.py` L231-L243](../actions/action_server/src/actions/server/foundry/robot_validation.py#L231).
Therefore `_extract_snapshot` is not evidence of a Windows-supported
cross-platform execution API. The Windows pytest failure stack should be
checked for this module mark: its Linux-only tests ought to be skipped, while
Windows mypy still needs a typed POSIX boundary. Do not add a Windows `fchmod`
fallback or claim that the method provides Windows file-mode/security
semantics. If `GeneratedRccExecution` can be constructed and reached on a
Windows service despite its Linux-only private provider dependency, add an
explicit fail-closed capability guard at the existing provider/execution
admission boundary, then test that refusal; do not guess a new broad API
contract.

The package revision compiler path is materially different. `compile_*`
validates selected source and then materializes a temporary package directory
for the build executor at [`package_revision_compiler.py` L785-L839](../actions/action_server/src/actions/server/deployments/package_revision_compiler.py#L785).
The public compiler/manifest contract retains each source entry's mode and
uses that mode when creating the deterministic archive
([same file L1054-L1071 and L1167-L1177](../actions/action_server/src/actions/server/deployments/package_revision_compiler.py#L1054)).
The compiler contract tests are not globally Linux-marked; only descriptor-
confined staging tests near L590 and L621 are explicitly Linux-only. This
supports Windows execution of the ordinary compilation contract, while not
proving that Windows mode-bit behavior is already correct.

The smallest safe Windows change is to make workspace materialization's
permission application platform-aware: keep `os.fchmod(fd, item.mode)` on
POSIX; on Windows use path-based `os.chmod(target, item.mode)` only if its
read-only mapping is the intended supported behavior, or omit the permission
call when the compiler contract promises archive/source identity rather than
POSIX workspace modes. In either case retain exclusive creation, containment,
bounded inputs and the mode in `SourceByteSnapshot`/the archive; never fake
Windows execute bits or claim private ACLs from POSIX mode values. The real
RCC-on-Windows build support is not established by the current CI matrix
alone, so the minimum regression should use the existing fake executor and
assert successful exact source bytes plus unchanged source/archive mode
identity on a Windows host. A separate platform-neutral test should assert
POSIX `fchmod` remains in use when available. Before claiming end-to-end
Windows compile support, require an exact pinned RCC Windows compiler receipt;
this host's output is only a Windows Runtime aggregate failure and does not
show that the native Windows runner itself was unavailable.

No generic secure Windows `fchmod` replacement exists in the reviewed
Actions source. `_community_expose_lifecycle.py` has typed `_posix_fchmod` and
`_posix_getuid` helpers, but uses them behind POSIX checks
([L27-L35 and L67-L70](../actions/action_server/src/actions/server/_community_expose_lifecycle.py#L27)); this is a typing pattern for explicitly POSIX operations, not a Windows permission implementation. `discovery.py` already conditionally applies `fchmod` and separately omits directory fsync on Windows ([L514-L532](../actions/action_server/src/actions/server/foundry/discovery.py#L514)); that is a useful precedent for best-effort POSIX metadata in an atomic cross-platform publication flow, but it does not establish private ACLs. The lifecycle module also has Windows reparse-point checks ([`_community_expose_lifecycle.py` L74-L80](../actions/action_server/src/actions/server/_community_expose_lifecycle.py#L74)); those are path-alias protections, not substitutes for permission preservation.

Scope distinction: the hosted job is a real Windows 2022 matrix leg
([`actions_runtime_tests.yml` L48-L65](../actions/.github/workflows/actions_runtime_tests.yml#L48)); therefore its recorded failures are not explained by a missing Windows test host. The Docker error is narrower: the Windows daemon cannot run the pinned Linux Postgres image, so it demonstrates absent Linux-container capability in that fixture environment, not a database product defect. Preserve that distinction in reporting.

Updated documentation improvement receipt:
- Canonical file changed or proposed: same proposed `docs/skills/repository-operations.md` delta above; sharpen its compiler/execution distinction with caller evidence.
- Durable learning captured: `_write_source_snapshot` is on the ordinary compile materialization path; `_extract_snapshot` is consumed by Linux-only private-provider execution and Linux x86_64 Robot supervision.
- Evidence: `compile_generated_python_action` materializes the temporary package at compiler L785-L839; RCC extraction is reached at `rcc_execution.py` L398-L412; Linux-only module mark at `test_foundry_rcc_execution.py` L221-L228; Robot platform guard at `robot_execution.py` L347-L388; Windows workflow matrix at `actions_runtime_tests.yml` L48-L65.
- Stale or ambiguous guidance removed: none edited; initial statement that RCC extraction scope needed owner review is resolved by call-path evidence, with only an explicit guard check remaining if a Windows caller can bypass the Linux-only provider.
- Remaining uncertainty: an exact Windows RCC compilation receipt is absent; source and fake-executor tests do not establish RCC host support. Confirm `GeneratedRccExecution` cannot be reached through a Windows provider before deciding whether a constructor/admission guard is needed.

## Compiler portability patch proposal

Text-only implementation proposal: [compiler-windows-proposal.patch](compiler-windows-proposal.patch).
It touches only the package compiler source materializer and its contract test.
It is not applied to the repository and was not executed.

The exact mode contract is defined by `source_manifest.validate_proposed_inventory`:
source permission modes are POSIX-valued identity data and normalize to only
`0644` or `0755` (`source_manifest.py` L153-L175). `SourceByteSnapshot` retains
that normalized mode alongside bytes (`package_revision_compiler.py` L100-L116,
L698-L713). `_deterministic_source_archive` stores the mode in ZIP external
attributes (`package_revision_compiler.py` L1167-L1178), and
`verify_compiled_package_revision` reconstructs and checks the source inventory
and deterministic archive (`package_revision_compiler.py` L412-L445). This
proves that source mode participates in the portable package identity. It does
not prove that the temporary directory used during build must mirror POSIX
execute bits on Windows; that directory supplies the exact source bytes to the
executor at L827-L839.

The proposal therefore makes Windows temporary materialization an explicit
bytes-only behavior and leaves the canonical snapshot/archive mode unchanged.
It intentionally does not call `os.chmod` on Windows: Windows chmod's
read-only mapping is not the POSIX 0644/0755 contract and would create an
unsupported permission claim. POSIX still resolves `fchmod` with checked
`getattr` and callable admission before creating entries; missing or
non-callable support raises a deliberate `RuntimeError`, while an operational
`fchmod` failure propagates through `finally` after closing the owned fd. No
`AttributeError` fallback is introduced. Existing path containment, optional
POSIX `O_NOFOLLOW`, and `O_EXCL` remain untouched.

Proposed regression coverage is limited and meaningful: a native-Windows-capable
ordinary compiler contract test captures exact workspace file bytes and checks
the archive's exact `0755` mode/content; POSIX tests prove missing and
non-callable `fchmod` fail before file creation, and prove a real fchmod error
propagates with its descriptor closed. Existing containment/exclusive-create
tests remain in force. This does not establish native RCC-on-Windows support;
an exact pinned RCC Windows receipt remains a later verification gate. No
genuine owner feature/scope decision is needed on this source evidence.

Updated documentation improvement receipt:
- Canonical file changed or proposed: proposed `docs/skills/repository-operations.md` clarification above; add that SourceByteSnapshot POSIX mode is canonical package identity while Windows workspace permission semantics are not inferred from it.
- Durable learning captured: mode identity is normalized to `0644` or `0755` and retained in deterministic archive; temporary build workspace contract is exact bytes plus POSIX mode operation where available.
- Evidence: `source_manifest.py` L153-L175; `package_revision_compiler.py` L100-L116, L698-L713, L827-L839, L1054-L1071 and L1167-L1178; existing archive verifier L412-L445.
- Stale or ambiguous guidance removed: none edited; proposed text distinguishes source identity from host filesystem permission semantics.
- Remaining uncertainty: the Windows RCC build executor behavior still requires an exact native receipt; the patch proposal is not applied or tested.
