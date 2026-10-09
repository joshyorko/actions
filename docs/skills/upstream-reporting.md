# Upstream defect reporting

Use this workflow when implementation, review, debugging, release, or
coordination finds a possible defect in a dependency or maintained upstream
repository. Report a verified upstream defect through that repository's issue
process, then keep the downstream impact linked to its disposition. A paragraph
in local documentation is not a substitute for an assignable upstream report.

## Authority and ownership

This guide is a procedure, not a permission grant. Reading it, an agent role,
repository access, or an open issue does not authorize external mutations.
Creating an upstream issue requires explicit authorization for the target
repository and issue-only reporting of a confirmed new defect. That authority
does not cover source edits, branches, commits, pull requests, labels,
assignments, milestones, settings, merging, releases, or publication. Ask for
the specific authority before those actions. If the target is third-party or
otherwise outside the explicitly authorized scope, prepare a factual draft and
request issue-publication authority.

For the 2026-10-09 campaign, the user's task authorization covers issue-only
reporting of confirmed new defects in explicitly in-scope maintained
`joshyorko` repositories, including `joshyorko/rcc`, subject to actual account
permissions and each repository's rules. This campaign scope grants no other
mutation authority and is not a standing grant for later tasks; verify the
active task's authority each time.

Before classifying the defect, verify the source owner and repository, the
actual remote/fork, and the version or immutable revision Actions consumes.
Trace the observed behavior to current upstream source, tests, release notes,
and documentation. For RCC, Actions pins Josh Yorko's maintained fork; the RCC
repository identifies `admariner/rcc` as historical archaeology, not the
current release authority. Do not infer current ownership from an old import,
repository name, or upstream lineage.

Classify the finding before reporting:

- If the behavior is caused by Actions, fix or track it here.
- If evidence does not establish an upstream defect, record the uncertainty and
  continue local diagnosis; do not file a speculative issue.
- If an integration boundary or external service is involved, isolate the
  caller, provider, network, and published contract. A failed integration alone
  does not identify an upstream owner; report a defect only when evidence shows
  the upstream implementation violates a documented supported contract.
- If the failure is on an unsupported dependency version, classify it as
  unsupported-version compatibility or a support request, not a confirmed
  defect. If the version is supported and violates the compatibility promise,
  treat it as a defect candidate.
- If a capability is missing without a broken documented contract, classify it
  as a feature request or product decision, not a defect. Keep the request
  separate from bug reports and defer product priority to maintainers.
- For a confirmed, new defect in an authorized target, after deduplication
  promptly file one focused issue following that repository's contribution
  rules, then link it from the downstream blocker, test, or task. If an
  equivalent report already exists, update or link that report instead of
  opening a duplicate.
- If the finding concerns a vulnerability, credential exposure, private data,
  or exploitable behavior, stop public drafting and follow that repository's
  private security reporting process. Keep sensitive details out of public
  issues and this repository's general documentation.

## Evidence and report preparation

1. Capture a minimal reproducible case: exact upstream revision/package version,
   relevant configuration and platform, command or request, expected result,
   observed result, and the smallest useful output. Remove secrets, personal
   data, and unrelated logs.
2. Cite source with immutable commit permalinks and line anchors. Cite the
   release/docs version actually consumed. Separate directly observed facts
   from hypotheses, downstream effects, and unknowns.
3. Search the target repository's open and closed issues and pull requests,
   including its canonical owner and relevant fork. Reuse an existing report
   when the evidence is the same; add a new comment only when it contributes
   material evidence, answers a maintainer, or corrects the record.
4. Read the target repository's current contribution, issue-template, and
   security guidance. Follow its naming, base-branch, and report format rules.
   Do not carry labels, assignment rules, templates, or other governance from a
   different project.
5. State the reproducible behavior, affected version/revision, downstream
   impact, evidence links, and uncertainty. Attribute local design choices to
   Actions when they contribute to the behavior. Describe outcomes and options;
   let maintainers choose an implementation. Do not prescribe a patch as a
   condition of accepting the report.

Do not turn an upstream gap into a permanent local workaround. If an immediate
downstream mitigation is needed and the active task already authorizes that
local fix, keep it narrow and tested, link it to the upstream report, name its
owner, and state a concrete removal condition; the task's existing scope is
sufficient. If the mitigation is outside that scope, request authority before
changing source. Do not weaken security or silently retain a fallback after
the upstream defect is fixed or its behavior is resolved by maintainers.

## Follow-up and downstream handoff

Follow up when evidence changes, a maintainer asks a question, the report is
disproved, a release changes the affected behavior, or a downstream gate needs
to be updated. Do not send timer-based status comments. Acknowledge maintainer
decisions, record remaining evidence-based concerns once, and avoid relitigating
settled direction. When the issue is fixed or otherwise resolved, verify the
consumed version/revision and update the downstream issue, test, or release
gate. Keep the original report and any correction traceable.

Every task completion report states `Upstream disposition: none` when no
upstream investigation was needed, or summarizes the disposition. A task that
investigates a possible upstream defect also ends with this factual receipt,
including when no issue is filed:

```text
Upstream disposition
- Candidate repository, owner, and consumed version/revision:
- Classification and evidence:
- Deduplication searched (issues and pull requests):
- Disposition: issue URL/number, existing report updated, local fix, private
  security route, draft awaiting authority, or no confirmed upstream defect
- Maintainer decision/follow-up trigger:
- Downstream issue, gate, or consumer affected:
- Temporary mitigation owner and removal condition, or none:
- Remaining uncertainty:
```

Do not put confidential vulnerability details in this receipt. State only that
the finding was routed through the private process when appropriate.

## Source precedent and boundaries

The Bluefin contributor repository's upstream-reporting guide is a process
precedent for evidence-first reports and follow-up, not authority for Actions'
repository rules. Its history records the shift from documenting gaps as prose
to tracking them as issues ([change at `dd140d3`](https://github.com/projectbluefin/contribute/commit/dd140d3b2d201f861e3749d8b81e58d8d760abf4)); its current guide at
[`2082494`](https://github.com/projectbluefin/contribute/blob/20824949941b8ca06bad5725626c9777e5cfbe02/docs/skills/upstream-hive.md)
continues to require evidence, source permalinks, deduplication, and follow-up.
Hive-specific labels, design-response conventions, parent-issue rules, and
protocol prohibitions are intentionally not imported here.

The current RCC fork's [agent boundaries](https://github.com/joshyorko/rcc/blob/47a60ea78c5d97c892177f5649a1c950399faa6a/docs/agent-boundaries.md#sources-of-authority)
separate reading/proposals from issue mutations, and say repository guidance
cannot create GitHub credentials or authority. Its [contribution guide](https://github.com/joshyorko/rcc/blob/47a60ea78c5d97c892177f5649a1c950399faa6a/CONTRIBUTING.md)
asks contributors to search existing issues and open an issue before
non-trivial work. At that revision, RCC's [AGENTS.md](https://github.com/joshyorko/rcc/blob/47a60ea78c5d97c892177f5649a1c950399faa6a/AGENTS.md)
identifies `joshyorko/rcc` as the maintained release source and `admariner/rcc`
as historical lineage. Verify these repository facts again when reporting;
links in this guide are evidence for this policy revision, not timeless status.
