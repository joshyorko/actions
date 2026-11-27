"""Clean-wheel and official RCC Action proof inside native ARM64 cibuildwheel."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path


def verify_evidence(
    wheelhouse: Path, evidence: Path, version: str, digest: str, source_sha: str
) -> dict[str, str]:
    wheels = sorted(wheelhouse.glob("*.whl"))
    if len(wheels) != 2:
        raise ValueError("exactly two ARM64 qualification wheels required")
    rows = set()
    measured = {}
    for wheel in wheels:
        if wheel.is_symlink() or not wheel.is_file():
            raise ValueError("regular ARM64 wheel files required")
        interpreter, abi, platforms = wheel.stem.rsplit("-", 3)[1:]
        if (
            interpreter not in {"cp312", "cp313"}
            or abi != interpreter
            or interpreter in rows
            or not all(
                tag.startswith("manylinux") and tag.endswith("_aarch64")
                for tag in platforms.split(".")
            )
        ):
            raise ValueError("native ARM64 CPython wheel matrix mismatch")
        rows.add(interpreter)
        root = evidence / wheel.stem
        proof = json.loads((root / "wheel.json").read_text())
        action = json.loads((root / "action-receipt.json").read_text())
        status = json.loads((root / "raw/action-status.json").read_text())
        wheel_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
        if (
            proof.get("status") != "PASS"
            or proof.get("qualification_sha") != source_sha
            or proof.get("wheel") != wheel.name
            or proof.get("sha256") != wheel_hash
            or proof.get("machine") not in {"aarch64", "arm64"}
            or action.get("official_contract") is not True
            or action.get("installed_wheel_sha256") != wheel_hash
            or action.get("rcc_sha256") != digest
            or action.get("rcc_version") != "v" + version
            or action.get("import_exit") != 0
            or action.get("synthetic_result") != "arm64:synthetic"
            or status.get("status") != 200
            or not status.get("run_id")
            or json.loads((root / "raw/action-response.json").read_text())
            != "arm64:synthetic"
        ):
            raise ValueError("ARM64 wheel Action receipt differs from producer bytes")
        originals = ("floor.log", "smoke.log", "raw/import.log", "raw/server.log")
        if any(not (root / name).is_file() for name in originals):
            raise ValueError("original ARM64 qualification logs missing")
        measured[wheel.name] = wheel_hash
    return measured


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("project", type=Path)
    parser.add_argument("--verify-evidence", action="store_true")
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine().lower() not in {
        "aarch64",
        "arm64",
    }:
        parser.error("native Linux ARM64 required")
    if args.verify_evidence:
        from actions.server._download_rcc import RCC_VERSION
        from actions.server._rcc_platform import LINUX_ARM64_RELEASE_SHA256

        files = verify_evidence(
            args.wheel,
            args.project,
            RCC_VERSION,
            LINUX_ARM64_RELEASE_SHA256[RCC_VERSION],
            os.environ["GITHUB_SHA"],
        )
        (args.project / "qualification.json").write_text(
            json.dumps(
                {
                    "qualification_only": True,
                    "status": "PASS",
                    "source_sha": os.environ["GITHUB_SHA"],
                    "rcc_version": RCC_VERSION,
                    "rcc_sha256": LINUX_ARM64_RELEASE_SHA256[RCC_VERSION],
                    "files": files,
                },
                indent=2,
            )
            + "\n"
        )
        return
    wheel = args.wheel.resolve(strict=True)
    project = args.project.resolve(strict=True)
    evidence = project / "arm64-wheel-evidence" / wheel.stem
    evidence.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="arm64-wheel-rcc-") as temporary:
        environment = os.environ.copy()
        environment["ROBOCORP_HOME"] = temporary
        with (evidence / "floor.log").open("wb") as log:
            subprocess.run(
                [
                    sys.executable,
                    str(project / "scripts/verify_published_runtime_floor.py"),
                    "--installed-wheel",
                    str(wheel),
                    "--checkout-root",
                    str(project),
                    "--candidate-sdk-wheelhouse",
                    str(project / "candidate-sdk-wheelhouse"),
                    "--candidate-core-wheelhouse",
                    str(project / "candidate-core-wheelhouse"),
                ],
                check=True,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        from actions.server._download_rcc import get_default_rcc_location

        rcc = get_default_rcc_location().resolve(strict=True)
        with (evidence / "smoke.log").open("wb") as log:
            subprocess.run(
                [
                    sys.executable,
                    str(project / "scripts/verify_linux_arm64_candidate.py"),
                    "--official",
                    "--rcc",
                    str(rcc),
                    "--rcc-sha256",
                    hashlib.sha256(rcc.read_bytes()).hexdigest(),
                    "--output",
                    str(evidence / "action-receipt.json"),
                    "--evidence-dir",
                    str(evidence / "raw"),
                ],
                check=True,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
    (evidence / "wheel.json").write_text(
        json.dumps(
            {
                "wheel": wheel.name,
                "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                "python": sys.version,
                "machine": platform.machine(),
                "qualification_sha": os.environ["ACTIONS_CANDIDATE_SOURCE_SHA"],
                "status": "PASS",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
