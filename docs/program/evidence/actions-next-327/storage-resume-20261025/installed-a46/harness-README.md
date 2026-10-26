# Bounded installed-harness supervisor

Root-owned launch artifact; no RCC/PG/server launch was performed by this lane. Four isolated Python dummy-process self-tests ran: successful exit, exit7, deadline expiry, and a grandchild detached into its own session. Each supervisor receipt had no cleanup errors or remaining descendants; the detached PID no longer existed. Tree-selection tests exclude unrelated sibling workloads and include adopted grandchildren. See selftest-receipt.json. Test-only overrides reduced deadline to0.5/10seconds and disk floor to0; production defaults remain1800seconds/10GiB/16MiB.

Example (all paths target-local; config environment name must match the selected harness):

    /target/toolkit/python /target/installed-harness-review/supervise.py \
      --candidate-python /target/a46/consumer/bin/python \
      --script /target/claimed-public/qualify.py \
      --config /target/candidate.json \
      --config-env ACTIONS_CLAIMED_ROBOT_CANDIDATE \
      --budget-root /target \
      --evidence-root /target/new-supervisor-evidence

Also supports ACTIONS_V2_CANDIDATE and ACTIONS_KNOWLEDGE_CANDIDATE. The Knowledge choice was added after the process tests; AST was rechecked and no process logic changed. Evidence root must not exist; budget root already exists and must cover the filesystem where the workload writes. Run the supervisor as its own dedicated process, never embed main() in a shared task process. It rejects preexisting child processes. Candidate Python executable path is preserved (absolute, not symlink-resolved) so virtual-environment identity survives.

The child gets a new session/process group. Linux subreaper state is saved/restored. Descendants are identified from /proc parentage rooted at this supervisor, including processes adopted after their parents exit. Unrelated root pytest/build siblings are outside that ancestry. Per-process start ticks plus pidfd handles protect signals from PID reuse; no global kill or parent process-tree targeting occurs. All owned descendants are signalled individually, including separate-session Runtime children; process-group-only cleanup would miss them. No command-line/environment inspection is used.

Main deadline1800seconds; monitored free-space floor10GiB; child combined stdout/stderr cap16MiB; outer log cap16MiB. Polling nominal0.25seconds plus /proc/read/I/O time, not a quota. Cleanup independently attempts TERM/wait10seconds, KILL/wait5seconds, direct wait5seconds, adopted reaping, selector/stream closure, final descendant observation, subreaper/signal restoration, final disk check and receipt/log writes. SIGTERM/SIGINT request bounded cleanup. Any failure, timeout, cleanup error or retained descendant gives nonzero exit. SIGKILL/kernel termination cannot guarantee cleanup.

Outer supervisor.jsonl contains static event labels and elapsed time only. Child output is consumed, byte-counted and discarded rather than copied into logs that might reveal credentials. The harness retains its own sanitized evidence. No argv, environment, config contents, token or exception message is serialized. receipt.json records supervisor PID, child exit code, deadline/termination outcome, sanitized cleanup phase/type errors, any live descendant PID/state and log path. Files reside under a new0700 evidence directory and log/receipt are0600.

Supervisor PASS means zero harness exit plus completed bounded cleanup, not a substituted product/GUI result. Read the harness's own terminal receipt separately. A receipt write failure remains nonzero even if no receipt is available. Capacity sampling and cleanup assertions are not guarantees against uninterruptible kernel I/O.

Documentation improvement proposed for docs/skills/repository-operations.md: “Installed qualification needs an outer deadline because individual CLI calls may block before harness cleanup. Run the supervisor as a dedicated Linux subreaper, track descendants by ancestry and process birth identity, and reap children that started separate sessions; never target a shared executor's process tree. Preserve candidate virtual-environment executable paths. Keep supervisor exit/cleanup evidence separate from harness acceptance, and count/discard untrusted child output when outer logging cannot guarantee token redaction.”

Upstream disposition: none. Owned qualification tooling; no upstream defect or external mutation.
