"""Carry an exact candidate SDK or Core identity into project-only wheel tests."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from install_candidate_core import select_candidate

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("wheelhouse", type=Path)
parser.add_argument(
    "--distribution",
    choices=("actions-work-items", "actions-core"),
    default="actions-work-items",
)
args = parser.parse_args()
project = Path(__file__).resolve().parents[1]
wheelhouse = args.wheelhouse.resolve()
wheel = select_candidate(wheelhouse, args.distribution)
source_directory, prefix = {
    "actions-work-items": ("work-items", "sdk"),
    "actions-core": ("actions", "core"),
}[args.distribution]
package = (
    (project.parent / source_directory / "pyproject.toml").read_bytes().decode("utf-8")
)
producer = {
    "schema": f"actions.candidate-{prefix}-producer/v1",
    "source_sha": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=project, text=True
    ).strip(),
    "runtime_pyproject_sha256": hashlib.sha256(
        (project / "pyproject.toml").read_bytes()
    ).hexdigest(),
    f"{prefix}_pyproject": package,
    f"{prefix}_pyproject_sha256": hashlib.sha256(package.encode()).hexdigest(),
    "wheel": {
        "filename": wheel.name,
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    },
}
(wheelhouse / "producer.json").write_text(json.dumps(producer, indent=2) + "\n")
