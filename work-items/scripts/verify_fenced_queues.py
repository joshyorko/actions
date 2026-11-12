"""Local nonpublishing SQL conformance with one owned tmpfs PostgreSQL service.

Run through the prepared RCC toolkit. No image pull, shared service, production
database, credential lookup, or artifact cleanup outside this fixture is used.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from developer.toolkit import package_environment  # noqa: E402


def command(*args):
    return subprocess.run(
        args, text=True, capture_output=True, check=True, timeout=30
    ).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument(
        "--full",
        action="store_true",
        help="also run the SDK portable suite with the service cases required",
    )
    parser.add_argument(
        "--image",
        default="postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81",
    )
    args = parser.parse_args()
    if not args.evidence_dir.is_absolute():
        parser.error("absolute retained evidence directory required")
    attempt = str(uuid4())
    evidence = args.evidence_dir / attempt
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = {
        "head": command("git", "-C", str(ROOT), "rev-parse", "HEAD"),
        "attempt": attempt,
        "status": "FAIL",
        "cleanup": "NOT_RUN",
        "tests": {},
    }
    files = [
        *ROOT.glob("work-items/src/actions/work_items/_adapters/*.py"),
        ROOT / "work-items/src/actions/work_items/_fencing.py",
        *ROOT.glob("work-items/tests/work_items_tests/test_*fenc*.py"),
        ROOT / "work-items/pyproject.toml",
        ROOT / "work-items/poetry.lock",
        Path(__file__).resolve(),
        ROOT / "developer/toolkit.py",
        ROOT / "developer/toolkit.yaml",
    ]
    receipt["inputs"] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)
    }
    container = None
    try:
        receipt["image"] = command("docker", "image", "inspect", args.image, "--format", "{{.Id}}")
        container = command(
            "docker",
            "run",
            "--detach",
            "--pull=never",
            "--name",
            "actions-327-fenced-" + attempt,
            "--label",
            "actions327.fenced.attempt=" + attempt,
            "--memory=256m",
            "--cpus=1",
            "--pids-limit=128",
            "--tmpfs",
            "/var/lib/postgresql/data:size=128m",
            "--publish",
            "127.0.0.1::5432",
            "--env",
            "POSTGRES_PASSWORD=synthetic-fenced-only",
            args.image,
        )
        deadline = time.monotonic() + 45
        while True:
            ready = subprocess.run(
                ["docker", "exec", container, "pg_isready", "-U", "postgres"],
                capture_output=True,
                timeout=5,
            )
            if ready.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("owned PostgreSQL readiness")
            time.sleep(0.5)
        binding = command("docker", "port", container, "5432/tcp")
        receipt["postgres_version"] = command("docker", "exec", container, "postgres", "--version")
        if (
            not binding.startswith("127.0.0.1:")
            or not binding.removeprefix("127.0.0.1:").isdecimal()
        ):
            raise RuntimeError("owned fixture did not bind only loopback")
        env = package_environment(ROOT / "work-items")
        env["ACTIONS_FENCED_TEST_POSTGRES"] = (
            "postgresql://postgres:synthetic-fenced-only@" + binding + "/postgres"
        )
        env["ACTIONS_REQUIRE_FENCED_POSTGRES"] = "1"
        env["OMP_NUM_THREADS"] = "1"
        suites = {
            "conformance": [
                "tests/work_items_tests/test_fenced_queue_conformance.py",
                "tests/work_items_tests/test_postgres_fenced_schema.py",
                "tests/work_items_tests/test_sqlite_fencing.py",
            ]
        }
        if args.full:
            suites["portable"] = ["tests", "-m", "not persistent_backend_service"]
        for label, paths in suites.items():
            with (evidence / (label + ".log")).open("w") as log:
                result = subprocess.run(
                    [
                        "poetry",
                        "run",
                        "pytest",
                        *paths,
                        "-q",
                        "--junitxml=" + str(evidence / (label + ".xml")),
                    ],
                    cwd=ROOT / "work-items",
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=180,
                )
            receipt["tests"][label] = result.returncode
            xml = evidence / (label + ".xml")
            if xml.exists():
                cases = ET.parse(xml).findall(".//testcase")
                receipt.setdefault("counts", {})[label] = {
                    "tests": len(cases),
                    "skipped": sum(c.find("skipped") is not None for c in cases),
                    "failures": sum(c.find("failure") is not None for c in cases),
                    "errors": sum(c.find("error") is not None for c in cases),
                }
            if (
                result.returncode
                or not xml.exists()
                or not cases
                or (label == "conformance" and receipt["counts"][label]["skipped"])
            ):
                raise RuntimeError("required SQL conformance failed")
        receipt["status"] = "PASS"
    except Exception as error:
        receipt["failure_type"] = type(error).__name__
    finally:
        if container:
            try:
                owned_label = command(
                    "docker",
                    "inspect",
                    container,
                    "--format",
                    '{{index .Config.Labels "actions327.fenced.attempt"}}',
                )
                if owned_label != attempt:
                    raise RuntimeError("owned fixture identity changed; refusing cleanup")
                (evidence / "postgres.log").write_text(command("docker", "logs", container))
                command("docker", "rm", "--force", container)
                receipt["cleanup"] = "PASS"
            except Exception as error:
                receipt["cleanup"] = type(error).__name__
                receipt["status"] = "FAIL"
        receipt["artifacts"] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(evidence.iterdir())
            if p.is_file()
        }
        (evidence / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "evidence": str(evidence)}))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
