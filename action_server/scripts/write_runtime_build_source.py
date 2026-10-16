"""Bind each distribution producer's bytes to its actual Git checkout and run."""

import hashlib
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

package = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1])
files = sorted(path for path in source.iterdir() if path.suffix in {".whl", ".gz"})
if not files or any(not path.is_file() or path.is_symlink() for path in files):
    raise ValueError("expected regular built distributions")
event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
result = {
    "source_sha": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip(),
    "tree": subprocess.check_output(
        ["git", "rev-parse", "HEAD^{tree}"], text=True
    ).strip(),
    "qualification_sha": event.get("pull_request", {})
    .get("head", {})
    .get("sha", os.environ["GITHUB_SHA"]),
    "run_id": os.environ["GITHUB_RUN_ID"],
    "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
    "version": tomllib.loads((package / "pyproject.toml").read_text())["tool"][
        "poetry"
    ]["version"],
    "files": {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files
    },
}
(package / "runtime-build-source.json").write_text(json.dumps(result, indent=2) + "\n")
