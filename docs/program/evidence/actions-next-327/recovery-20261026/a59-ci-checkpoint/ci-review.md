# CI/test patch review

Reviewed the requested CI/test changes in `/workspace/actions` against `a90d6cdb8af8b07bf534953903f157d003a4d322`. This was a read-only review; no tests were run, per assignment.

## Result

No patch-introduced validation weakening, secret disclosure, false evidence, or Python path issue found in the requested files.

- The published-Core location summarizer recognizes an explicit `published` profile mapped to the exact published test name, and rejects unknown profiles before opening JUnit. It emits only bounded numeric source lines and fixed exception enums, with size/location caps; it does not return raw failure text or paths (`action_server/scripts/summarize_candidate_failure_327.py:15-24,59-107`). Its invocation follows capture of `pytest_status`; a failed/unavailable advisory command is caught and does not replace the strict JUnit/receipt acceptance path (`.github/workflows/_gen_workflows.py:748-761`).
- The source Runtime launcher check now requires the `-P -m actions.server` prefix and an absolute interpreter in the published-Core validator/diagnostic mirror. The candidate validator and frontend published receipt validator use the same prefix. This tightens source-path isolation; it does not relax source/module digest, worker, browser, JUnit, or pytest checks (`_gen_workflows.py:902-907`; generated workflow counterparts reviewed).
- The candidate admission test constructs a synthetic forward projection of the retained receipt for the new `-P` prefix and expressly identifies it as an admission fixture, not new execution evidence. Its negative cases still reject a missing prefix and altered source/worker identity (`developer/tests/test_canvas_candidate_receipt_327.py`).
- Published diagnostics report pytest, JUnit, and receipt status independently and retain only predicate identifiers, pass/fail/unavailable enums, and fixed error classes. The uploaded diagnostic and sanitized JUnit paths do not include raw pytest output. The summarizer also omits all raw message/path content.
- `publish_evidence.sh` resolves `python3`, then `python`, fails before scanning/commit/push if neither resolves, quotes both interpreter and scanner paths, and leaves the staged scan and `diff --cached --check` ahead of commit and push. The tests exercise a PATH with only the Python fallback, including a secret-valued scan failure that prevents commit/push and suppresses the secret (`scripts/publish_evidence.sh:8-21`; `developer/tests/test_evidence_publication.py`).

The reported historical Ubuntu published pytest failure remains unexplained by this diff. A stricter receipt predicate and a synthetic admission projection establish the validator behavior only; they do not establish why the historical pytest case failed. The new diagnostic may help identify its source line when run against that failure’s JUnit, but no such evidence was reviewed here.

## Documentation improvement

- Canonical file changed or proposed: `docs/skills/repository-operations.md` (propose retaining/reconciling the current dirty changes around lines 2243-2274).
- Durable learning captured: Keep the `-P` launcher prefix synchronized across producer, validator, and diagnostic mirror; treat the admission projection as synthetic; keep published diagnostics profile-bound and advisory; do not infer a pytest cause from a receipt-admission failure.
- Evidence: Reviewed `_gen_workflows.py:751-761,902-907,941-954`, the summarizer implementation, and `developer/tests/test_canvas_candidate_receipt_327.py` / `test_canvas_published_workflow.py`.
- Stale or ambiguous guidance removed: None proposed; the working guide change already clarifies the observed invariants.
- Remaining uncertainty: The actual historical published JUnit failure was not available in the reviewed diff, so its root cause remains unknown.

Upstream disposition: none
