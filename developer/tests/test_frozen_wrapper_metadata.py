"""Exercise the generated artifact admission predicate with real build identities."""

import json
import os
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
BUILD_HEAD = "2f631e5403ae3ff0b37af2416dc19a98bdc04a84"
ACCEPTED_HEAD = "ba85aac7324ea4463bfba8c5f8586e27706dc2fe"


@pytest.mark.parametrize("field", [None, "head", "run", "id", "name", "size", "expired"])
@pytest.mark.skipif(os.name == "nt", reason="requires native POSIX Bash admission step")
def test_wrapper_artifact_metadata_admission(tmp_path: Path, field: str | None):
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/actions_runtime_frozen_catalog_rollback.yml").read_text(
            encoding="utf-8"
        )
    )
    step = next(
        step
        for step in workflow["jobs"]["go_wrapper"]["steps"]
        if step.get("id") == "wrapper_artifact"
    )
    env = {**os.environ, **step["env"]}
    assert env["EXPECTED_CANDIDATE_SHA"] == ACCEPTED_HEAD
    metadata = {
        "id": int(env["ARTIFACT_ID"]),
        "name": env["EXPECTED_ARTIFACT_NAME"],
        "size_in_bytes": int(env["EXPECTED_ARCHIVE_SIZE"]),
        "expired": False,
        "workflow_run": {"id": int(env["EXPECTED_RUN_ID"]), "head_sha": BUILD_HEAD},
    }
    if field == "head":
        metadata["workflow_run"]["head_sha"] = ACCEPTED_HEAD
    elif field == "run":
        metadata["workflow_run"]["id"] += 1
    elif field == "id":
        metadata["id"] += 1
    elif field == "name":
        metadata["name"] += "-other"
    elif field == "size":
        metadata["size_in_bytes"] += 1
    elif field == "expired":
        metadata["expired"] = True
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(metadata))
    predicate = next(line for line in step["run"].splitlines() if line.startswith("jq -e "))
    result = subprocess.run(
        ["bash", "-c", f"metadata={shlex.quote(str(path))}\n{predicate}"],
        env=env,
        capture_output=True,
    )
    assert result.returncode == (0 if field is None else 1), result.stderr.decode()
