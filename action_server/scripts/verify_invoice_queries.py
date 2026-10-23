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


def suite_environment(label: str, environment: dict[str, str]) -> dict[str, str]:
    result = dict(environment)
    if label == "portable":
        # Actual pinned task inputs already run with zero skips in worker.
        # Do not rebuild the same multi-GB RCC fixture in the portable suite.
        result.pop("ACTIONS_ROBOT_INPUT_RCC", None)
    return result


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
    parser.add_argument(
        "--worker",
        action="store_true",
        help="also prove the fixed invoice task with owned local RCC artifact and installed SDK",
    )
    parser.add_argument(
        "--generated",
        action="store_true",
        help="prove existing generated revision through review, RCC and artifact readback",
    )
    parser.add_argument(
        "--worker-runtime",
        type=Path,
        help="explicit retained task-owned SDK-only RCC artifact configuration",
    )
    parser.add_argument(
        "--effects",
        action="store_true",
        help="prove explicit owned synthetic-effect reconciliation and bounded dead letters",
    )
    args = parser.parse_args()
    if args.worker_runtime is not None and not (
        args.worker or args.generated or args.effects
    ):
        parser.error("--worker-runtime requires --worker, --generated or --effects")
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
        *ROOT.glob("action_server/src/actions/server/foundry/*.py"),
        *ROOT.glob("action_server/src/actions/server/managed_work_items/*.py"),
        *ROOT.glob("action_server/tests/action_server_tests/test_managed_work_items_*.py"),
        ROOT / "action_server/tests/action_server_tests/test_native_run_authority.py",
        *ROOT.glob("action_server/src/actions/server/deployments/*.py"),
        ROOT / "action_server/tests/action_server_tests/foundry_fixtures.py",
        *ROOT.glob("action_server/tests/action_server_tests/test_foundry_*.py"),
        *[
            p
            for p in ROOT.glob("action_server/examples/invoice_reconciliation/**/*")
            if p.is_file() and "__pycache__" not in p.parts
        ],
        ROOT / "action_server/frontend/scripts/capture-invoice-reconciliation.mjs",
        ROOT / "action_server/tests/action_server_tests/test_browser_gate_selection.py",
        ROOT
        / "action_server/tests/action_server_tests/test_browser_origin_acceptance.py",
        ROOT / "action_server/pyproject.toml",
        ROOT / "action_server/poetry.lock",
        Path(__file__).resolve(),
        *ROOT.glob("action_server/tests/action_server_tests/test_invoice_*.py"),
        *ROOT.glob(
            "action_server/tests/action_server_tests/test_generated_invoice*.py"
        ),
        ROOT / "action_server/src/actions/server/canvas_lifecycle.py",
        ROOT / "action_server/tests/action_server_tests/test_canvas_lifecycle.py",
        ROOT / "action_server/tests/action_server_tests/invoice_effect_fixture.py",
        ROOT / "developer/toolkit.py",
        ROOT / "developer/toolkit.yaml",
        ROOT / "action_server/src/actions/server/mcp/setup_mcp_server_v2.py",
        ROOT / "action_server/src/actions/server/_server.py",
        ROOT / "action_server/src/actions/server/_api_action_routes.py",
        ROOT / "action_server/src/actions/server/canvas_lifecycle.py",
        ROOT / "action_server/tests/action_server_tests/test_canvas_lifecycle.py",
        ROOT / "action_server/tests/action_server_tests/test_knowledge_collections.py",
        ROOT / "action_server/tests/action_server_tests/test_candidate_work_items.py",
        ROOT / "work-items/src/actions/work_items/_adapters/_sql_review.py",
        ROOT / "work-items/pyproject.toml",
        ROOT / "action_server/src/actions/server/_models.py",
        ROOT / "action_server/src/actions/server/_rcc_runtime_adapter.py",
        ROOT / "action_server/tests/action_server_tests/test_rcc_runtime_adapter.py",
        ROOT / "action_server/tests/action_server_tests/test_robot_run_inputs.py",
        ROOT / "action_server/src/actions/server/_robot_inputs.py",
        ROOT / "action_server/src/actions/server/migrations/__init__.py",
        ROOT
        / "action_server/src/actions/server/migrations/migration_add_invoice_reviews.py",
        ROOT
        / "action_server/src/actions/server/migrations/migration_add_foundry_records.py",
        ROOT / "action_server/tests/action_server_tests/test_foundry_storage.py",
        ROOT / "action_server/src/actions/server/migrations/migration_allow_package_less_canvas.py",
        ROOT / "action_server/tests/action_server_tests/test_foundry_package_less_storage.py",
        ROOT / "action_server/tests/action_server_tests/test_foundry_deployments.py",
    ]
    receipt["inputs"] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(files)
    }
    container = None
    try:
        # Editable environments belong to one exact checkout. Hashing this tree
        # does not prove that Poetry imports it, so reject another checkout first.
        probe = """
import hashlib, importlib, json, sys
from pathlib import Path
source = Path(sys.argv[1]).resolve()
identities = {}
for name in ('actions.server.foundry.sql_authoring', 'actions.server.foundry.sql_authorization', 'actions.server.foundry.authoring', 'actions.server.foundry.boot', 'actions.server.foundry.discovery', 'actions.server.deployments.package_revision_compiler', 'actions.server.deployments.foundry_repository', 'actions.server.deployments.foundry_service', 'actions.server.deployments.foundry_values', 'actions.server.foundry.models', 'actions.server.canvas_lifecycle', 'actions.server.data_queries.review', 'actions.server.data_queries.invoice_worker', 'actions.server.data_queries.generated', 'actions.server.data_queries.invoice_effects', 'actions.server.data_queries.knowledge',
             'actions.server.data_queries.invoices', 'actions.server.run_outputs.service'):
    module = importlib.import_module(name)
    path = Path(module.__file__).resolve()
    if not path.is_relative_to(source):
        raise RuntimeError('Runtime module belongs to another source checkout')
    identities[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
from importlib.metadata import distribution
sdk = distribution('actions-work-items')
module = importlib.import_module('actions.work_items._adapters._sql_review')
path = Path(module.__file__).resolve()
expected = source.parent.parent / 'work-items/src/actions/work_items/_adapters/_sql_review.py'
if sdk.version != '0.5.0a1' or not path.is_relative_to(Path(sys.prefix).resolve()) or path.read_bytes() != expected.read_bytes():
    raise RuntimeError('installed candidate SDK differs from the selected source')
identities['actions.work_items._adapters._sql_review'] = {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'version':sdk.version}
print(json.dumps(identities))
"""
        receipt["module_identity"] = json.loads(
            command(
                "poetry",
                "run",
                "python",
                "-c",
                probe,
                str(ROOT / "action_server/src"),
                cwd=ROOT / "action_server",
                env=package_environment(ROOT / "action_server"),
            )
        )
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
            "--memory=768m" if args.full else "--memory=256m",
            "--cpus=1",
            "--pids-limit=128",
            "--tmpfs",
            # The full package repeats schema-heavy SQL cases after the focused
            # gates. PostgreSQL WAL exhausted 128 MiB before that run finished.
            "/var/lib/postgresql/data:size=512m"
            if args.full
            else "/var/lib/postgresql/data:size=128m",
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
        if args.browser or args.generated:
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
        if args.worker or args.generated or args.effects:
            import platform

            if platform.system() != "Linux":
                raise RuntimeError(
                    "invoice worker proof currently requires Linux owned filesystem provider"
                )
            wheels = evidence / "sdk-wheels"
            build = subprocess.run(
                ["poetry", "build", "-f", "wheel", "-o", str(wheels)],
                cwd=ROOT / "work-items",
                env=package_environment(ROOT / "work-items"),
                capture_output=True,
                text=True,
                timeout=120,
            )
            (evidence / "sdk-build.log").write_text(build.stdout + build.stderr)
            build.check_returncode()
            entries = list(wheels.iterdir())
            if (
                len(entries) != 1
                or entries[0].name != "actions_work_items-0.5.0a1-py3-none-any.whl"
                or entries[0].is_symlink()
            ):
                raise RuntimeError("one exact candidate SDK wheel required")
            wheel = entries[0]
            wheel_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
            rcc = command(
                "poetry",
                "run",
                "python",
                "-c",
                "from actions.server._rcc_runtime_adapter import get_rcc_location; print(get_rcc_location())",
                cwd=ROOT / "action_server",
                env=package_environment(ROOT / "action_server"),
            )
            if args.worker_runtime is not None:
                retained = json.loads(args.worker_runtime.read_text())
                if set(retained) != {
                    "artifact_digest",
                    "environment",
                    "sdk_wheel_sha256",
                    "rcc",
                    "rcc_home",
                }:
                    raise RuntimeError("unexpected retained runtime fields")
                if (
                    retained["sdk_wheel_sha256"] != wheel_hash
                    or Path(retained["rcc"]).resolve() != Path(rcc).resolve()
                ):
                    raise RuntimeError(
                        "retained runtime SDK/RCC differs from current source/toolchain"
                    )
                environment = Path(retained["environment"])
                rcc_home = Path(retained["rcc_home"])
                artifact = retained["artifact_digest"]
                worker_env = dict(
                    env, ROBOCORP_HOME=str(rcc_home), ACTIONS_HOME=str(rcc_home)
                )
                receipt["retained_worker_runtime"] = {
                    "path": str(args.worker_runtime.resolve()),
                    "sha256": hashlib.sha256(
                        args.worker_runtime.read_bytes()
                    ).hexdigest(),
                    "environment_sha256": hashlib.sha256(
                        environment.read_bytes()
                    ).hexdigest(),
                }
            else:
                fixture = evidence / "worker-environment"
                fixture.mkdir()
                environment = fixture / "package.yaml"
                environment.write_text(
                    "version: 0.1\nspec-version: v2\ndependencies:\n  conda-forge:\n    - python=3.12.15\n  pypi:\n    - typing-extensions=4.16.0\npost-install:\n  - python -m pip install --no-deps --force-reinstall "
                    + str(wheel)
                    + "\n"
                )
                rcc_home = evidence / "rcc-home"
                worker_env = dict(
                    env, ROBOCORP_HOME=str(rcc_home), ACTIONS_HOME=str(rcc_home)
                )
                with (evidence / "rcc-prepare.log").open("w") as log:
                    prepared = subprocess.run(
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
                        env=worker_env,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=log,
                        timeout=900,
                    )
                (evidence / "rcc-prepare.json").write_text(prepared.stdout)
                prepared.check_returncode()
                artifact = json.loads(prepared.stdout)["artifactDigest"]
                # Preserve local provider and the existing permissive-local policy;
                # RCC18.19.3 otherwise treats the 'local' alias as an HTTP carrier.
            with (evidence / "rcc-acquire.log").open("w") as log:
                acquired = subprocess.run(
                    [
                        rcc,
                        "env",
                        "acquire",
                        "--artifact",
                        artifact,
                        "--provider",
                        "local",
                        "--trust-carrier",
                        str(rcc_home / "artifacts/v1/trust"),
                        "--trust-carrier-type",
                        "filesystem",
                        "--permissive-local",
                        "--json",
                    ],
                    env=worker_env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=log,
                    timeout=120,
                )
            (evidence / "rcc-acquire.json").write_text(acquired.stdout)
            acquired.check_returncode()
            acquired_result = json.loads(acquired.stdout)
            if (
                acquired_result.get("artifactDigest") != artifact
                or acquired_result.get("verification", {}).get("valid") is not True
            ):
                raise RuntimeError("worker artifact acquisition not verified")
            config = evidence / "worker-runtime.json"
            config.write_text(
                json.dumps(
                    {
                        "artifact_digest": artifact,
                        "environment": str(environment),
                        "sdk_wheel_sha256": wheel_hash,
                        "rcc": rcc,
                        "rcc_home": str(rcc_home),
                    }
                )
            )
            env.update(
                ACTIONS_INVOICE_WORKER_EVIDENCE_DIR=str(evidence / "worker-cells"),
                ACTIONS_INVOICE_WORKER_ENVIRONMENT=str(config),
                ACTIONS_REQUIRE_INVOICE_WORKER="1",
            )
            if args.worker:
                env["ACTIONS_ROBOT_INPUT_RCC"] = rcc
            receipt["worker_runtime"] = {
                "artifact_digest": artifact,
                "sdk_wheel_sha256": wheel_hash,
                "rcc_sha256": hashlib.sha256(Path(rcc).read_bytes()).hexdigest(),
                "config": str(config),
            }
        suites = {
            "foundry_storage": [
                "tests/action_server_tests/test_foundry_storage.py",
                "tests/action_server_tests/test_foundry_package_less_storage.py",
                "tests/action_server_tests/test_foundry_deployments.py",
                "tests/action_server_tests/test_foundry_sql_authoring.py",
                "tests/action_server_tests/test_native_run_authority.py",
            ],
            "components": [
                "tests/action_server_tests/test_invoice_review.py",
                "tests/action_server_tests/test_invoice_review_mcp.py",
                "tests/action_server_tests/test_candidate_work_items.py",
                "tests/action_server_tests/test_canvas_lifecycle.py",
                "tests/action_server_tests/test_knowledge_collections.py",
                "tests/action_server_tests/test_foundry_authoring.py",
                "tests/action_server_tests/test_foundry_boot.py",
                "tests/action_server_tests/test_foundry_discovery.py",
                "tests/action_server_tests/mcp/test_foundry_mcp.py",
            ],
            "invoice": [
                "tests/action_server_tests/test_invoice_providers.py",
                "tests/action_server_tests/test_invoice_run_outputs.py",
                "tests/action_server_tests/test_invoice_canvas.py",
                "tests/action_server_tests/test_invoice_canvas_mcp.py",
                "tests/action_server_tests/run_outputs",
            ],
        }
        if args.worker:
            suites["worker"] = [
                "tests/action_server_tests/test_invoice_worker.py",
                "tests/action_server_tests/test_invoice_worker_mcp.py",
                "tests/action_server_tests/test_robot_run_inputs.py",
                "tests/action_server_tests/test_rcc_runtime_adapter.py::test_local_worker_carrier_keeps_provider_and_policy_explicit",
                "tests/action_server_tests/test_rcc_runtime_adapter.py::test_local_carrier_cannot_replace_nonlocal_provider_trust",
            ]
        if args.browser:
            suites["browser"] = [
                "tests/action_server_tests/test_invoice_canvas_browser.py"
            ]
        if args.generated:
            suites["generated"] = [
                "tests/action_server_tests/test_generated_invoice.py"
            ]
            if args.browser:
                suites["generated"].append(
                    "tests/action_server_tests/test_generated_invoice_browser.py"
                )
        if args.effects:
            suites["effects"] = ["tests/action_server_tests/test_invoice_effects.py"]
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
                    env=suite_environment(label, env),
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
                or (
                    label
                    in (
                        "foundry_storage",
                        "components",
                        "invoice",
                        "browser",
                        "worker",
                        "generated",
                        "effects",
                    )
                    and counts["skipped"]
                )
            ):
                raise RuntimeError("JUnit did not prove the required gate")
        for relative, expected in receipt["inputs"].items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
                raise RuntimeError(
                    "source input changed during verification: " + relative
                )
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
