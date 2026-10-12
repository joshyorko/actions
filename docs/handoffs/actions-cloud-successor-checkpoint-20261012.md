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

| PR | Preserved successor head | Verified progress | Remaining gate |
|---|---|---|---|
| #307 | `23a6be5044f7a9377180f7ec7d33c50ad8c4c364` | All 23 checks passed; scoped independent source/security and packaged OAuth acceptance; normal merge into integration verified | Broader release installed/native/platform/dependency gates remain separate |
| #308 | `b0a014512da9024003dcd4e09056a951c42c48c4` | Minimal Windows source corrections; actual output-reader callback error observations; strict worker fixture retirement admission; independent source controls | Provider reader/deadline/census/lease controls, self-cgroup admission, genuine 18.19.3 Action baseline |
| #313 | `bd4f3f8397dd4563fe767484bf7de15ab99a0123` | All 19 checks passed on its original e2 target; mutex mutation controls reject early entry; ordinary local refresh preserves four non-documentation source blobs | Refreshed head CI and complete shared-deadline process/reader/lease acceptance |
| #306 | `b3defc66e7e127b071511f0ac1940847054dcaea` | Ordinary merge of e2 integration; database/savepoint source blobs preserved; independent merge-tree review; 16 SQLite tests pass | Fresh exact-head Windows/savepoint gates; historical first-readiness and descendant-cleanup failures remain separately unresolved |
| #305 | `f75dcae52fcd78c5c382d3903b012e5b049ca48b` | Exact public source and separate retained 640-second draft audited | Enforceable primary bound and actual browser/descendant/reader/lease cleanup |

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
owned loopback token exchanges, and has no broken requirements. This is neither
public PyPI publication nor complete native/startup acceptance.

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

Native attempts remain zero. The exact next gate is complete source-bound
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
occurred. Upstream disposition: none.
