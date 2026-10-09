"""Source Runtime acceptance for RCC's explicit local provider and trust carrier."""

from __future__ import annotations

import base64
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest
import requests


def _verify_runtime_wheel(
    repo_root: Path,
    runtime_origin: Path,
    package_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, str | int | bool]:
    """Bind the installed Runtime and its child server process to the wheel bytes."""
    wheel = Path(os.environ["ACTIONS_ACCEPTANCE_RUNTIME_WHEEL"]).resolve()
    report = Path(os.environ["ACTIONS_ACCEPTANCE_RUNTIME_INSTALL_REPORT"]).resolve()
    expected_digest = os.environ["ACTIONS_ACCEPTANCE_RUNTIME_WHEEL_SHA256"]
    wheel_digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert wheel_digest == expected_digest
    assert not os.environ.get("PYTHONPATH")
    assert Path(sys.prefix).resolve() != Path(sys.base_prefix).resolve()
    assert not Path.cwd().resolve().is_relative_to(repo_root)
    assert not runtime_origin.is_relative_to(repo_root)
    source_root = repo_root / "action_server" / "src"
    assert all(
        not Path(entry or Path.cwd()).resolve().is_relative_to(source_root)
        and Path(entry or Path.cwd()).resolve() != repo_root
        for entry in sys.path
    )

    distribution = importlib.metadata.distribution("actions-runtime")
    installed_files = {
        Path(distribution.locate_file(entry)).resolve(): entry
        for entry in distribution.files or ()
    }

    assert runtime_origin in installed_files
    assert distribution.version == "1.0.3"
    direct_url = json.loads(distribution.read_text("direct_url.json") or "{}")
    assert direct_url.get("dir_info", {}).get("editable") is not True
    assert Path(unquote(urlparse(direct_url["url"]).path)).resolve() == wheel
    assert direct_url["archive_info"]["hashes"]["sha256"] == wheel_digest

    for installed_path, entry in installed_files.items():
        if entry.hash is None:
            continue
        payload = installed_path.read_bytes()
        actual = (
            base64.urlsafe_b64encode(hashlib.new(entry.hash.mode, payload).digest())
            .decode("ascii")
            .rstrip("=")
        )
        assert actual == entry.hash.value, installed_path.name

    install_report = json.loads(report.read_text(encoding="utf-8"))
    runtime_installs = [
        item
        for item in install_report.get("install", [])
        if item.get("metadata", {}).get("name", "").lower().replace("_", "-")
        == "actions-runtime"
    ]
    assert len(runtime_installs) == 1
    install_source = runtime_installs[0]["download_info"]
    assert Path(unquote(urlparse(install_source["url"]).path)).resolve() == wheel
    assert install_source["archive_info"]["hashes"]["sha256"] == wheel_digest

    proof_path = package_dir / "runtime-child-import-proof.json"
    wrapper = package_dir / "action-server-runtime-proof"
    wrapper.write_text(
        "#!/usr/bin/env python3\n"  # replaced below with the selected interpreter
        + "import hashlib, importlib.metadata, json, os, sys\n"
        + "from pathlib import Path\n"
        + "import actions.server\n"
        + "dist = importlib.metadata.distribution('actions-runtime')\n"
        + "origin = Path(actions.server.__file__).resolve()\n"
        + "files = {Path(dist.locate_file(p)).resolve() for p in dist.files or ()}\n"
        + "assert origin in files\n"
        + "wheel = Path(os.environ['ACTIONS_ACCEPTANCE_RUNTIME_WHEEL']).resolve()\n"
        + "digest = hashlib.sha256(wheel.read_bytes()).hexdigest()\n"
        + "assert digest == os.environ['ACTIONS_ACCEPTANCE_RUNTIME_WHEEL_SHA256']\n"
        + "report = Path(os.environ['ACTIONS_ACCEPTANCE_RUNTIME_INSTALL_REPORT'])\n"
        + "Path(os.environ['ACTIONS_ACCEPTANCE_RUNTIME_CHILD_PROOF']).write_text(json.dumps({"
        + "'python': sys.executable, 'runtime_import_origin': str(origin), "
        + "'runtime_version': dist.version, 'wheel_sha256': digest, "
        + "'pip_report_sha256': hashlib.sha256(report.read_bytes()).hexdigest(), "
        + "'origin_in_RECORD': True}, sort_keys=True))\n"
        + "from actions.server.cli import main\n"
        + "raise SystemExit(main())\n",
        encoding="utf-8",
    )
    wrapper_text = wrapper.read_text(encoding="utf-8").replace(
        "#!/usr/bin/env python3", f"#!{sys.executable}"
    )
    wrapper.write_text(wrapper_text, encoding="utf-8")
    wrapper.chmod(0o700)
    monkeypatch.setenv("ACTIONS_ACCEPTANCE_RUNTIME_CHILD_PROOF", str(proof_path))
    return {
        "wheel_sha256": wheel_digest,
        "pip_report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "recorded_runtime_files": len(installed_files),
        "child_proof_ready": True,
    }


def _run_published_dependency_provider_dead_gate(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    trust_carrier: Path,
) -> dict[str, object]:
    """Reuse the Dakota provider-dead lifecycle with this installed Runtime."""
    wheelhouse = Path(os.environ["ACTIONS_ACCEPTANCE_CORE_HELPER_WHEELHOUSE"])
    install_report_path = Path(
        os.environ["ACTIONS_ACCEPTANCE_CORE_HELPER_INSTALL_REPORT"]
    )
    core_wheel = wheelhouse / "actions_core-1.0.2-py3-none-any.whl"
    helper_wheel = wheelhouse / "actions_http_helper-1.0.3-py3-none-any.whl"
    install_report = json.loads(install_report_path.read_text(encoding="utf-8"))
    expected = {
        "actions-core": ("1.0.2", core_wheel),
        "actions-http-helper": ("1.0.3", helper_wheel),
    }
    published: dict[str, dict[str, str]] = {}
    for item in install_report.get("install", []):
        name = item.get("metadata", {}).get("name", "").lower().replace("_", "-")
        if name not in expected:
            continue
        version, wheel = expected[name]
        assert item.get("metadata", {}).get("version") == version
        download = item["download_info"]
        assert urlparse(download["url"]).hostname == "files.pythonhosted.org"
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        assert download["archive_info"]["hashes"]["sha256"] == digest
        published[name] = {
            "version": version,
            "filename": wheel.name,
            "sha256": digest,
            "url": download["url"],
        }
    assert set(published) == set(expected)

    script_path = (
        repo_root / "action_server" / "scripts" / "verify_dakota_rcc_acceptance.py"
    )
    spec = importlib.util.spec_from_file_location("dakota_rcc_acceptance", script_path)
    assert spec is not None and spec.loader is not None
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    passthrough = {
        "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE",
        "ACTIONS_ACCEPTANCE_RUNTIME_WHEEL",
        "ACTIONS_ACCEPTANCE_RUNTIME_WHEEL_SHA256",
        "ACTIONS_ACCEPTANCE_RUNTIME_INSTALL_REPORT",
        "ACTIONS_ACCEPTANCE_RUNTIME_CHILD_PROOF",
    }
    monkeypatch.setattr(harness, "_ENV_ALLOWLIST", harness._ENV_ALLOWLIST | passthrough)
    monkeypatch.setattr(
        harness,
        "build_candidate_wheels",
        lambda *_args, **_kwargs: (core_wheel, helper_wheel),
    )
    monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TRUST_CARRIER", str(trust_carrier))
    receipt_path = tmp_path / "provider-dead-dakota-harness.json"
    prior_environment = os.environ.copy()
    try:
        evidence = harness._run(receipt_path)
    finally:
        os.environ.clear()
        os.environ.update(prior_environment)

    cells = evidence["cells"]
    required_cells = (
        "authenticated_action",
        "artifact_verification",
        "provider_backed_exec_fail_closed",
        "wrapper_exit",
        "process_cleanup",
        "offline_warm_action",
        "offline_warm_artifact_verification",
        "offline_warm_wrapper_exit",
        "provider_unavailable",
        "zero_requests_during_warm_runtime",
        "warm_process_cleanup",
    )
    assert all(cells[name] == "PASS" for name in required_cells), cells
    offline = evidence["offline_warm"]
    assert offline["warm_runtime_provider_requests"] == 0
    assert offline["warm_runtime_request_events"] == []
    negative = offline["provider_backed_exec"]
    assert negative["provenance_503_observed"] is True
    assert negative["child_side_effect_observed"] is False
    assert negative["successful_child_receipt"] is False
    assert evidence["run_id"] != offline["run_id"]
    assert evidence["rcc_receipt"]["leaseId"] != offline["rcc_receipt"]["leaseId"]
    assert evidence["trust_carrier_mode"] == "separate-filesystem"

    wheel_receipt_path = Path(os.environ["ACTIONS_ACCEPTANCE_PROVIDER_DEAD_RECEIPT"])
    if wheel_receipt_path.exists():
        raise FileExistsError(
            "refusing to overwrite the installed-wheel provider receipt"
        )
    wheel_evidence = {
        "schema_version": 1,
        "acceptance_status": "PASS",
        "action_server_mode": "installed-runtime-wheel",
        "runtime_wheel_sha256": os.environ["ACTIONS_ACCEPTANCE_RUNTIME_WHEEL_SHA256"],
        "runtime_wheel_source_sha": os.environ[
            "ACTIONS_ACCEPTANCE_RUNTIME_WHEEL_SOURCE_SHA"
        ],
        "runtime_harness_source_sha": evidence["source_sha"],
        "published_core_helper_wheels": published,
        "published_dependency_install_report_sha256": hashlib.sha256(
            install_report_path.read_bytes()
        ).hexdigest(),
        "trust_carrier_mode": evidence["trust_carrier_mode"],
        "trust_carrier_identity": evidence["trust_carrier_identity"],
        "artifact_digest": evidence["artifact_digest"],
        "initial_run_id": evidence["run_id"],
        "warm_run_id": offline["run_id"],
        "initial_rcc_receipt": evidence["rcc_receipt"],
        "warm_rcc_receipt": offline["rcc_receipt"],
        "warm_runtime_provider_requests": offline["warm_runtime_provider_requests"],
        "warm_runtime_request_events": offline["warm_runtime_request_events"],
        "provider_backed_exec_negative": negative,
        "cells": cells,
    }
    wheel_receipt_path.parent.mkdir(parents=True, exist_ok=True)
    wheel_receipt_path.write_text(
        json.dumps(wheel_evidence, indent=2) + "\n", encoding="utf-8"
    )
    return wheel_evidence


@pytest.mark.real_rcc
def test_local_provider_and_separate_trust_carrier_survive_runtime_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run a spec-v2 Action before and after a local-provider Runtime restart."""
    if os.environ.get("ACTIONS_REAL_RCC_ARTIFACT_TEST") != "1":
        pytest.skip("set ACTIONS_REAL_RCC_ARTIFACT_TEST=1 for real RCC acceptance")
    rcc = Path(os.environ["ACTIONS_RUNTIME_RCC_BINARY"]).resolve()
    assert rcc.is_file() and os.access(rcc, os.X_OK)

    import actions.server as runtime_package
    from actions.server._models import ActionPackage, Run, RunStatus, load_db
    from actions.server._rcc_runtime_adapter import read_receipt
    from actions.server._selftest import ActionServerProcess

    repo_root = Path(__file__).resolve().parents[3]
    runtime_mode = os.environ.get("ACTIONS_ACCEPTANCE_RUNTIME_MODE", "source")
    source_package = repo_root / "action_server" / "src" / "actions" / "server"
    runtime_origin = Path(runtime_package.__file__).resolve()
    wheel_proof: dict[str, str | int | bool] | None = None
    cpu_affinity = (
        sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else []
    )
    if runtime_mode == "source":
        assert runtime_origin.is_relative_to(source_package)
    elif runtime_mode == "wheel":
        assert sys.platform == "linux"
        assert len(cpu_affinity) == 2, "run RCC wheel acceptance with two-CPU affinity"
        assert not runtime_origin.is_relative_to(repo_root)
        original_module = runtime_origin.read_bytes()
        corrupted_module = bytes([original_module[0] ^ 1]) + original_module[1:]
        runtime_origin.write_bytes(corrupted_module)
        try:
            with pytest.raises(AssertionError):
                _verify_runtime_wheel(repo_root, runtime_origin, tmp_path, monkeypatch)
        finally:
            runtime_origin.write_bytes(original_module)
        wheel_proof = _verify_runtime_wheel(
            repo_root, runtime_origin, tmp_path, monkeypatch
        )
        monkeypatch.setenv(
            "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE",
            str(tmp_path / "action-server-runtime-proof"),
        )
    else:
        pytest.fail("ACTIONS_ACCEPTANCE_RUNTIME_MODE must be source or wheel")

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
    if runtime_mode == "wheel":
        child_proof = json.loads(
            Path(os.environ["ACTIONS_ACCEPTANCE_RUNTIME_CHILD_PROOF"]).read_text(
                encoding="utf-8"
            )
        )
        assert child_proof["runtime_import_origin"] == str(runtime_origin)
        assert Path(child_proof["python"]).resolve() == Path(sys.executable).resolve()
        assert child_proof["runtime_version"] == "1.0.3"
        assert child_proof["origin_in_RECORD"] is True

    receipt_path = os.environ.get("ACTIONS_ACCEPTANCE_RECEIPT")
    if runtime_mode == "wheel" and not receipt_path:
        pytest.fail("wheel acceptance requires a durable acceptance receipt path")
    if receipt_path:
        provider_dead_receipt = None
        if runtime_mode == "wheel":
            provider_dead_receipt = _run_published_dependency_provider_dead_gate(
                repo_root, tmp_path, monkeypatch, trust_carrier
            )
        path = Path(receipt_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "source_sha": subprocess.run(
                ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
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
            "runtime_mode": runtime_mode,
            "runtime_import_origin": str(runtime_origin),
            "runtime_wheel_sha256": os.environ.get(
                "ACTIONS_ACCEPTANCE_RUNTIME_WHEEL_SHA256"
            ),
            "runtime_wheel_proof": wheel_proof,
            "runtime_child_import_proof": json.loads(
                Path(os.environ["ACTIONS_ACCEPTANCE_RUNTIME_CHILD_PROOF"]).read_text(
                    encoding="utf-8"
                )
            )
            if runtime_mode == "wheel"
            else None,
            "provider_dead_installed_runtime_wheel": provider_dead_receipt,
            "test_cpu_affinity": cpu_affinity or None,
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
                "published_core_helper_action": "PASS",
                "source_runtime": "PASS" if runtime_mode == "source" else "NOTRUN",
                "installed_runtime_wheel": "PASS"
                if runtime_mode == "wheel"
                else "NOTRUN",
                "frozen_runtime_exact_source": "NOTRUN",
            },
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
