# Full a28 portable Runtime: FAIL retained

Frozen product source dfe2b06bebea553680d194b89297e594aead030b, Runtime 1.1.0a28. Prepared strict SQLite/PostgreSQL run: **1 failed, 2823 passed, 26 skipped, 290 deselected** in 1352.69 seconds. Owned PostgreSQL cleanup passed. Exact command in receipt.json; JUnit and log retained.

The failure is test_cli_validation_does_not_echo_rejected_secret. Earlier CLI tests leave a closed logging stream; logging inside the validation exception handler allows the logging error traceback to reveal rejected synthetic input. This is a boundary defect, not a passing qualification or fixture-only dismissal. The displayed sentinel is deliberately synthetic and is unrelated to the AppSession incident. A focused subsequent fix leaves the exception handlers before logging; its 28-case integrated result is retained alongside. The full suite has not yet been rerun with that fix.

Skip reasons are enumerated in skip-reasons.json: eight native Windows cases, twelve explicit exclusive actual-RCC gates (the separate a28 actual-RCC suite passed 12 cases), three publication/upload cases, one explicit artifact RCC vertical, one Unix-socket fixture unavailable on this filesystem, and one pinned Robot-input acceptance gate. None is silently counted as passed here.

Upstream disposition: none. Repository-owned logging boundary.

Published text/JUnit copies normalize trailing line whitespace; original raw files remain in the task evidence directory.
