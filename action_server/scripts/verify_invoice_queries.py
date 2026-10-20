#!/usr/bin/env python3
"""Nonpublishing provider proof using one owned, bounded PostgreSQL fixture.

Run with the prepared RCC toolkit Python after Doctor/Bootstrap/ToolkitTest.
No image pull, reusable service, host credential, or production volume is used.
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


def command(*args, **kwargs):
    return subprocess.run(
        args, check=True, text=True, capture_output=True, timeout=60, **kwargs
    ).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument(
        "--browser",
        action="store_true",
        help="also prove the built Canvas using the isolated local browser host (not ChatGPT)",
    )
    parser.add_argument(
        "--image",
        default="postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="also run the complete portable Runtime suite",
    )
    args = parser.parse_args()
    attempt = str(uuid4())
    evidence = args.evidence_dir.resolve() / attempt
    evidence.mkdir(parents=True, exist_ok=False)
    name = "actions-327-invoice-" + attempt
    receipt = {
        "attempt": attempt,
        "status": "FAIL",
        "head": command("git", "rev-parse", "HEAD", cwd=ROOT),
        "image_reference": args.image,
        "tests": {},
        "cleanup": "NOT_RUN",
    }
    files = [
        *ROOT.glob("action_server/src/actions/server/data_queries/*.py"),
        *ROOT.glob("action_server/src/actions/server/run_outputs/*.py"),
        ROOT / "action_server/pyproject.toml",
        ROOT / "action_server/poetry.lock",
        Path(__file__).resolve(),
        *ROOT.glob("action_server/tests/action_server_tests/test_invoice_*.py"),
        ROOT / "developer/toolkit.py",
        ROOT / "developer/toolkit.yaml",
        ROOT / "action_server/src/actions/server/mcp/setup_mcp_server_v2.py",
        ROOT / "action_server/src/actions/server/_server.py",
        ROOT / "action_server/src/actions/server/_api_action_routes.py",
    ]
    receipt["inputs"] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(files)
    }
    container = None
    try:
        receipt["image"] = command(
            "docker", "image", "inspect", args.image, "--format", "{{.Id}}"
        )
        container = command(
            "docker",
            "run",
            "--detach",
            "--pull=never",
            "--name",
            name,
            "--label",
            "actions.release327.attempt=" + attempt,
            "--memory=256m",
            "--cpus=1",
            "--pids-limit=128",
            "--tmpfs",
            "/var/lib/postgresql/data:size=128m",
            "--publish",
            "127.0.0.1::5432",
            "--env",
            "POSTGRES_PASSWORD=synthetic-invoice-only",
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
                raise TimeoutError("owned PostgreSQL fixture readiness")
            time.sleep(0.5)
        port = command("docker", "port", container, "5432/tcp").removeprefix(
            "127.0.0.1:"
        )
        if not port.isdecimal():
            raise RuntimeError("fixture did not bind only loopback")
        env = package_environment(ROOT / "action_server")
        env[
            "ACTIONS_INVOICE_TEST_POSTGRES"
        ] = f"postgresql://postgres:synthetic-invoice-only@127.0.0.1:{port}/postgres"
        env["ACTIONS_REQUIRE_INVOICE_PROVIDERS"] = "1"
        env["OMP_NUM_THREADS"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if args.browser:
            resource = ROOT / "action_server/frontend/dist-canvas/index.html"
            receipt["canvas_html_sha256"] = hashlib.sha256(
                resource.read_bytes()
            ).hexdigest()
            env["ACTIONS_INVOICE_CANVAS_RESOURCE"] = str(resource)
            env["ACTIONS_INVOICE_BROWSER_EVIDENCE_DIR"] = str(
                evidence / "browser-details"
            )
            for p in [
                *ROOT.glob("action_server/frontend/apps/canvas-view/src/**/*.ts*"),
                ROOT
                / "action_server/frontend/apps/canvas-view/invoice-runtime.spec.ts",
                ROOT / "action_server/frontend/playwright.invoice.config.ts",
                ROOT / "action_server/frontend/package-lock.json",
            ]:
                receipt["inputs"][str(p.relative_to(ROOT))] = hashlib.sha256(
                    p.read_bytes()
                ).hexdigest()
        suites = {
            "invoice": [
                "tests/action_server_tests/test_invoice_providers.py",
                "tests/action_server_tests/test_invoice_run_outputs.py",
                "tests/action_server_tests/test_invoice_canvas.py",
                "tests/action_server_tests/test_invoice_canvas_mcp.py",
                "tests/action_server_tests/run_outputs",
            ]
        }
        if args.browser:
            suites["browser"] = [
                "tests/action_server_tests/test_invoice_canvas_browser.py"
            ]
        if args.full:
            suites["portable"] = ["tests", "-m", "not integration_test"]
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
                    cwd=ROOT / "action_server",
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=1200,
                )
            receipt["tests"][label] = result.returncode
            if result.returncode:
                raise RuntimeError("test gate failed: " + label)
            cases = ET.parse(evidence / (label + ".xml")).findall(".//testcase")
            counts = {
                "tests": len(cases),
                "skipped": sum(case.find("skipped") is not None for case in cases),
                "failures": sum(case.find("failure") is not None for case in cases),
                "errors": sum(case.find("error") is not None for case in cases),
            }
            receipt.setdefault("counts", {})[label] = counts
            if (
                not cases
                or counts["failures"]
                or counts["errors"]
                or (label in ("invoice", "browser") and counts["skipped"])
            ):
                raise RuntimeError("JUnit did not prove the required gate")
        receipt["status"] = "PASS"
    except Exception as exc:
        receipt["failure_type"] = type(exc).__name__
    finally:
        if container:
            try:
                # Never remove a container based only on a reusable name.
                label = command(
                    "docker",
                    "inspect",
                    container,
                    "--format",
                    '{{index .Config.Labels "actions.release327.attempt"}}',
                )
                if label != attempt:
                    raise RuntimeError("owned fixture label changed")
                (evidence / "postgres.log").write_text(
                    command("docker", "logs", container)
                )
                command("docker", "rm", "--force", container)
                receipt["cleanup"] = "PASS"
            except Exception as exc:
                receipt["status"] = "FAIL"
                receipt["cleanup"] = type(exc).__name__
        receipt["artifacts"] = {
            str(p.relative_to(evidence)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(evidence.rglob("*"))
            if p.is_file()
        }
        (evidence / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "evidence": str(evidence)}))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
