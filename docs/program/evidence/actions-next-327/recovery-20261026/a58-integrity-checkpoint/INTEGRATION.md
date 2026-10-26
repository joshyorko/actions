# Integration result and remaining gates

The output-integrity repair is commit
`943f2736b5616b9034f4a97dac9a11efafdcd065`, tree
`cf10a054ffef511f258a5a2ede27857fd1a92d72`, Runtime **1.1.0a58**.
The delivered a57 CONNECT+RENDER bundle and pinned Dakota a44 are unchanged.
The surrounding test/evidence checkpoint does not qualify a new installed
candidate by implication.

## Repair and proof

Coverage512 failed because a post-open same-size rewrite escaped a reader that
checked only descriptor metadata after its initial whole-file digest. The job
did not measure timestamps, so no particular filesystem clock cause is claimed.
The deterministic regression masks only timestamp observations and performs
actual equal-size writes to the same inode. Its valid pre-fix baseline was
3 failed / 1 passed; earlier setup mistakes remain separate invalid attempts.

The repair records bounded block digests during initial verification, freshly
reads and verifies each complete touched block, and returns only the requested
slice. It retains descriptor/name/mode/link/size guards. A failed spanning read
does not consume an unreturned prefix; that regression first failed against the
initial repair, then passed after cursor advancement became transactional.
Missing/non-callable `pread` fails before owned descriptor allocation. Objects
remain bounded to64 MiB and blocks to64 KiB. This remains a trusted service-owned
Linux provider, not a concurrent hostile-tree snapshot or Windows implementation.

- Original and added filesystem cases: **24 passed**, no skips.
- Complete affected `tests/action_server_tests/run_outputs` suite:
  **89 passed**, no skips,23.54 seconds.
- Linux configured typecheck: **661 source files**, no issues.
- Independent explicit Luna final review: no remaining correctness blocker.
- Configured-key route proof:58 default and59 shutdown-enabled methods,
  missing/wrong bearer for each, **234 denials** before body/effects;2 cases pass.
  The affected existing auth slice passes88 tests.
- Safe candidate-browser failure-location diagnostic:19 tests pass. It prints
  only bounded numeric lines and fixed exception classes. It never admits a
  candidate or exposes raw assertion text. The previously forbidden artifact
  was not retried and its hidden assertion remains unobserved.
- Toolkit publication test-host repair:10 focused tests pass. Git Bash selection
  is explicit on Windows and negative cases prove the wrapper actually started.
  A later prepared ToolkitTest run passed213 checks; actual Windows rerun remains
  pending. No WSL or host security setting was changed.
- Owned TLS PostgreSQL fixture capability regression:9 tests pass with ordinary
  and inherited strict-provider environments. The read-only Docker server OS
  check precedes TLS state/container creation; strict missing capability still
  fails and actual Linux setup failures propagate. This is fixture admission
  proof, not a fresh actual-TLS provider acceptance run.

Exact copied receipts, hashes and earlier lint diagnostics are in
`manifest.json`, `a58-current-checks.md` and `temporary-log-excerpts.md`.
Formatting/import failures were found during integration and are not product
test failures. The final quality receipt is recorded separately when complete.

## Acceptance still required

The complete28-row reconciliation is retained in
`campaign-gates-current-207300bf.json` and its Markdown companion. It identifies
the original gate, latest source/evidence, actual blocker and next minimal proof.
These newer deltas do not rewrite its earlier source identity:

| Original campaign area | Current remaining proof |
| --- | --- |
| Combined Runtime/control plane | One fresh exact-source aggregate after these repairs, with PostgreSQL and qualified full coverage. Coverage512 and frozena52 stay FAILED. |
| Public authoring, renderer, accessibility | Mandatory supported-client typed execution/Work Item/Run/Attempt/artifact/reconnect flow; authored Python/TS parity and required UI states. a57 owner ChatGPT CONNECT+RENDER is separately PENDING. |
| Workflow/Task, Robot, Knowledge/provider breadth | Consumed bounded typed-job/projection and lineage/cancel/reconnect at supported-client scope; remaining producer/output/provider and control-SQL parity. Existing a56 receipts remain bounded and source-specific. Failed legacy/default Node and Node Task-decoder profiles are disclosed, not newly invented mandatory gates. |
| Security/provider identity | Domain-level multiple principals, generated-worker/environment and provider/effect recovery breadth. Global-key234-denial proof does not establish those identities. |
| Recovery/version compatibility | Full coordinated SQL, objects, journals, source/runtime/RCC material and lineage restore with replay from a distinct restored root. Authentic1.0.4/a57 queue/attachment upgrade/refusal/rollback is a bounded PASS only. |
| Platform/distribution/operator | Fresh OS/native/image and final consumer inventory, registry/storage/local build/restore. Windows Runtime390 remains failed; fixture and Git Bash repairs need hosted proof. Lock-qualified64/65-distribution SBOM subgates do not close whole distribution; both29-edge strict failures remain unchanged. |
| Owner-controlled acceptance | Actual invoice ChatGPT E1, publisher/security disposition, celld inclusion/exclusion, and final release decision. No merge, publishing, deployment or new live credential/grant/security setting is authorized. |

No new owner decision is required for authentic public1.0.4 inputs or the
accepted dual-view SBOM interpretation: existing authorized sources resolved
those questions. No failed gate is relabeled PASS. Upstream disposition: none;
the repaired defect and fixture problems are Actions-owned.

## Documentation receipt integration

The filesystem diagnosis and both reviews are integrated into
`docs/skills/provenance-observability.md` as fresh touched-block verification and
transactional reader-position guarantees. Auth, Windows, aggregate reporting,
dependency-profile/SBOM and historical-input proposals are consolidated into
`docs/skills/repository-operations.md`. Duplicate per-run counts remain evidence
here instead of repeated canonical rules. The complete matrix audit is retained
and the current continuation points to this checkpoint without shrinking scope.
The Windows scope review's preliminary owner-question wording is superseded by
its caller-review addendum: continue engineering contract checks before claiming
an owner-only blocker. Actual Windows RCC compilation remains unproved.
