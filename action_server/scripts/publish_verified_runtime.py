#!/usr/bin/env python3
"""Verify and optionally publish a retained Actions Runtime artifact set."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

MANIFEST_NAME = "actions-runtime-manifest.sha256"
ARTIFACT_PATTERNS = (
    re.compile(r"^actions_runtime-(?P<version>[0-9][^/]*)\.tar\.gz$"),
    re.compile(
        r"^actions_runtime-(?P<version>[0-9][^-]*)-cp(?P<python>312|313)-cp(?P=python)-manylinux_2_17_x86_64\.manylinux_2_5_x86_64\.manylinux1_x86_64\.manylinux2014_x86_64\.whl$"
    ),
    re.compile(
        r"^actions_runtime-(?P<version>[0-9][^-]*)-cp(?P<python>312|313)-cp(?P=python)-macosx_12_0_arm64\.whl$"
    ),
    re.compile(
        r"^actions_runtime-(?P<version>[0-9][^-]*)-cp(?P<python>312|313)-cp(?P=python)-win_amd64\.whl$"
    ),
)
EXPECTED_WHEEL_ROWS = {
    ("312", "manylinux"),
    ("313", "manylinux"),
    ("312", "macos"),
    ("313", "macos"),
    ("312", "windows"),
    ("313", "windows"),
}


class VerificationError(ValueError):
    """The retained directory is not the exact verified Runtime artifact set."""


CANONICAL_WORKFLOW_PATH = ".github/workflows/actions_runtime_pypi_release.yml"
WORKFLOW_API_IDENTIFIER = "actions_runtime_pypi_release.yml"
RECOVERY_WORKFLOW_PATH = ".github/workflows/actions_runtime_recovery.yml"
RECOVERY_WORKFLOW_API_IDENTIFIER = "actions_runtime_recovery.yml"
RECOVERY_WORKFLOW_NAME = "Action Server Runtime Recovery"


def _artifact_names(directory: Path) -> list[str]:
    files = sorted(path.name for path in directory.iterdir() if path.is_file())
    if MANIFEST_NAME in files:
        files.remove(MANIFEST_NAME)
    if len(files) != 7:
        raise VerificationError(f"expected seven artifacts, found {len(files)}")
    matches = [
        next(
            (
                pattern.fullmatch(name)
                for pattern in ARTIFACT_PATTERNS
                if pattern.fullmatch(name)
            ),
            None,
        )
        for name in files
    ]
    if not all(matches):
        raise VerificationError("unexpected artifact filename")
    if sum(name.endswith(".tar.gz") for name in files) != 1:
        raise VerificationError("expected one sdist")
    if sum(name.endswith(".whl") for name in files) != 6:
        raise VerificationError("expected six wheels")
    sdist_match = ARTIFACT_PATTERNS[0].fullmatch(
        next(name for name in files if name.endswith(".tar.gz"))
    )
    version = sdist_match.group("version")
    rows = set()
    for name in files:
        if not name.endswith(".whl"):
            continue
        match = next(
            pattern.fullmatch(name)
            for pattern in ARTIFACT_PATTERNS[1:]
            if pattern.fullmatch(name)
        )
        if match.group("version") != version:
            raise VerificationError("artifact versions do not match sdist version")
        platform = (
            "manylinux"
            if "manylinux" in name
            else "macos"
            if "macosx" in name
            else "windows"
        )
        rows.add((match.group("python"), platform))
    if rows != EXPECTED_WHEEL_ROWS:
        raise VerificationError("wheel matrix does not match the approved Runtime rows")
    return files


def write_manifest(directory: Path) -> Path:
    names = _artifact_names(directory)
    manifest = directory / MANIFEST_NAME
    lines = []
    for name in names:
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def merge_downloads(download_root: Path, destination: Path) -> list[str]:
    """Copy separate artifact downloads only after basename collision checks."""
    sources: dict[str, Path] = {}
    for source in sorted(path for path in download_root.rglob("*") if path.is_file()):
        if source.name in sources:
            raise VerificationError(f"duplicate artifact basename: {source.name}")
        sources[source.name] = source
    if len(sources) != 7:
        raise VerificationError(
            f"expected seven downloaded artifacts, found {len(sources)}"
        )
    destination.mkdir(parents=True, exist_ok=True)
    for name, source in sorted(sources.items()):
        target = destination / name
        target.write_bytes(source.read_bytes())
    return (
        verify_artifacts(destination)
        if (destination / MANIFEST_NAME).exists()
        else sorted(sources)
    )


def verify_artifacts(directory: Path) -> list[str]:
    directory = directory.resolve()
    if not directory.is_dir():
        raise VerificationError(f"artifact directory does not exist: {directory}")
    names = _artifact_names(directory)
    manifest = directory / MANIFEST_NAME
    if not manifest.is_file():
        raise VerificationError("manifest is missing")
    expected = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        if (
            not separator
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or name not in names
        ):
            raise VerificationError("manifest has invalid entries")
        if name in expected:
            raise VerificationError("manifest has duplicate entries")
        expected[name] = digest
    if set(expected) != set(names):
        raise VerificationError("manifest inventory does not match artifacts")
    for name in names:
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if digest != expected[name]:
            raise VerificationError(f"checksum mismatch for {name}")
    return names


def read_pypi_token_text(contents: str) -> str | None:
    for line in contents.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if separator and key.strip() == "PYPI":
            return value.strip().strip("\"'")
    return None


def read_pypi_token(env_file: Path | None = None) -> str | None:
    token = os.environ.get("PYPI")
    if token:
        return token
    if env_file and env_file.is_file():
        return read_pypi_token_text(env_file.read_text(encoding="utf-8"))
    return None


def twine_command(directory: Path, *, publish: bool) -> list[str]:
    command = ["twine", "upload" if publish else "check", "--strict"]
    command.extend(
        str(path)
        for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix == ".whl"
    )
    command.extend(
        str(path)
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name.endswith(".tar.gz")
    )
    return command


def _run_twine(directory: Path, *, publish: bool, token: str | None) -> None:
    child_env = {
        key: value
        for key, value in os.environ.items()
        if key != "PYPI" and not key.startswith("TWINE_")
    }
    version = subprocess.run(
        ["twine", "--version"],
        check=True,
        capture_output=True,
        text=True,
        env=child_env,
    )
    match = re.search(
        r"\btwine version ([0-9]+\.[0-9]+\.[0-9]+)(?![.0-9A-Za-z-])",
        version.stdout + version.stderr,
    )
    if not match or match.group(1) != "6.2.0":
        raise RuntimeError("exact Twine 6.2.0 is required")
    check_command = twine_command(directory, publish=False)
    subprocess.run(check_command, check=True, env=child_env)
    if not publish:
        return
    if not token:
        raise RuntimeError("PYPI credential is required with --publish")
    upload_env = child_env | {"TWINE_USERNAME": "__token__", "TWINE_PASSWORD": token}
    subprocess.run(twine_command(directory, publish=True), check=True, env=upload_env)


def validate_release_run(
    metadata: dict, *, sha: str, ref: str, workflow_id: int
) -> None:
    if metadata.get("headSha") != sha:
        raise RuntimeError("the selected run does not match --sha")
    if metadata.get("headBranch") != ref:
        raise RuntimeError("the selected run does not match --ref")
    if not re.fullmatch(r"actions-runtime-[0-9]+(?:\.[0-9]+)+(?:[-A-Za-z0-9.]*)", ref):
        raise RuntimeError("--ref must be an actions-runtime version tag")
    if metadata.get("workflowName") != "Action Server PYPI Release":
        raise RuntimeError("the selected run is not the Runtime PyPI release workflow")
    selected_workflow_id = metadata.get("workflowDatabaseId")
    if (
        isinstance(selected_workflow_id, bool)
        or not isinstance(selected_workflow_id, int)
        or selected_workflow_id <= 0
    ):
        raise RuntimeError("the selected run has no valid workflow database ID")
    if selected_workflow_id != workflow_id:
        raise RuntimeError(
            "the selected run is not the canonical Runtime PyPI workflow"
        )
    if metadata.get("event") != "push":
        raise RuntimeError("the selected run is not a tag push")
    if metadata.get("conclusion") != "success":
        raise RuntimeError("the selected run did not succeed")
    if metadata.get("artifactExpired"):
        raise RuntimeError("the Runtime artifact is expired")


def validate_recovery_run(
    metadata: dict, *, sha: str, ref: str, workflow_id: int
) -> None:
    if not re.fullmatch(r"actions-runtime-[0-9]+\.[0-9]+\.[0-9]+", ref):
        raise RuntimeError("--ref must be an actions-runtime version tag")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError("--sha must be a full 40-hex release SHA")
    if not re.fullmatch(r"[0-9a-f]{40}", str(metadata.get("headSha", ""))):
        raise RuntimeError("the recovery run has no valid workflow head SHA")
    if metadata.get("headBranch") != "community":
        raise RuntimeError("the recovery run was not dispatched from community")
    if metadata.get("workflowName") != RECOVERY_WORKFLOW_NAME:
        raise RuntimeError("the selected run is not the Runtime recovery workflow")
    selected_workflow_id = metadata.get("workflowDatabaseId")
    if (
        isinstance(selected_workflow_id, bool)
        or not isinstance(selected_workflow_id, int)
        or selected_workflow_id <= 0
    ):
        raise RuntimeError(
            "the selected recovery run has no valid workflow database ID"
        )
    if selected_workflow_id != workflow_id:
        raise RuntimeError(
            "the selected run is not the canonical Runtime recovery workflow"
        )
    if metadata.get("event") != "workflow_dispatch":
        raise RuntimeError("the selected recovery run is not a manual dispatch")
    if metadata.get("conclusion") != "success":
        raise RuntimeError("the selected recovery run did not succeed")
    if metadata.get("artifactExpired"):
        raise RuntimeError("the Runtime recovery artifact is expired")
    display_title = metadata.get("displayTitle")
    if not isinstance(display_title, str) or display_title != (
        f"Runtime recovery: {ref} @ {sha}"
    ):
        raise RuntimeError("the recovery run title does not match --ref and --sha")


def workflow_database_id(
    repo: str, *, api_identifier: str, expected_path: str, workflow_label: str
) -> int:
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/actions/workflows/{api_identifier}",
                "--jq",
                "{id,path,state}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"could not resolve the {workflow_label} workflow"
        ) from error
    if not isinstance(payload, dict):
        raise RuntimeError(  # noqa: TRY004 - preserve the CLI's fail-closed error type
            f"{workflow_label} workflow metadata is malformed"
        )
    workflow_id = payload.get("id")
    if (
        isinstance(workflow_id, bool)
        or not isinstance(workflow_id, int)
        or workflow_id <= 0
    ):
        raise RuntimeError(f"{workflow_label} workflow has no valid database ID")
    if payload.get("path") != expected_path:
        raise RuntimeError(f"{workflow_label} workflow has an unexpected path")
    if payload.get("state") != "active":
        raise RuntimeError(f"{workflow_label} workflow is not active")
    return workflow_id


def canonical_workflow_id(repo: str) -> int:
    return workflow_database_id(
        repo,
        api_identifier=WORKFLOW_API_IDENTIFIER,
        expected_path=CANONICAL_WORKFLOW_PATH,
        workflow_label="canonical Runtime PyPI",
    )


def recovery_workflow_id(repo: str) -> int:
    return workflow_database_id(
        repo,
        api_identifier=RECOVERY_WORKFLOW_API_IDENTIFIER,
        expected_path=RECOVERY_WORKFLOW_PATH,
        workflow_label="Runtime recovery",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dist-dir", type=Path)
    source.add_argument("--run-id")
    source.add_argument("--download-root", type=Path)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--ref", default=None)
    parser.add_argument("--sha", default=None)
    parser.add_argument(
        "--env-file", type=Path, default=Path(__file__).resolve().parents[2] / ".env"
    )
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    directory = args.dist_dir
    if args.download_root:
        directory = Path.cwd() / "actions-runtime-dist"
        merge_downloads(args.download_root, directory)
        write_manifest(directory)
    elif args.run_id:
        if not args.repo:
            parser.error("--repo is required with --run-id")
        directory = Path.cwd() / "actions-runtime-dist"
        if not args.ref or not args.sha:
            parser.error("--ref and --sha are required with --run-id")
        result = subprocess.run(
            [
                "gh",
                "run",
                "view",
                args.run_id,
                "--repo",
                args.repo,
                "--json",
                "headSha,headBranch,workflowName,workflowDatabaseId,event,conclusion,displayTitle",
                "--jq",
                "{headSha,headBranch,workflowName,workflowDatabaseId,event,conclusion,displayTitle}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        metadata = json.loads(result.stdout)
        canonical_id = canonical_workflow_id(args.repo)
        selected_workflow_id = metadata.get("workflowDatabaseId")
        if selected_workflow_id == canonical_id:
            validate_run = validate_release_run
            workflow_id = canonical_id
        else:
            workflow_id = recovery_workflow_id(args.repo)
            if selected_workflow_id != workflow_id:
                raise RuntimeError(
                    "the selected run is not a recognized Runtime workflow"
                )
            validate_run = validate_recovery_run
        validate_run(metadata, sha=args.sha, ref=args.ref, workflow_id=workflow_id)
        artifact_result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{args.repo}/actions/runs/{args.run_id}/artifacts",
                "--jq",
                '.artifacts[] | select(.name == "actions-runtime-dist") | {artifactExpired:.expired}',
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        artifact_lines = [
            line for line in artifact_result.stdout.splitlines() if line.strip()
        ]
        if len(artifact_lines) != 1:
            raise RuntimeError("the selected run has no unique Runtime artifact")
        metadata["artifactExpired"] = json.loads(artifact_lines[0])["artifactExpired"]
        validate_run(metadata, sha=args.sha, ref=args.ref, workflow_id=workflow_id)
        command = [
            "gh",
            "run",
            "download",
            args.run_id,
            "--repo",
            args.repo,
            "--name",
            "actions-runtime-dist",
            "--dir",
            str(directory),
        ]
        subprocess.run(command, check=True)
    if directory is None:
        raise RuntimeError("an artifact directory is required")
    names = verify_artifacts(directory)
    print(f"verified {len(names)} Runtime artifacts and {MANIFEST_NAME}")
    if args.dry_run:
        print("dry-run: no upload performed")
        return 0
    _run_twine(directory, publish=args.publish, token=read_pypi_token(args.env_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
