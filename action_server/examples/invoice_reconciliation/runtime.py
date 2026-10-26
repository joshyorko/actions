"""Owned candidate-SDK RCC setup using the same pinned local-carrier contract."""

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import zipfile
from email.parser import BytesParser
from pathlib import Path

from actions.server._rcc_runtime_adapter import get_rcc_location, verify_rcc_version


def prepare_runtime(root: Path, retained: Path | None):
    target = root / "runtime.json"
    if target.exists():
        runtime = json.loads(target.read_text())
    else:
        wheels = root / "sdk-wheels"
        repository = Path(__file__).resolve().parents[3]
        env = dict(os.environ)
        for key in ("VIRTUAL_ENV", "POETRY_ACTIVE", "PYTHONPATH", "PYTHONHOME"):
            env.pop(key, None)
        supplied = os.environ.get("ACTIONS_INVOICE_SDK_WHEEL")
        if supplied:
            wheel = Path(supplied)
            if not wheel.is_absolute() or wheel.is_symlink() or not wheel.is_file():
                raise ValueError("regular absolute local SDK wheel input required")
            wheels.mkdir()
            shutil.copyfile(wheel, wheels / wheel.name)
        else:
            with (root / "sdk-build.log").open("w") as log:
                subprocess.run(
                    ["poetry", "build", "-f", "wheel", "-o", str(wheels)],
                    cwd=repository / "work-items",
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                    timeout=120,
                )
        entries = list(wheels.glob("*.whl"))
        if (
            len(entries) != 1
            or entries[0].name != "actions_work_items-0.5.0a1-py3-none-any.whl"
        ):
            raise ValueError("exact source candidate SDK required")
        with zipfile.ZipFile(entries[0]) as archive:
            metadata = BytesParser().parsebytes(
                archive.read(
                    next(
                        name
                        for name in archive.namelist()
                        if name.endswith(".dist-info/METADATA")
                    )
                )
            )
            if (
                metadata["Name"] != "actions-work-items"
                or metadata["Version"] != "0.5.0a1"
            ):
                raise ValueError("SDK input metadata differs from candidate")
        sdk_hash = hashlib.sha256(entries[0].read_bytes()).hexdigest()
        if retained is not None:
            runtime = json.loads(retained.read_text())
            if runtime.get("sdk_wheel_sha256") != sdk_hash:
                raise ValueError("retained runtime differs from the source SDK wheel")
        else:
            rcc = str(get_rcc_location())
            home = root / "rcc-home"
            environment = root / "package.yaml"
            environment.write_text(
                "version: 0.1\nspec-version: v2\ndependencies:\n  conda-forge:\n    - python=3.12.15\n  pypi:\n    - typing-extensions=4.16.0\npost-install:\n  - "
                + json.dumps(
                    "python -m pip install --no-deps --force-reinstall "
                    + shlex.quote(str(entries[0]))
                )
                + "\n"
            )
            owned = dict(env, ROBOCORP_HOME=str(home), ACTIONS_HOME=str(home))
            with (root / "rcc-prepare.log").open("w") as log:
                built = subprocess.run(
                    [
                        rcc,
                        "env",
                        "publish",
                        "--environment",
                        str(environment),
                        "--provider",
                        "local",
                        "--json",
                    ],
                    env=owned,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=log,
                    check=True,
                    timeout=900,
                )
            (root / "rcc-prepare.json").write_text(built.stdout)
            runtime = {
                "artifact_digest": json.loads(built.stdout)["artifactDigest"],
                "environment": str(environment),
                "sdk_wheel_sha256": sdk_hash,
                "rcc": rcc,
                "rcc_home": str(home),
            }
        target.write_text(json.dumps(runtime, indent=2) + "\n")
    if set(runtime) != {
        "artifact_digest",
        "environment",
        "sdk_wheel_sha256",
        "rcc",
        "rcc_home",
    }:
        raise ValueError("exact owned RCC runtime configuration required")
    rcc = Path(runtime["rcc"])
    verify_rcc_version(rcc)
    home = Path(runtime["rcc_home"])
    owned = dict(os.environ, ROBOCORP_HOME=str(home), ACTIONS_HOME=str(home))
    with (root / "rcc-acquire.log").open("w") as log:
        acquired = subprocess.run(
            [
                str(rcc),
                "env",
                "acquire",
                "--artifact",
                runtime["artifact_digest"],
                "--provider",
                "local",
                "--trust-carrier",
                str(home / "artifacts/v1/trust"),
                "--trust-carrier-type",
                "filesystem",
                "--permissive-local",
                "--json",
            ],
            env=owned,
            text=True,
            stdout=subprocess.PIPE,
            stderr=log,
            check=True,
            timeout=120,
        )
    (root / "rcc-acquire.json").write_text(acquired.stdout)
    receipt = json.loads(acquired.stdout)
    if (
        receipt["artifactDigest"] != runtime["artifact_digest"]
        or receipt.get("verification", {}).get("valid") is not True
    ):
        raise ValueError("RCC artifact verification failed")
    return runtime
