#!/usr/bin/env python3
"""Verify and optionally publish a retained Actions Runtime artifact set."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
from pathlib import Path

MANIFEST_NAME = "actions-runtime-manifest.sha256"
ARTIFACT_PATTERNS = (
    re.compile(r"^actions_runtime-[0-9][^/]*\.tar\.gz$"),
    re.compile(r"^actions_runtime-[^-]+-cp(312|313)-cp\1-manylinux_[^/]*x86_64\.whl$"),
    re.compile(r"^actions_runtime-[^-]+-cp(312|313)-cp\1-macosx_12_0_arm64\.whl$"),
    re.compile(r"^actions_runtime-[^-]+-cp(312|313)-cp\1-win_amd64\.whl$"),
)


class VerificationError(ValueError):
    """The retained directory is not the exact verified Runtime artifact set."""


def _artifact_names(directory: Path) -> list[str]:
    files = sorted(path.name for path in directory.iterdir() if path.is_file())
    if MANIFEST_NAME in files:
        files.remove(MANIFEST_NAME)
    if len(files) != 7:
        raise VerificationError(f"expected seven artifacts, found {len(files)}")
    if not all(
        any(pattern.fullmatch(name) for pattern in ARTIFACT_PATTERNS) for name in files
    ):
        raise VerificationError("unexpected artifact filename")
    if sum(name.endswith(".tar.gz") for name in files) != 1:
        raise VerificationError("expected one sdist")
    if sum(name.endswith(".whl") for name in files) != 6:
        raise VerificationError("expected six wheels")
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
    version = subprocess.run(
        ["twine", "--version"], check=True, capture_output=True, text=True
    )
    if "6.2.0" not in version.stdout + version.stderr:
        raise RuntimeError("exact Twine 6.2.0 is required")
    check_command = twine_command(directory, publish=False)
    subprocess.run(check_command, check=True)
    if not publish:
        return
    if not token:
        raise RuntimeError("PYPI credential is required with --publish")
    child_env = os.environ.copy()
    child_env.update(TWINE_USERNAME="__token__", TWINE_PASSWORD=token)
    subprocess.run(twine_command(directory, publish=True), check=True, env=child_env)


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dist-dir", type=Path)
    source.add_argument("--run-id")
    parser.add_argument("--repo", default=None)
    parser.add_argument("--ref", default=None)
    parser.add_argument(
        "--env-file", type=Path, default=Path(__file__).resolve().parents[2] / ".env"
    )
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    directory = args.dist_dir
    if args.run_id:
        if not args.repo:
            parser.error("--repo is required with --run-id")
        directory = Path.cwd() / "actions-runtime-dist"
        if args.ref:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "view",
                    args.run_id,
                    "--repo",
                    args.repo,
                    "--json",
                    "headBranch",
                    "--jq",
                    ".headBranch",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout.strip() != args.ref:
                raise RuntimeError("the selected run does not match --ref")
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
    assert directory is not None
    names = verify_artifacts(directory)
    print(f"verified {len(names)} Runtime artifacts and {MANIFEST_NAME}")
    if args.dry_run:
        print("dry-run: no upload performed")
        return 0
    _run_twine(directory, publish=args.publish, token=read_pypi_token(args.env_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
