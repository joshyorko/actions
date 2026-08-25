# Pull request quality rubric

Reviewers assess the change against the repository contract, not the presence of a particular file.

1. **Correctness:** focused tests cover the changed behavior, including failure and recovery paths where applicable.
2. **Safety:** trust boundaries, filesystem containment, credentials, and side effects are explicit and tested.
3. **Operations:** commands, package boundaries, configuration, and rollback/recovery evidence are documented.
4. **Scope:** the diff is cohesive, avoids unrelated generated files, and links the issue or requirement it addresses.
5. **Evidence:** the PR lists exact focused checks, skipped gates, and remaining uncertainty. Reviewers must not infer green checks from a report that did not run.

Record one of `approved`, `changes_requested`, or `commented`; do not treat missing review data as approval. The quality report consumes exported records and reports missing denominators as `null`.
