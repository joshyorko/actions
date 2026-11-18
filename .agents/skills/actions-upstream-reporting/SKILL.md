---
name: actions-upstream-reporting
description: Use when investigating or reporting a possible upstream dependency defect found in joshyorko/actions.
---

# Actions upstream reporting

Use this workflow when work in `joshyorko/actions` finds a possible defect in
an upstream dependency or maintained external repository. It adapts the
evidence-first investigation and follow-through workflow used by
`joshyorko/josh-all-the-things`; Actions' own policy remains authoritative.

## Read the applicable rules

- In an Actions checkout, read root `AGENTS.md` and
  `docs/skills/upstream-reporting.md`. The guide is canonical for Actions'
  reporting policy and completion receipt.
- For the actual target repository, inspect its current `AGENTS.md`,
  `CONTRIBUTING.md`, issue templates, security policy, ownership, and branch
  rules. Do not carry Actions' or another project's labels, templates, or
  contribution rules into the target.
- This skill grants no permission. Creating an external issue requires current,
  explicit authorization for the named repository and issue-only reporting of
  a confirmed defect. Do not infer permission from credentials, role, an open
  issue, or authorization for another repository or operation. If publication
  is not authorized, prepare a sanitized draft. Do not ask again when the
  active task already grants the required scope.
- For a possible vulnerability, exposed credential, private data, or exploitable
  behavior, stop public reporting and follow the affected repository's private
  disclosure process.

## Choose the entry point

- For a supplied failure or finding, investigate that case directly; a focused
  investigation does not require a repository-wide scan.
- For an explicit discovery request without a supplied finding, inspect the
  target's current instructions, source revision, available discovery tooling,
  existing state, and requested scope before starting. Do not install tools,
  expand scope, or imply comprehensive coverage without authority and evidence.
  If discovery cannot run or is incomplete, say so; an unavailable scan is not a
  finding of no defects. A complete run may report no verified defects within
  its stated scope; do not generalize that result to the whole repository.
- For a continuation, preserve existing finding IDs, evidence, and submissions.
  Check the source revision, consumed dependency version, and report state, then
  resume missing work instead of restarting or duplicating reports.

## Investigate before reporting

1. Reproduce the smallest useful failure and record the exact Actions revision,
   dependency version or commit actually consumed, relevant configuration and
   environment, expected behavior, observed behavior, and sanitized output.
   Compare the Actions caller or adapter with a direct dependency invocation
   when that can distinguish local behavior from an upstream defect.
2. Trace the behavior to the current implementation, tests, and documented
   contract. Verify the actual owner and maintained repository or fork; do not
   infer ownership from an old import, repository name, or upstream lineage.
   Cite source with immutable commit links and line anchors.
3. Classify the result. An Actions caller defect belongs in Actions. An
   unverified attribution remains uncertain and is not an upstream bug report.
   A failure on an unsupported dependency version is a compatibility or
   support request. A missing capability without a broken documented contract
   is a feature request, not a defect.
4. Search the target's open and closed issues and pull requests, including its
   canonical owner and relevant maintained fork. Reuse a matching report;
   add information only when it contributes evidence, answers a maintainer, or
   corrects the record. Do not open duplicates.

## Prepare or publish the report

Follow the target repository's current issue template and contribution rules.
Keep the report focused on the upstream behavior: affected version or revision,
expected and actual results, a minimal reproduction, relevant environment,
sanitized evidence, immutable source links, attribution, downstream impact when
useful, and remaining uncertainty. Describe the evidence and impact; leave
implementation and prioritization to maintainers.

The Actions issue forms apply when reporting a defect in Actions itself: the
bug form asks what is wrong, relevant component and system versions, and an
example script when available; the feature form asks why and who needs the
capability, what is missing, and possible solutions or alternatives. For an
upstream dependency report, use that dependency's own current form instead.
Security reports use the target's security process.

If the task authorizes issue-only reporting and the new defect is confirmed,
publish one focused issue after deduplication. Do not treat that authority as
permission to edit source, create branches or pull requests, change triage
metadata, merge, or release. Those are separate operations requiring their own
scope. If an immediate downstream mitigation is separately authorized, keep
it narrow and tested, link it to the report, name its owner, and state when it
can be removed; otherwise prepare a proposal without changing source.

## Follow through

Follow up for material new evidence, maintainer questions, a correction, or a
release that changes the result. Avoid timer-based comments. If an upstream fix
is merged or released, verify that Actions consumes the corrected version and
passes its relevant qualification before describing the downstream issue as
resolved.

Complete the Actions-specific disposition receipt required by
`docs/skills/upstream-reporting.md`. Distinguish a draft, filed report,
maintainer decision, merged fix, released version, and consumed-and-verified
fix. Keep confidential evidence out of public reports and receipts.
