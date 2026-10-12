Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md
- Exact replacement for the memory-admission paragraph beginning “Memory admission must bind...” and ending “missing ownership/scope check.”:

Bind memory observations to the current process's cgroup and identify the scope
of each counter. Namespace-relative `/proc` paths need not match a mounted
hierarchy's root; never rewrite `/..` to `/`. A current-PID witness through a
pinned child FD, with its verified parent relationship, can bind a shared
ancestor's `memory.max` and `memory.current` even when the child's maximum is
`max`. This is an applicable shared constraint, not reserved or fully available
memory. Keep unknown higher constraints and native budgets, enforcement and
cleanup admission separate from resource-source identification.

- Durable learning captured: descriptor-bound own membership and physical ancestor relation can identify a real shared resource source without reconstructing namespace-relative lexical paths. Finite parent limits continue to apply to a child with local maximum max.
- Evidence: retained ONE audit PID58303 in init/procs twice, pinned child inode213/procs215 and parentinode148 on dev24, finite parentmax17179869184 and enabledmemorycontroller. Primary LinuxKernel cgroupv2 docs sections Introduction, Processes, MemoryInterfaceFiles and Namespace. Immutable f949 gitgrep finds no cgroup resource validator in action_server/src or scripts.
- Stale or ambiguous guidance removed: treating unresolved namespace/mount-path text as an independent reason to reject an already FD-bound shared ancestor counter, or claiming a formal canonical-only launch policy absent from inspected Runtime source.
- Remaining uncertainty: actual namespace/mount creation history is unknown and unnecessary to this source inference. Higher constraints, future process migration/binding, accepted native budgets, guardian/controller/readers and lease qualification remain unproven; nativeattempts0.
- Primary source: https://docs.kernel.org/admin-guide/cgroup-v2.html
Upstream disposition: none.
