# AI quality and observability runbook

## Produce a report

Export one JSON object per pull request to a JSONL file, then run:

```sh
python scripts/pr_quality_report.py /path/to/pr-records.jsonl --output report.json
```

Inspect `schema`, denominators, and `limitations` before sharing the result. Keep the export and generated report as CI artifacts; do not commit private review data.

## Triage

- `records` is zero: the export job or filter is wrong; do not call this a zero acceptance rate.
- A rate is `null`: collect the corresponding field before making a trend claim.
- A report disagrees with GitHub: retain the export, check its timestamp and query, and regenerate; this script does not contact GitHub.

## Audit evidence

Reviewers use [the PR rubric](review-rubric.md). The audit workflow records the commit, changed files, and test command output as a run artifact. It does not approve, merge, or remove holds.
