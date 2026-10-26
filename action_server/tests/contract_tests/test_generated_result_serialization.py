"""Generated helpers preserve the Core JSON-mode output contract."""

import hashlib
import json
import os
import subprocess
import sys

import pytest

from actions.server.foundry.rcc_execution import GeneratedRccExecution


@pytest.mark.parametrize(
    "logical",
    [
        pytest.param(False, id="plain"),
        pytest.param(
            True,
            id="logical",
            marks=pytest.mark.skipif(
                os.name != "posix" or not hasattr(os, "O_NOFOLLOW"),
                reason="logical context helper requires POSIX O_NOFOLLOW",
            ),
        ),
    ],
)
@pytest.mark.parametrize("kind", ["model", "mapping", "unsupported", "nonfinite"])
def test_generated_helper_serializes_core_json_outputs(tmp_path, logical, kind):
    source = tmp_path / "source"
    source.mkdir()
    value = {
        "model": "Result(rows=[Row(label='alpha', value=2)], day=date(2026, 10, 25))",
        "mapping": "{'rows': [{'label': 'alpha', 'value': 2}], 'day': '2026-10-25'}",
        "unsupported": "object()",
        "nonfinite": "{'value': float('nan')}",
    }[kind]
    (source / "fixture.py").write_text(
        "from datetime import date\nfrom pydantic import BaseModel\n"
        "class Row(BaseModel):\n label: str\n value: int\n"
        "class Result(BaseModel):\n rows: list[Row]\n day: date\n"
        f"def report(): return {value}\n"
    )
    inputs = tmp_path / "input.json"
    inputs.write_text("{}")
    result = tmp_path / "result.json"
    entrypoint = {"module": "fixture", "actionName": "report"}
    args = [str(source), str(inputs), str(result)]
    if logical:
        raw = b'{"version":"actions.logical-read-context/v1","lookups":[{"requirementId":"orders","operation":"orders.scan/v1","rows":[]}]}'
        raw = json.dumps(
            json.loads(raw), sort_keys=True, separators=(",", ":")
        ).encode()
        context = tmp_path / "context.json"
        context.write_bytes(raw)
        args += [str(context), "sha256:" + hashlib.sha256(raw).hexdigest()]
        helper = GeneratedRccExecution._bound_execution_helper(entrypoint)
    else:
        helper = GeneratedRccExecution._execution_helper(entrypoint)
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", helper, *args],
        capture_output=True,
        timeout=15,
    )
    if kind in {"unsupported", "nonfinite"}:
        assert completed.returncode != 0
        assert not result.exists()
        assert (
            "not JSON serializable"
            if kind == "unsupported"
            else "Out of range float values"
        ) in completed.stderr.decode()
    else:
        assert completed.returncode == 0, completed.stderr.decode()
        assert json.loads(result.read_bytes()) == {
            "rows": [{"label": "alpha", "value": 2}],
            "day": "2026-10-25",
        }
