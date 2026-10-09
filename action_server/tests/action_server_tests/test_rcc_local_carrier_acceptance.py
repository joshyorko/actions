"""Source Runtime acceptance for RCC's explicit local provider and trust carrier."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import requests


@pytest.mark.real_rcc
def test_local_provider_and_separate_trust_carrier_survive_runtime_restart(
    tmp_path: Path,
) -> None:
    """Run a spec-v2 Action before and after a local-provider Runtime restart."""
    if os.environ.get("ACTIONS_REAL_RCC_ARTIFACT_TEST") != "1":
        pytest.skip("set ACTIONS_REAL_RCC_ARTIFACT_TEST=1 for real RCC acceptance")
    rcc = Path(os.environ["ACTIONS_RUNTIME_RCC_BINARY"]).resolve()
    assert rcc.is_file() and os.access(rcc, os.X_OK)

    from actions.server._models import ActionPackage, Run, RunStatus, load_db
    from actions.server._rcc_runtime_adapter import read_receipt
    from actions.server._selftest import ActionServerProcess

    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "package.yaml").write_text(
        """version: 0.1
spec-version: v2
name: rcc-local-acceptance
dependencies:
  conda-forge:
    - python=3.12.15
  pypi:
    - actions-core=1.0.2
    - actions-http-helper=1.0.3
""",
        encoding="utf-8",
    )
    (package_dir / "action.py").write_text(
        "import json\n"
        "from importlib.metadata import version\n"
        "from actions import action\n"
        "from actions.server_integration import ManagedParameters\n"
        "\n"
        "@action\n"
        "def answer() -> str:\n"
        "    return json.dumps({\n"
        "        'result': 'separate-local-trust-carrier',\n"
        "        'actions_core': version('actions-core'),\n"
        "        'actions_http_helper': version('actions-http-helper'),\n"
        "        'server_integration': ManagedParameters.__name__,\n"
        "        'trust_carrier_exposed_to_action': 'ACTIONS_RUNTIME_RCC_TRUST_CARRIER' in __import__('os').environ,\n"
        "    }, sort_keys=True)\n",
        encoding="utf-8",
    )

    datadir = tmp_path / "datadir"
    rcc_home = tmp_path / "rcc-home"
    trust_carrier = tmp_path / "service-owned-trust-carrier"
    trust_carrier.mkdir(mode=0o700)
    api_key = "acceptance-key"
    runtime_env = os.environ.copy()
    runtime_env.update(
        {
            "ACTIONS_RUNTIME_RCC_BINARY": str(rcc),
            "ACTIONS_REAL_RCC_ARTIFACT_TEST": "1",
            "ACTIONS_RUNTIME_RCC_PROVIDER": "local",
            "ACTIONS_RUNTIME_RCC_TRUST_CARRIER": str(trust_carrier),
            "ROBOCORP_HOME": str(rcc_home),
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
        }
    )

    expected_result = {
        "result": "separate-local-trust-carrier",
        "actions_core": "1.0.2",
        "actions_http_helper": "1.0.3",
        "server_integration": "ManagedParameters",
        "trust_carrier_exposed_to_action": False,
    }
    receipts: list[dict[str, object]] = []
    artifact_digests: list[str] = []
    trust_carrier_identities: list[str] = []
    run_ids: list[str] = []
    process_reaped: list[bool] = []
    for generation in range(2):
        prior_receipt_files = set((datadir / "rcc-receipts").glob("*.json"))
        server = ActionServerProcess(datadir)
        server_process = None
        try:
            server.start(
                timeout=900,
                db_file="server.db",
                actions_sync=True,
                cwd=package_dir,
                min_processes=0,
                max_processes=1,
                reuse_processes=True,
                additional_args=[
                    "--address=127.0.0.1",
                    "--api-key",
                    api_key,
                ],
                env=runtime_env,
                port=0,
                verbose="",
            )
            server_process = server.process
            action_url = (
                f"http://{server.host}:{server.port}"
                "/api/actions/rcc-local-acceptance/answer/run"
            )
            unauthenticated = requests.post(action_url, json={}, timeout=20)
            assert unauthenticated.status_code in (401, 403)
            response = requests.post(
                action_url,
                json={},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=900,
            )
            response.raise_for_status()
            assert str(trust_carrier) not in response.text
            assert json.loads(response.json()) == expected_result
            run_id = response.headers["x-action-server-run-id"]
            run_ids.append(run_id)
            with load_db(datadir / "server.db") as db:
                with db.connect():
                    run = next(item for item in db.all(Run) if item.id == run_id)
                    package = db.all(ActionPackage)[0]
                    runtime = json.loads(package.env_json)["runtime"]
            assert run.status == RunStatus.PASSED
            assert runtime["provider_reference"] == "local"
            assert runtime["trust_policy"] == "permissive-local"
            assert runtime["trust_carrier_identity"].startswith("sha256:")
            assert str(trust_carrier) not in package.env_json
            artifact_digests.append(runtime["artifact_digest"])
            trust_carrier_identities.append(runtime["trust_carrier_identity"])
        finally:
            if server_process is None:
                server_process = getattr(server, "_process", None)
            server.stop()
            if server_process is not None:
                process_reaped.append(
                    server_process.returncode is not None
                    and not server_process.is_alive()
                )
            assert str(trust_carrier) not in server.get_stdout() + server.get_stderr()

        receipt_files = sorted(
            set((datadir / "rcc-receipts").glob("*.json")) - prior_receipt_files
        )
        assert receipt_files, f"generation {generation} produced no RCC receipt"
        receipt = read_receipt(receipt_files[-1], artifact_digests[-1])
        receipts.append(receipt)
        assert receipt.get("leaseId")
        assert receipt.get("verification", {}).get("valid") is True
        assert receipt.get("status") == "completed"
        assert receipt.get("exitCode") == 0
        assert str(trust_carrier) not in json.dumps(receipt)

    assert artifact_digests[0].startswith("sha256:")
    assert artifact_digests[1] == artifact_digests[0]
    assert trust_carrier_identities[0] == trust_carrier_identities[1]
    assert run_ids[0] != run_ids[1]
    assert process_reaped == [True, True]
    assert receipts[0]["leaseId"] != receipts[1]["leaseId"]

    receipt_path = os.environ.get("ACTIONS_ACCEPTANCE_RECEIPT")
    if receipt_path:
        path = Path(receipt_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "source_sha": subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "rcc_version": subprocess.run(
                [str(rcc), "--version"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "runtime_mode": "source",
            "provider_reference": "local",
            "trust_policy": "permissive-local",
            "trust_carrier_identities": trust_carrier_identities,
            "artifact_digests": artifact_digests,
            "run_ids": run_ids,
            "runtime_process_reaped": process_reaped,
            "rcc_receipts": receipts,
            "cells": {
                "spec_v2_action": "PASS",
                "local_provider_restart_same_artifact": "PASS",
                "separate_trust_carrier": "PASS",
                "runtime_process_reaping": "PASS",
                "core_helper_installed_wheel": "NOTRUN",
                "frozen_runtime_exact_source": "NOTRUN",
            },
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
