# PR metrics report

`python scripts/pr_quality_report.py <export.jsonl> --output report.json` builds a deterministic report from newline-delimited PR review records. Each record requires an integer `number`; `merged`, `approved`, `changes_requested`, and `labels` are optional and are never inferred.

The report exposes record count, merged/approved/reviewed counts, acceptance and approval rates, and label counts. A null rate means the denominator was absent, not zero. The report is an operational input for review and trend analysis, not a claim about GitHub state or a public metrics endpoint.
