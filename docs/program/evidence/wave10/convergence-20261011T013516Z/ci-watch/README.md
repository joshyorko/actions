# Exact-head CI watch

One observation round; 2026-10-11T01:21:20.078376Z–2026-10-11T01:21:24.369599Z UTC. Stopped early after PR311 had a material completed failure.

| PR | exact head | check counts | status |
|---|---|---|---|
| 292 | `2f631e5403ae3ff0b37af2416dc19a98bdc04a84` | 19 success | terminal |
| 310 | `7c98534ad4eece6d892e3bb2957471d0f1ad76e6` | 18 success; 1 skipped; 3 in_progress | pending |
| 311 | `c888fb4a33fb2f8aa2bc30700d36ff92ccf535ca` | 18 success; 1 failure | failure; details below |

PR292: all 19 checks succeeded at its exact head; that is scoped CI evidence, not combined-tree or issue closure. PR310: 18 succeeded, the publish check was skipped for the PR event, and three build checks remain in progress:

- build (ubuntu-py3.12-devmode): in_progress — https://github.com/joshyorko/actions/actions/runs/38100704276/job/114355869990
- build (windows-py3.12-devmode): in_progress — https://github.com/joshyorko/actions/actions/runs/38100704276/job/114355869976
- build (macos-py3.12-devmode): in_progress — https://github.com/joshyorko/actions/actions/runs/38100704276/job/114355869797

PR311: the exact Windows `build (windows-py3.12-devmode)` job failed at `Test (integration)`; all other 18 checks succeeded. The job-detail endpoint shows build, upload, non-integration tests, lint, typecheck, and docs succeeded. Logs were not fetched. Failure URL: https://github.com/joshyorko/actions/actions/runs/38099013706/job/114350853595 .

Endpoint response hashes and timestamps are in `round-1.json`; failed-job detail is in `pr311-failed-job-detail.json`. No retries, source edits, PR changes, or Git mutation were performed.

Documentation: no new guide delta proposed; this is time-scoped CI status. Existing repository operations guidance requires exact check/result reporting and treats skipped or unavailable gates as unverified. The PR310 dynamic-receipt typing lesson is recorded separately in its source change.

Upstream disposition: none.
