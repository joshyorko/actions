"""Record measured provenance for credential-free native build outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import stat
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def packaged_files_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    ):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def packaged_tree_inventory(root: Path) -> list[dict[str, str | int | None]]:
    inventory = []
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if path.is_symlink():
            kind = "symlink"
            target = path.readlink().as_posix()
        elif path.is_dir():
            kind = "directory"
            target = None
        elif path.is_file():
            kind = "file"
            target = None
        else:
            raise ValueError(f"unsupported packaged artifact entry: {relative!r}")
        inventory.append(
            {
                "path": relative.decode("utf-8"),
                "kind": kind,
                "mode": mode,
                "link_target": target,
                "content_sha256": sha256(path) if path.is_file() else None,
            }
        )
    return inventory


def packaged_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for entry in packaged_tree_inventory(root):
        relative = str(entry["path"]).encode("utf-8")
        digest.update(
            relative + b"\0" + str(int(entry["mode"]) & 0o777).encode() + b"\0"
        )
        if entry["kind"] == "symlink":
            digest.update(b"link\0" + str(entry["link_target"]).encode("utf-8") + b"\0")
        elif entry["kind"] == "directory":
            digest.update(b"directory\0")
        else:
            digest.update(b"file\0" + bytes.fromhex(str(entry["content_sha256"])))
    return digest.hexdigest()


def source_files_sha256(root: Path, relative_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative in relative_paths:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"wrapper source input missing: {relative}")
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(sha256(path)))
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

    frozen_tree = package / "dist" / "action-server"
    assets_zip = package / "go-wrapper" / "assets" / "assets.zip"
    wrapper_source_files = (
        "go-wrapper/main.go",
        "go-wrapper/process.go",
        "go-wrapper/go.mod",
        "go-wrapper/go.sum",
    )
    if not frozen_tree.is_dir():
        raise FileNotFoundError("frozen package tree missing")
    if not assets_zip.is_file():
        raise FileNotFoundError("Go-wrapper assets archive missing")
    measured_components = {
        "embedded_files_sha256": packaged_files_sha256(frozen_tree),
        "assets_zip_sha256": sha256(assets_zip),
        "assets_zip_path": "go-wrapper/assets/assets.zip",
        "wrapper_source_sha256": source_files_sha256(package, wrapper_source_files),
        "wrapper_source_files": list(wrapper_source_files),
        "frozen_package_tree_sha256": packaged_tree_sha256(frozen_tree),
    }
    for artifact in artifacts.values():
        artifact.update(measured_components)

    inventory_path = output.parent / "native-artifact-tree-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(packaged_tree_inventory(frozen_tree), indent=2) + "\n",
        encoding="utf-8",
    )
    for artifact in artifacts.values():
        artifact[
            "frozen_package_tree_inventory_path"
        ] = "output/native-artifact-tree-inventory.json"

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
        "provenance_scope": "checks Git HEAD only (not a clean-source attestation); hashes named file contents and frozen-tree metadata (file reads follow symlinks); no candidate Core wheel is included",
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
