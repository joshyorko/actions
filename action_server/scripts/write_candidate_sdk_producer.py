"""Carry source and wheel identity into cibuildwheel's project-only mount."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from install_candidate_core import select_candidate

project = Path(__file__).resolve().parents[1]
wheelhouse = Path(sys.argv[1]).resolve()
wheel = select_candidate(wheelhouse, "actions-work-items")
sdk = (project.parent / "work-items/pyproject.toml").read_bytes().decode("utf-8")
producer = {
    "schema": "actions.candidate-sdk-producer/v1",
    "source_sha": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=project, text=True
    ).strip(),
    "runtime_pyproject_sha256": hashlib.sha256(
        (project / "pyproject.toml").read_bytes()
    ).hexdigest(),
    "sdk_pyproject": sdk,
    "sdk_pyproject_sha256": hashlib.sha256(sdk.encode()).hexdigest(),
    "wheel": {
        "filename": wheel.name,
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    },
}
(wheelhouse / "producer.json").write_text(json.dumps(producer, indent=2) + "\n")
