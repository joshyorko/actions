#!/usr/bin/env python3
"""Run a disposable local RCC Action through authenticated Runtime HTTP."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prove the source Runtime's local RCC Environment Artifact and process "
            "lease with a synthetic Action over authenticated HTTP."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("candidate-wheel",),
        default="candidate-wheel",
        help="Use local candidate Core/Helper wheels with the source Runtime.",
    )
    return parser


def _start_provider(rcc_binary: str, root: Path, env: dict[str, str]):
    process = subprocess.Popen(
        [
            rcc_binary,
            "cache",
            "serve",
            "--root",
            str(root / "provider"),
            "--listen",
            "127.0.0.1:0",
            "--json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    assert process.stdout is not None
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        if not selector.select(timeout=10):
            process.terminate()
            process.wait(timeout=10)
            raise RuntimeError("RCC cache serve did not return startup JSON in 10s")
        startup = process.stdout.readline()
    if process.poll() is not None or not startup:
        stderr = process.stderr.read() if process.stderr else ""
        process.wait()
        raise RuntimeError(f"RCC cache serve failed to start: {stderr[-1000:]}")
    try:
        url = json.loads(startup)["url"]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        process.terminate()
        process.wait(timeout=10)
        raise RuntimeError("RCC cache serve returned invalid startup JSON") from exc
    if not url.startswith("http://127.0.0.1:"):
        process.terminate()
        process.wait(timeout=10)
        raise RuntimeError("RCC cache serve did not bind to loopback")
    return process, url


def _build_candidate_wheels(root: Path) -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[2]
    poetry = os.environ.get("ACTIONS_ACCEPTANCE_POETRY") or shutil.which("poetry")
    if not poetry:
        raise RuntimeError(
            "ACTIONS_ACCEPTANCE_POETRY must point to Poetry from the pinned RCC toolchain"
        )
    wheelhouse = root / "candidate-wheelhouse"
    wheelhouse.mkdir()
    env = os.environ.copy()
    env["POETRY_CACHE_DIR"] = str(root / "poetry-cache")
    for package_dir in (repo_root / "actions-http-helper", repo_root / "actions"):
        subprocess.run(
            [poetry, "build", "--format", "wheel", "--output", str(wheelhouse)],
            cwd=package_dir,
            env=env,
            check=True,
            timeout=300,
        )
    core = wheelhouse / "actions_core-1.0.2-py3-none-any.whl"
    helper = wheelhouse / "actions_http_helper-1.0.2-py3-none-any.whl"
    if not core.is_file() or not helper.is_file():
        raise RuntimeError("Poetry did not produce the expected candidate wheels")
    return core, helper


def _run() -> dict[str, object]:
    sys.path.insert(0, str(_source_root() / "src"))

    import requests

    from actions.server._models import ActionPackage, Run, RunStatus, load_db
    from actions.server._rcc_runtime_adapter import read_receipt
    from actions.server._selftest import ActionServerProcess

    rcc_binary = os.environ.get("ACTIONS_RUNTIME_RCC_BINARY")
    if not rcc_binary:
        raise RuntimeError("ACTIONS_RUNTIME_RCC_BINARY must name pinned RCC v18.19.3")
    with tempfile.TemporaryDirectory(prefix="dakota-rcc-acceptance-") as temp:
        root = Path(temp)
        core_wheel, helper_wheel = _build_candidate_wheels(root)
        package_dir = root / "package"
        package_dir.mkdir()
        (package_dir / "package.yaml").write_text(
            f"""version: 0.1
spec-version: v2
name: dakota-rcc-acceptance
dependencies:
  conda-forge:
    - python=3.12.15
  pypi:
    - actions-core @ {core_wheel.as_uri()}
    - actions-http-helper @ {helper_wheel.as_uri()}
""",
            encoding="utf-8",
        )
        (package_dir / "action.py").write_text(
            "import json\n"
            "from importlib.metadata import version\n"
            "from actions import action\n"
            "from actions.server_integration import ManagedParameters\n\n"
            "@action\n"
            "def answer() -> str:\n"
            "    return json.dumps({\n"
            "        'result': 'dakota-rcc-local-acceptance',\n"
            "        'actions_core': version('actions-core'),\n"
            "        'actions_http_helper': version('actions-http-helper'),\n"
            "        'server_integration': ManagedParameters.__name__,\n"
            "    }, sort_keys=True)\n",
            encoding="utf-8",
        )

        environment = os.environ.copy()
        environment.update(
            {
                "ACTIONS_REAL_RCC_ARTIFACT_TEST": "1",
                "ACTIONS_RUNTIME_RCC_BINARY": rcc_binary,
                "ROBOCORP_HOME": str(root / "rcc-home"),
            }
        )
        provider, provider_url = _start_provider(rcc_binary, root, environment)
        environment["ACTIONS_RUNTIME_RCC_PROVIDER"] = provider_url
        api_key = "synthetic-dakota-rcc-acceptance-key"
        datadir = root / "runtime-data"
        server = None
        run_id = ""
        try:
            server = ActionServerProcess(datadir)
            server.start(
                timeout=900,
                db_file="server.db",
                actions_sync=True,
                cwd=package_dir,
                min_processes=0,
                max_processes=1,
                additional_args=[
                    "--address=127.0.0.1",
                    "--api-key",
                    api_key,
                ],
                env=environment,
                port=0,
            )
            base_url = f"http://{server.host}:{server.port}"
            action_url = f"{base_url}/api/actions/dakota-rcc-acceptance/answer/run"

            unauthenticated = requests.post(action_url, json={}, timeout=20)
            if unauthenticated.status_code not in (401, 403):
                raise AssertionError(
                    "Runtime did not reject the unauthenticated synthetic Action"
                )

            response = requests.post(
                action_url,
                json={},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=900,
            )
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Action HTTP {response.status_code}: {response.text[:1000]}\n"
                    f"Runtime diagnostics:\n{server.get_stderr()[-12000:]}"
                )
            response.raise_for_status()
            expected_result = {
                "result": "dakota-rcc-local-acceptance",
                "actions_core": "1.0.2",
                "actions_http_helper": "1.0.2",
                "server_integration": "ManagedParameters",
            }
            candidate_result = json.loads(response.json())
            if candidate_result != expected_result:
                raise AssertionError("Action returned an unexpected result")
            run_id = response.headers.get("x-action-server-run-id", "")
            if not run_id:
                raise AssertionError("Runtime did not return a run identity")

            detail = requests.get(
                f"{base_url}/api/runs/{run_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=20,
            )
            detail.raise_for_status()
            if detail.json().get("id") != run_id:
                raise AssertionError("SQLite-backed run lookup returned another run")
        finally:
            try:
                if server is not None:
                    server.stop()
            finally:
                provider.terminate()
                try:
                    provider.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    provider.kill()
                    provider.wait()

        db_path = datadir / "server.db"
        with load_db(db_path) as db:
            with db.connect():
                run = next((item for item in db.all(Run) if item.id == run_id), None)
                if run is None or run.status != RunStatus.PASSED:
                    raise AssertionError("SQLite did not persist a passed Action run")
                if json.loads(run.result or "null") != json.dumps(
                    expected_result, sort_keys=True
                ):
                    raise AssertionError("SQLite persisted an unexpected Action result")
                package = db.all(ActionPackage)[0]
                runtime = json.loads(package.env_json)["runtime"]

        digest = runtime["artifact_digest"]
        if not digest.startswith("sha256:"):
            raise AssertionError("Runtime did not persist the RCC Artifact digest")
        receipts = sorted((datadir / "rcc-receipts").glob("*.json"))
        if not receipts:
            raise AssertionError("Runtime produced no RCC process receipt")
        receipt = read_receipt(receipts[-1], digest)
        if not receipt.get("leaseId"):
            raise AssertionError("RCC receipt has no process lease identity")

        return {
            "runtime_mode": "candidate-wheel",
            "action_server_mode": "source",
            "actions_core": "1.0.2",
            "actions_http_helper": "1.0.2",
            "server_integration": candidate_result["server_integration"],
            "rcc_version": runtime["rcc_version"],
            "artifact_digest": digest,
            "run_id": run_id,
            "status": "passed",
            "unauthenticated_http_status": unauthenticated.status_code,
            "authenticated_http_status": response.status_code,
            "verification_valid": receipt["verification"]["valid"],
            "lease_id_present": True,
            "provider": "rcc-cache-serve-loopback",
        }


def main() -> int:
    args = _parser().parse_args()
    if args.mode != "candidate-wheel":
        raise AssertionError("unreachable unsupported mode")
    try:
        result = _run()
    except Exception as exc:
        print(
            f"Dakota RCC acceptance failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
