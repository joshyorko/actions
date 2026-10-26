# a59 platform and browser-gate correction

This round starts from pushed checkpoint
`d878068ed3149e448830b0abfd5183412f185f21` and changes Runtime to1.1.0a59.
No a59 artifact or full-suite acceptance is claimed here. The separate a58
artifact below and delivered a57 owner-retest bundle remain unchanged.

## Measured corrections

Windows Runtime390 exposed unconditional `fchmod` in ordinary compiler workspace
materialization. Its canonical source snapshot/archive retain POSIX modes on all
hosts, while Windows workspace creation preserves exact bytes without claiming
POSIX execute bits or ACL privacy. POSIX requires callable descriptor `fchmod`
before creating files; permission failures propagate and the descriptor closes.
Exclusive creation, containment and source/archive identity checks remain.
The new platform-facade baseline was3 failed/2 passed. After repair, compiler
coverage passed45 cases with1 existing exact-manifest real-RCC skip; affected
capability/Knowledge callers passed49 cases. Independent Luna review found no
security/contract regression. Native Windows RCC compilation remains unproved.

The Windows-targeted mypy baseline then exposed34 errors across7 intentionally
POSIX/private-provider modules. Checked typed capability lookups preserve the
existing refusal boundaries, no-follow/nonblocking flags and mode checks. Missing
flags/functions fail closed; no zero fallback, type-ignore or Windows permission
substitute is added. Private archive extraction resolves its required chmod
before creating destination state; its2 new missing-capability regressions first
failed, then passed in the affected execution/provider slice. That slice passed
96 cases with33 explicit external-provider/RCC skips. Windows-targeted mypy passes
665 source files; this is static analysis on Linux, not a native Windows run.

POSIX operator fixtures now refuse unsupported hosts before creating state.
Portable acknowledgement/schema/help checks and actual API early-refusal checks
remain enabled. All existing Linux assertions remain active; no module-wide skip
was added. Native Windows execution is pending. The joined restore/authorization,
platform-refusal, CI-capability and Docker-engine regression suite passes75 tests
with no skips. New source guards and fixtures do not imply successful Windows
restore or private-provider support.

Fresh macOS391 exposed2 failures from the a58 fixture's changed missing-Docker
message (`Docker CLI required` expected, `Docker CLI is unavailable` returned).
Both failures were reproduced locally. The original diagnostic contract is
restored; ordinary/strict refusal and the new daemon OS check stay intact. The
75-case joined suite includes both unchanged original contract assertions.

New permitted Ubuntu753 logs expose the exact safe diagnostic
`AssertionError` at line688 of `test_canvas_query_template.py`, at merge
`6f95b68bb095a07b4634a8e225b422620b79b294` / tree
`b39a6ebd44261ef362d3ebb5f73408961f5059b6`. That assertion expected3 argv entries
and omitted the launcher's intentional `-P`. Both candidate and published-Core
checks now require the actual4-entry safe-path prefix. `-P`, source/module origin,
wheel API byte identity and strict browser/receipt admission remain mandatory.
Actual browser retest is still PENDING in this source checkpoint; the original
Ubuntu753 result stays FAILED. The inaccessible older artifact was not retried,
and its unobserved assertion is not identified by implication.

Configured Runtime Ruff checks, configured format, Isort and Linux mypy pass;
Markdown lint is unavailable. `origin-manifest.json` retains raw log hashes and
copied supervisor/report hashes. Initial failed style diagnostics and harness
attempts are not promoted to passing qualification. All final owned-command
supervisors report no surviving owned processes; the execution suite separately
records one adopted exit reaped by the supervisor.

## a58 recovery artifact retained separately

Clean a58 source943f2736/treecf10a054 produced Runtime wheel SHA256
`d4865a0a9d509d853897d7c97f23b4b371f10d6e5c27b0bce91cca406bb3629d`.
Its339 payload hashes, clean lock-constrained install and normal unmasked
same-inode post-open tamper rejection are retained under `a58-artifact/`.
The separate timestamp-masked diagnostic is labeled explicitly. HTML is identical
to delivered a57 (490733 bytes, SHA256
`753e9b50759cb628bf5a402575b33e2a411f4c3a775840146f6d507a05183b44`).

Library `libfile_017d897a1a9c81919fa400083b4f445b` v0 preserves
`actions-327-a58-integrity-qualification.zip`,15628188 bytes, SHA256
`fdd3f51154bec9993c68c48d8b3374fa79633e3d30c8b47b43448aa12df99dfc`.
It includes exact Runtime/Core/Work Items wheels, lock constraints, qualification
receipts and the prior campaign checkpoint. It is not an owner a57 replacement
or full service, cross-platform or release acceptance.

## Remaining original campaign gates

The complete28-row map in
`../a58-integrity-checkpoint/campaign-gates-current-207300bf.json` remains
controlling. Coverage513/run40352516551 at pushed d878 was running when this
source checkpoint was prepared; no duplicate aggregate was launched. It cannot
qualify these later a59 changes. Frozen a52 and coverage512 remain FAILED.
Current-source aggregate and native OS/browser proof, mandatory supported-client
typed execution/Task flow, provider/security/effect recovery breadth, coordinated
whole-Runtime restore, final distribution/operator acceptance, actual ChatGPT
invoice E1, publisher/security and celld decisions remain open. Actual a57 owner
CONNECT+RENDER remains separately pending. No release/merge/deployment or new
live credentials, grants, OS/network or security settings are authorized here.

Documentation proposals from all lanes are integrated in repository operations
and Work Items guidance. The typing proposal was narrowed: unused helpers/imports
were removed, bool flags reject explicitly, and extraction capability resolution
moved ahead of destination creation. Historical preliminary contract questions
were resolved with the prior caller audit rather than labeled owner-only blocks.
Upstream disposition: none; these defects and fixture contracts are Actions-owned.
