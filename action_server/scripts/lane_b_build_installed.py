"""Build an exact source checkpoint using the prepared RCC/Poetry toolchain.

Run inside the repository's completed Doctor/Bootstrap/ToolkitTest environment.
This adapts recovery-a38/installed-qualified/build-installed.py without mutating
the source checkout or candidate versions. Installation is task-local only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(args):
    root, destination = args.repo.resolve(), args.destination.resolve()
    # Existing destinations are refused without overwriting their prior receipts.
    destination.mkdir(mode=0o700, exist_ok=False)
    receipt = {
        "expected_source": args.source_sha,
        "python": sys.executable,
        "poetry": shutil.which("poetry"),
        "status": "RUNNING",
        "execution": "NOT_QUALIFIED",
        "commands": [],
        "wheels": {},
    }
    environment = dict(os.environ)
    environment["PIP_CACHE_DIR"] = str(destination / "pip-cache")
    environment["POETRY_CACHE_DIR"] = str(destination / "poetry-cache")
    environment["npm_config_cache"] = str(destination / "npm-cache")
    environment["XDG_CACHE_HOME"] = str(destination / "cache")
    environment["ROBOCORP_HOME"] = str(destination / "rcc-home")

    def save():
        (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def run(command, *, cwd=root, stdout=None):
        command = [str(value) for value in command]
        entry = {"argv": command, "cwd": str(cwd), "status": "RUNNING"}
        receipt["commands"].append(entry)
        save()
        with (destination / f"command-{len(receipt['commands']):02d}.log").open(
            "wb"
        ) as log:
            result = subprocess.run(
                command, cwd=cwd, env=environment, stdout=stdout or log, stderr=log
            )
        entry.update(
            status="PASS" if result.returncode == 0 else "FAIL", exit=result.returncode
        )
        save()
        result.check_returncode()

    try:
        if shutil.disk_usage(destination).free < 8 * 1024**3:
            raise ValueError("8 GiB free disk required before candidate build")
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip():
            raise ValueError("clean source checkpoint required")
        source_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
        receipt["source"] = source_sha
        if source_sha != args.source_sha:
            raise ValueError("source checkout does not match expected checkpoint")
        relative_constraints = Path(args.constraints)
        if relative_constraints.is_absolute() or ".." in relative_constraints.parts:
            raise ValueError("source-relative contained constraints required")
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", str(relative_constraints)],
            cwd=root,
            check=True,
            capture_output=True,
        )
        rcc = root / "action_server/src/actions/server/bin/rcc-18.19.3"
        if (
            subprocess.check_output(
                [str(rcc), "version"], text=True, env=environment
            ).strip()
            != "v18.19.3"
        ):
            raise ValueError("Josh RCC 18.19.3 required")
        source = destination / "source"
        source.mkdir()
        archive = destination / "source.tar"
        with archive.open("wb") as output:
            run(["git", "archive", source_sha], stdout=output)
        with tarfile.open(archive) as packed:
            packed.extractall(source, filter="data")
        archive.unlink()
        metadata = destination / "source-git.git"
        run(["git", "init", "--bare", metadata])
        git = ["git", "--git-dir=" + str(metadata)]
        run([*git, "fetch", root, source_sha])
        run([*git, "update-ref", "--no-deref", "HEAD", source_sha])
        run([*git, "read-tree", source_sha])
        run([*git, "config", "core.bare", "false"])
        run([*git, "config", "core.worktree", source])
        (source / ".git").write_text("gitdir: " + str(metadata) + "\n")
        bundled = source / rcc.relative_to(root)
        bundled.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rcc, bundled)
        bundled.chmod(0o755)
        python = root / "action_server/.venv/bin/python"
        run([python, "-m", "invoke", "build-frontend"], cwd=source / "action_server")
        run(
            [python, source / "action_server/scripts/build_oauth2_config.py"],
            cwd=source / "action_server",
        )
        inputs = (
            "action_server/src/actions/server/bin/rcc-18.19.3",
            "action_server/src/actions/server/_static_contents.py",
            "action_server/src/actions/server/_oauth2_config.py",
            "action_server/frontend/package-lock.json",
        )
        receipt["build_inputs"] = {path: digest(source / path) for path in inputs}
        for package in ("actions", "work-items", "action_server"):
            run(
                [
                    "poetry",
                    "build",
                    "--format",
                    "wheel",
                    "--output",
                    destination / "wheels" / package,
                ],
                cwd=source / package,
            )
        wheels = sorted((destination / "wheels").rglob("*.whl"))
        if len(wheels) != 3:
            raise ValueError("exact three candidate wheels required")
        receipt["wheels"] = {
            str(path.relative_to(destination)): digest(path) for path in wheels
        }
        consumer = destination / "consumer"
        run([sys.executable, "-m", "venv", consumer])
        installed = consumer / "bin/python"
        constraints = source / args.constraints
        receipt["constraints_sha256"] = digest(constraints)
        # Select the declared optional adapter extra, never a host dependency fallback.
        targets = [
            str(path)
            + ("[data-duckdb]" if path.name.startswith("actions_runtime-") else "")
            for path in wheels
        ]
        run(
            [
                installed,
                "-m",
                "pip",
                "install",
                "-c",
                constraints,
                "--report",
                destination / "install.json",
                *targets,
            ]
        )
        run([installed, "-m", "pip", "check"])
        probe = (
            "import importlib.metadata as m,pathlib,sys,actions.server,actions;"
            "assert m.version('actions-runtime')==sys.argv[1];"
            "assert m.version('actions-core')==sys.argv[2];"
            "assert pathlib.Path(actions.server.__file__).resolve().is_relative_to(pathlib.Path(sys.argv[3]));"
            "assert pathlib.Path(actions.__file__).resolve().is_relative_to(pathlib.Path(sys.argv[3]));"
            "print('installed distribution versions and origins PASS')"
        )
        run(
            [
                installed,
                "-I",
                "-c",
                probe,
                args.runtime_version,
                args.core_version,
                consumer,
            ],
            cwd=destination,
        )
        receipt["status"] = "PASS"
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__)
        raise
    finally:
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--runtime-version", required=True)
    parser.add_argument("--core-version", required=True)
    parser.add_argument(
        "--constraints",
        default="docs/program/evidence/actions-next-327/recovery-handoff-20261025/extension-handoff/dependency-constraints.txt",
    )
    build(parser.parse_args())


if __name__ == "__main__":
    main()
