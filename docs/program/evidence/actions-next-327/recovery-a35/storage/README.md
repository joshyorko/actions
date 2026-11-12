# Storage preservation and test admission

The initial frozen a35 full portable run was interrupted after ENOSPC. Its
receipt remains FAIL (exit -2); no complete JUnit result exists and no pass
count is claimed. Full local stdout and fixtures remain retained.

Two completed archival passes converted only inactive task-owned raw .robolog
files to deterministic gzip. Each original was regular, single-link, not open,
and unchanged before replacement; decompressed SHA256 matched the original.
The manifests retain original/archive paths, sizes and both hashes. Original
bytes total 3,855,850,828; compressed bytes total 527,649,774. Human-readable
HTML, stdout, XML, source receipts, screenshots and datadirs were unchanged.
Archives remain local under /workspace/actions-recovery-327/evidence; restore
a raw trace with gzip -dc archive.robolog.gz > restored.robolog and verify
its original SHA256. These manifests are not remote copies of all raw traces.

The replacement full run uses the same tests and not-integration_test marker,
with pytest tracing disabled via -p no:robocorp_log_pytest and full stdout/XML
retained. It is still running at this checkpoint, not a completed pass. An
attached PID/create-time guarded watcher interrupts its exact pytest process
if free space falls below 768 MiB. It does not delete files or retry tests.

The new read-only disk preflight exits 2 below an explicit positive budget,
never overwrites a prior receipt, and is invoked with subprocess check=True
before Docker or pytest in the saved future driver. Its two regression tests
passed. The actual 3 GiB preflight returned BLOCKED with 2,788,208,640 bytes
available; no additional full run was launched. The running replacement had
started before this preflight was added, and is not claimed to have used it.

Upstream disposition: none. This is local test resource management.
