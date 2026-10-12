Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md
- Placement: after the memory-admission paragraph ending “missing ownership/scope check.”
- Exact addition:

A failed direct-membership probe applies to the directory it examined. A mounted
parent can have an empty `cgroup.procs` while a child contains the current PID.
For a bounded identified child, open its directory relative to a pinned parent
FD, sample `cgroup.procs` twice through one file FD, and retain the route, mount
metadata and FD identities. Report child membership and visible ancestor limits
as separate facts. This empirical witness does not waive canonical-path checks
or turn shared counter headroom into reserved launch capacity.

- Durable learning captured: direct-member discovery, visible ancestor limits and canonical namespace mapping are distinct evidence dimensions; a failed parent probe cannot be generalized to children.
- Evidence: ONE independent audit PID58303 present in both sameFD init/cgroup.procs reads dev24/inode215, matching separate root discovery for PID56979. Parentprocs still0 entries dev24/inode150; child memory.max=max, parent17179869184 withmemoryenabled andonevisible descendant. Directory/file identities and mount text stable. Route0::/ andmountroot/.. remainunresolved.
- Stale or ambiguous guidance removed: any inference from empty root/procs to absence of selfmembership in the visible hierarchy. Preserve the actual prior rootcandidateFAIL and existing canonical launchpolicy HOLD; no guard is relaxed.
- Remaining uncertainty: canonical namespace-path mapping, hidden ancestor constraints, applicability to future provider/Action trees, accepted overhead/resource budgets and whole-operation controller admission remainunqualified. Nativeattempts0.
Upstream disposition: none.
