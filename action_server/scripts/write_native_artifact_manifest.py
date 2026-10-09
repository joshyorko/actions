"""Record measured provenance for credential-free native build outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(
    package: Path,
    *,
    source_sha: str,
    workflow_run_id: str,
    workflow_run_attempt: str,
    runner_os: str,
    build_command: str,
    output: Path,
) -> dict:
    if re.fullmatch(r"[0-9a-f]{40}", source_sha) is None:
        raise ValueError("source SHA must be a full lowercase commit SHA")
    package = package.resolve()
    repository = package.parent
    actual_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual_sha != source_sha:
        raise ValueError("checked out source SHA does not match workflow SHA")

    go_version = subprocess.run(
        ["go", "version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    suffix = ".exe" if platform.system() == "Windows" else ""
    binaries = {
        "frozen": package / "dist" / "action-server" / f"action-server{suffix}",
        "go-wrapper": package / "dist" / "final" / f"action-server{suffix}",
    }
    artifacts = {}
    for kind, binary in binaries.items():
        if not binary.is_file():
            raise FileNotFoundError(f"{kind} executable missing")
        artifacts[kind] = {
            "path": binary.relative_to(package).as_posix(),
            "sha256": sha256(binary),
        }

    manifest = {
        "schema_version": 1,
        "source_sha": actual_sha,
        "workflow_run_id": workflow_run_id,
        "workflow_run_attempt": workflow_run_attempt,
        "platform": platform.system(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "go_version": go_version,
        "build_command": build_command,
        "artifacts": artifacts,
        "artifact_downloads": {
            "go-wrapper": {
                "artifact_name": f"action-server-unauthenticated-{runner_os}",
                "archive_path": binaries["go-wrapper"].name,
            },
            "frozen": {
                "artifact_name": f"action-server-native-provenance-{runner_os}-"
                f"{workflow_run_id}-{workflow_run_attempt}",
                "archive_path": "dist/action-server/" + binaries["frozen"].name,
            },
            "manifest": {
                "artifact_name": f"action-server-native-provenance-{runner_os}-"
                f"{workflow_run_id}-{workflow_run_attempt}",
                "archive_path": "output/native-artifact-manifest.json",
            },
        },
        "provenance_scope": "checks Git HEAD only (not a clean-source attestation); hashes bytes read from executable paths (path reads follow symlinks); no candidate Core wheel is included",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--workflow-run-attempt", required=True)
    parser.add_argument("--runner-os", required=True)
    parser.add_argument("--build-command", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = Path(__file__).resolve().parents[1]
    write_manifest(
        package,
        source_sha=args.source_sha,
        workflow_run_id=args.workflow_run_id,
        workflow_run_attempt=args.workflow_run_attempt,
        runner_os=args.runner_os,
        build_command=args.build_command,
        output=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
