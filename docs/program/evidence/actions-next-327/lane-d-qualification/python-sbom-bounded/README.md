# Final bounded wrapper acceptance

This is the actual final wrapper run, superseding earlier execution-layout traces.
Exact input/environment command is in ../python-sbom-producer/README.md; change
only --output-dir to /workspace/lane-d/producer-bounded-qualified. Run from
prepared package-local devutils Poetry with its optional sbom group and task-owned
writable caches. Prior producer/consumer locks and wheel identity are unchanged.

The producer now emits validated JSON through --output-file -, drained directly
to task-owned python-consumer.cdx.json. Two draining threads retain at most 32 MiB
per stdout/stderr stream, with 64 KiB transient read chunks; overflow fails and
terminates the child. Thus the SBOM output file is bounded while being generated,
not merely checked afterward. Prefix probe output is capped at 64 KiB. No
unbounded capture_output remains. This limits captured output, not the producer's
internal memory or unrelated files written by trusted children.

Every invocation has a 120-second deadline (tests override it). On POSIX cleanup
kills the created process group and reaps the direct child; stream readers get
bounded joins. Cleanup failure raises explicitly. Windows cleanup only terminates
the direct child and reports lingering readers; no Windows process-tree or native
acceptance claim. Partial capped files remain after overflow/timeout. These are
resource controls, not a sandbox or defense against a hostile process escaping
its group. Consumer and producer must be trusted: interpreter startup/site/.pth
execution remains possible even with isolated Python flags.

The wrapper queries consumer sys.prefix through its interpreter, resolves it and
compares with resolved producer sys.prefix. Alternate path spelling cannot bypass
same-environment rejection; both actual prefixes are recorded. No executable
symlink resolution is used to conflate distinct venvs sharing a base Python.

Final actual run: exit 0 for approved dependency inventory/provenance scope,
DECLARED SBOM, all 29 differences explained, strict_active_graph=failed retained.
319 installed wheel members verified before/after. Raw SBOM byte-identical to
original strict-failed run. This remains original da928b69/a38 consumer evidence,
not combined candidate qualification or runtime reachability/signing/publication.

Tests: overflow retains exactly 1024 bytes in a bounded test, timeout preserves
partial stdout, and alternate executable spelling of the producer environment
is rejected by actual prefix. Full devutils stdout/XML retained alongside final
run receipt and outputs. Lint checks passed. Release hook remains integrator-owned.
Rollback this slice restores the prior wrapper; no dependency or database changes.

Canonical-guide delta proposed to integrator: “Use bounded streaming for producer
stdout/stderr and SBOM bytes, retain partial output on timeout/overflow, and record
cleanup limitations. Verify separate environments using interpreter-reported
resolved prefixes. Require a trusted consumer: these controls do not sandbox
Python startup or .pth execution.” Learning is verified by the final installed
run and three new negative tests. Uncertainty: no Windows/macOS native execution,
no hostile-child containment. Upstream disposition: local resource-control
improvement; no new upstream defect or external report.
