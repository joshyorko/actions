# Task retention and final publication budget fixes

Three-file scratch-only follow-up against root's applied domain818a+runner6491 snapshot. Exact pre-edit hashes in base-hashes.json and baseline files retained. No root edits, RCC/cache/container/environment changes. Patch logical-boundary-fixes.patch.

Task: validate_bound_record defaults remain strict. Private _allow_expired_terminal permits only actual terminal metadata acknowledgement. Both TaskService._project(include_result=False) and _result(resolve=False) forward it. Pending Run use refuses; all identities, SQL seals and canonical retention timestamps remain checked. Get/publication remain strict.

Runner contract: bind_logical_execution(execution, prepared, *, publication_check=None). Trusted callback returns None or raises, pure monotonic/local cancellation only; called through LogicalPublicationGuard.publish immediately before base publication, inside transaction and after subclass validation. No standalone/generic module edits needed because their existing super().publish traverses the mixin. Root's separate runner patch supplies callback. Callback does not replace canonical DB cancellation/fences. Existing callback-free synthetic component calls remain supported.

Tests: red.xml4failed reproduces expired ack and missing budget seam; green.xml4passed. final.xml55passed19deselected13.91s (all SQLite/pure codec; no PostgreSQL fixtures instantiated). Last canonical timestamp refinement qualified retention-final.xml4passed2.80s, including corrupt seal and malformed timestamp refusing no-result acknowledgement. Mypy2sourcefiles/Ruff/isort clean. No instrumentation.

Command from scratch: PYTHONPATH=action_server/src:common/src:devutils/src:action_server/tests /workspace/actions/action_server/.venv/bin/python -m pytest -p no:robocorp_log_pytest action_server/tests/action_server_tests/test_logical_boundary_fixes.py action_server/tests/action_server_tests/test_logical_domain.py action_server/tests/action_server_tests/test_logical_receipts.py -q -k 'not postgresql' --junitxml=/workspace/actions-recovery-327/logical-boundary-fix-evidence/final.xml

Upstream disposition: both findings are repository-owned integration defects, fixed here; no new external issue. Prior Pydantic draft remains unsubmitted. Exact canonical documentation proposal attached. Remaining root-owned gates: joined PostgreSQL, pure runner cancellation/deadline wiring, installed native execution acceptance.
