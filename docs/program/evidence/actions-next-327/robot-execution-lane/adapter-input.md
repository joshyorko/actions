# New adapter input contract proof

Separate incremental test slice; production adapter bc9896d and documentation
3de78ad remain unchanged. Six new cases passed, 32 existing adapter cases were
deselected. This is new direct Robot proof, not the earlier 216-case receipt and
not installed canonical host or RCC input qualification.

Actual Robot reads `${INPUT_FILE}` through a source-archived Python library,
compares exact canonical bytes and typed nested/Unicode values; shell syntax,
Robot-like variables and command substitutions remain literal JSON data. The
retained file and host intent selection retain identical bytes and source digest.
Invalid integer values (boolean/string), noncanonical JSON, non-object JSON and
malformed JSON reject before any launch intent or staging.

Command after sourcing task-local env.sh, from lane worktree:

```sh
rcc task script -r developer/toolkit.yaml -- python /workspace/lane-c-state/package-command.py run pytest -p no:robocorp_log_pytest tests/contract_tests/test_robot_execution.py -k 'input_file or input_schema or input_encoding' -q --basetemp=/workspace/lane-c-state/adapter-input --junitxml=/workspace/lane-c-state/receipts/adapter-input.xml
```

Pinned RCC18.19.3, package-local Poetry; result **6 passed,32 deselected**.
JUnit retained alongside this file. Scoped Ruff check/format and isort were run;
initial format check failed and its log remains in task receipts; Ruff formatting
corrected the test only. No production implementation changed. Host lifecycle is
still a spy; no queue/database/admission proof is asserted. Roll back this test
commit independently. Upstream disposition: none.
