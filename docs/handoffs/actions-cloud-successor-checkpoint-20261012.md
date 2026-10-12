# Actions Cloud successor checkpoint — 2026-10-12

This checkpoint continues the existing campaign under Josh's successor-workspace
authorization. The historical recovery entry remains immutable at
`0d5424ee8ec7c0a0ccea42a91eeecea144aa2934`; its detached evidence checkout is
`/workspace/actions-handoff`. No old worker or execution grant was resumed.

The fresh workspace independently verified all 18 canonical remote refs, the
complete untruncated 6,632-leaf payload tree, 2,862 source-copy manifest entries,
and eight historical setup-source supplement entries. These are preserved
source bytes, not recovered retired environments, raw logs, or private RCC
source. See the [machine checkpoint](evidence/successor-20261012/checkpoint.json)
and [receipt manifest](evidence/successor-20261012/manifest.json).

The supported repository launcher completed Doctor, Bootstrap and ToolkitTest
for the active engineering checkouts. The fresh toolchain reports RCC 18.19.3,
Python 3.12.15, Poetry 2.1.1, Invoke 2.2.0, Node 20.19.3 and Go 1.23.6;
ToolkitTest passed 179 tests. RCC owns the outer environment and Poetry owns
package environments. `/usr/bin/rcc` is a Qt compiler in this image; it is not
the repository toolchain.

## Source progress and acceptance limits

The original hosted snapshot is [timestamped 2026-10-12T03:32:11.889219Z](evidence/successor-20261012-supplement1/current-checks-0335.json). The [05:14 UTC snapshot](evidence/successor-20261012-supplement2/current-checks-supplement2.json) records306/313 terminal success and308 at0546 with22 successful checks, one macOS failure and Windows still running. The [second additive supplement](evidence/successor-20261012-supplement2/manifest.json) preserves later source, packaged-consumer, failure and workspace-access evidence. The original37 and first-supplement63 receipts remain byte-identical.

| PR | Preserved successor head | Verified progress | Remaining gate |
|---|---|---|---|
| #307 | `23a6be5044f7a9377180f7ec7d33c50ad8c4c364` | All 23 checks passed; scoped independent source/security and packaged OAuth acceptance; normal merge into integration verified | Broader release installed/native/platform/dependency gates remain separate |
| #308 | pushed `eeb806e7699d7f8e6878d5cc1dd83cd22e795ff5` | Diagnostic source329 tests pass; independent old-test RED/four-control GREEN and documentation-only successor review accepted; normal remote push verified. Historical0546 had22 successful checks, macOS failed and Windows running at05:14 | Fresh exact-eeb CI; actual macOS cause remains unknown; full controller/deadline/census/lease controls, self-cgroup admission, genuine18.19.3 Action baseline |
| #313 | `216ad55b5bcafaa54ba61fcc87982a57573adce7` | All 19 refreshed-head checks passed; 21 cleanup/mutex controls pass; independent exact target-diff review preserves four feature source/test blobs | Complete shared-deadline process/reader/lease acceptance |
| #306 | `eb0df4f97f390b413e364fe68364b81a65663f02` | Ordinary refresh onto accepted integration; six feature source/test blobs preserved; independent merge-tree review; 16 SQLite tests pass; all19 checks pass including Windows | Five original Windows failure nodes now pass; historical cause remains unknown; native/dependency/cleanup prerequisites remain open |
| #305 | `f75dcae52fcd78c5c382d3903b012e5b049ca48b` | Exact public source and separate retained 640-second draft audited | Enforceable primary bound and actual browser/descendant/reader/lease cleanup |

The #313 refresh composition review first expected too narrow a target delta and
failed. The corrected review included retained production/process-test changes;
that correction changed the review expectation, not source bytes.

CI observations in this checkpoint are timestamped snapshots, not transferable
acceptance. New source heads require their own checks; a passing
old head does not qualify a successor. All pushes are ordinary fast-forwards or
additive merge commits, independently read back from the remote.

The current #307 artifact set contains one sdist and six wheels. Its downloaded
archive matches GitHub's SHA-256; all seven files match their manifest. OAuth
runtime consumers match the tracked source. Windows embeds CRLF checkout
inputs with distinct correct provenance hashes; these are not relabelled as
exact LF Git blobs. A fresh Poetry-owned Linux consumer outside the checkout
imports the installed bundle, reports 1.0.3, passes nine OAuth controls including
owned loopback token exchanges, and has no broken requirements. A second fresh consumer resolves public Core
1.0.3 and HTTP Helper 1.0.3 through the default registry; downloaded wheel hashes
and all installed Python members are independently verified. Nine installed OAuth
controls and idle HTTP startup pass, including configured-key rejection (403)
and valid bearer access (200). The first harness attempt incorrectly expected
401 and remains FAIL. Post-start root/data/robots/tmp modes are 0700, one child
ACTIONS_HOME is 0750, and output logs are 0600. This is scoped idle startup with
zero workers and normal RCC feedback, not managed Action acquisition, a final
uncapped reader/descendant/lease census, public Runtime publication or complete
release installed/platform acceptance.

The #308 metadata increment initially failed independent decoder-poison review
at `89a599d9`. Its additive correction `fe1bdee3` has 323 focused tests passing,
one skip and three native tests deselected. Six controls fail on held89 and pass
on fe1; 36 metadata tests and 20 independent controls pass. The exact source was
independently accepted and normally pushed. It is opt-in observation transport,
not native controller wiring. Its new CI is separate from predecessor22. Missing
reader/sampler/enforcer facts and wait-event birth identity stay unavailable.

The fe1 source run was cancelled once after a bounded reproduction established
that fake waitpid backends omitted WNOHANG on Windows, entering a nonadvancing
legacy fallback. Its actual CANCELLED receipt and full-log diagnosis remain
preserved. The0546 correction changes tests and guidance only. Its macOS run
reports1420 passed,216 skipped and one failed provider-stopped assertion. The
original test discarded typed cleanup facts and had no emergency teardown;
the actual failure cause remains unknown. A controlled scheduler overshoot
demonstrates one possible route, without proving that route occurred on macOS.
Diagnostic b30 preserves strict live/complete assertions and the same0.2-second
budget, adds typed diagnostics and original-child teardown, and changes no
production helper. Independent review accepts that diagnostic scope. The additive
documentation-only successor eeb corrects the final zero-budget wait wording,
preserves all tested source bytes, and was normally pushed and remotely verified.
It requires fresh exact-head CI and remains distinct from failing0546.

The fe1 seven-file package set also passed independent complete Python-member,
manifest, RECORD and generated-input provenance checks. A fresh public Core1.0.2/
Helper1.0.3 consumer passes nine installed OAuth tests, dependency checks,
bundled-template creation and idle HTTP200/403/200. This qualifies that package
scope only; it does not qualify later complete source heads or native Action,
MCP, reader/descendant/lease, platform or release acceptance.

After the platform reported a05:10 UTC disconnection, a bounded read-only shell
check exited0 on the same host9e619bc297a7 and clean b30 checkout. The existing
workspace and workers were retained; no uncertain operation was replayed.

A separate fresh minimum-Core consumer uses public Core1.0.2/Helper1.0.3. All
203 Runtime,47 Core and2 Helper installed Python members match the measured
wheels; nine OAuth controls, dependency checks and idle HTTP200/403/200 pass.
Independent audit found no concrete Runtime-host floor incompatibility. Minimum
Core MCP discovery/read/tool execution and managed Action acceptance remain
untested. The authoring `meta=` limitation does not justify raising a host floor
when that host does not call the authoring decorators.

## Native admission and resource evidence

The visible cgroup has a 17,179,869,184-byte maximum, but self-binding is
unqualified: this process reports `0::/`, while the mounted cgroup root is
`/..`. Two bounded direct `cgroup.procs` reads returned zero bytes and no own
PID, with stable descriptor identity. Plausible counters do not prove ownership.
The [binding receipt](evidence/successor-20261012/pr308/self-cgroup-visible-direct-membership.json)
is an external admission blocker, not a reason to relax the existing check.

The resource snapshot records real disk/TMP/SHM and memory values. `/tmp` and
`/dev/shm` are RAM mounts; the toolkit uses disk-backed workspace TMPDIR. The
latest visible memory headroom is below the retained proposed native floor,
which itself has not been accepted or calibrated. A bounded read-only advice
attempt on completed parent scratch files failed; it is retained as a failure,
with no deletion, relocation, permission change, or global cache drop.

Managed native Action baseline attempts remain zero. Read-only RCC metadata and
toolkit commands, and ordinary idle-CLI RCC feedback, are separately observed. The exact next gate is complete source-bound
provider/worker/census/deadline/lease admission plus qualifying resources and a
verified self-cgroup identity, followed by one genuine RCC 18.19.3 Action
baseline. Only after PASS may released 18.19.5 and exact candidate
`727c1ff8b679cdbbe12836e53c87734a1edb0071` run separately, stopping at the first
failure. Newer binaries do not replace frozen RCC 7945 shipping-source
attribution. Private RCC 01f/frozen-v6 remains unrecovered.

## Release and retained graph

The initial snapshot recorded integration at `e2c81adce7858d5a952991ba9a8b7f72e902038a`.
#307 subsequently merged normally as `48eeaf171e695d9b8ac140ea53239eaeb6eff331`,
with ordered parents `[e2c81adc, 23a6be50]` and the accepted tree `137468f1`.
Independent remote readback confirms that integration ref. Community remains
`a70993fafc99a9f94041485542d5a720797ca394`; no other successor PR is integrated.
Runtime 1.0.3 remains HOLD on real source/security/CI, packaged OAuth, native
18.19.3/platforms, installed consumers, resource/dependency contents, release
metadata/checksums/signing labels, community distribution and publication
authority. RCC 18.19.6 publication HOLD is absolute and separate.

The #101/#82/#211 graph still retains 54 contracts, including accepted closed
#210 and 53 open at handoff. Release gates are separate from later lifecycle,
adapters, durable execution/recovery, providers, Robot/Work Items, MCP/Canvas,
control room and deployment/install slices. No issue was closed or duplicated.
The community tap still needs actual native assets, digest-bound Cask delivery,
and install/upgrade proof. No distinct operator-controlled publication approval
has been consumed; no release, tag, token publication or infrastructure action
occurred. Upstream disposition: none. Later source and receipt observations are preserved
in additive supplements; original FAIL and NOT_RUN receipts are unchanged.
