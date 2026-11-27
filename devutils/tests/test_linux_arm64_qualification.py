"""The qualification receipt must bind both native wheel slots to real Actions."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
VERSION = "18.19.12"
DIGEST = "a" * 64
SOURCE = "b" * 40


@pytest.fixture
def qualifier():
    spec = importlib.util.spec_from_file_location(
        "arm64_qualification",
        ROOT / "action_server/scripts/verify_linux_arm64_wheel.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def measured_wheels(tmp_path):
    wheels = tmp_path / "wheels"
    evidence = tmp_path / "evidence"
    wheels.mkdir()
    measured = {}
    for python in ("312", "313"):
        wheel = wheels / (
            f"actions_runtime-1.1.1-cp{python}-cp{python}-manylinux2014_aarch64.whl"
        )
        wheel.write_bytes(b"synthetic wheel bytes " + python.encode())
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        measured[wheel.name] = digest
        root = evidence / wheel.stem
        (root / "raw").mkdir(parents=True)
        (root / "wheel.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "qualification_sha": SOURCE,
                    "wheel": wheel.name,
                    "sha256": digest,
                    "machine": "aarch64",
                    "rcc_environment_version": VERSION,
                    "rcc_environment_prefix": "/tmp/private-rcc/holotree/synthetic",
                }
            )
        )
        (root / "action-receipt.json").write_text(
            json.dumps(
                {
                    "official_contract": True,
                    "installed_wheel_sha256": digest,
                    "rcc_sha256": DIGEST,
                    "rcc_version": "v" + VERSION,
                    "import_exit": 0,
                    "synthetic_result": "arm64:synthetic",
                }
            )
        )
        (root / "raw/action-status.json").write_text(
            json.dumps({"status": 200, "run_id": "synthetic"})
        )
        (root / "raw/action-response.json").write_text(json.dumps("arm64:synthetic"))
        for name in (
            "install.log",
            "installed-environment.txt",
            "floor.log",
            "smoke.log",
            "raw/import.log",
            "raw/server.log",
        ):
            (root / name).write_bytes(b"original synthetic diagnostic\r\n")
    return wheels, evidence, measured


def test_both_wheel_receipts_bind_source_binary_and_action(qualifier, measured_wheels):
    wheels, evidence, measured = measured_wheels
    assert (
        qualifier.verify_evidence(wheels, evidence, VERSION, DIGEST, SOURCE) == measured
    )


@pytest.mark.parametrize(
    "filename,key,value",
    [
        ("wheel.json", "qualification_sha", "c" * 40),
        ("wheel.json", "machine", "x86_64"),
        ("wheel.json", "rcc_environment_version", "18.19.8"),
        ("action-receipt.json", "official_contract", False),
        ("action-receipt.json", "installed_wheel_sha256", "c" * 64),
        ("action-receipt.json", "rcc_sha256", "c" * 64),
        ("action-receipt.json", "import_exit", 1),
        ("raw/action-status.json", "status", 500),
    ],
)
def test_mismatched_or_failed_receipt_is_rejected(
    qualifier, measured_wheels, filename, key, value
):
    wheels, evidence, _ = measured_wheels
    root = evidence / next(wheels.glob("*.whl")).stem
    path = root / filename
    payload = json.loads(path.read_text())
    payload[key] = value
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="receipt differs"):
        qualifier.verify_evidence(wheels, evidence, VERSION, DIGEST, SOURCE)


def test_missing_original_log_is_not_acceptance(qualifier, measured_wheels):
    wheels, evidence, _ = measured_wheels
    (evidence / next(wheels.glob("*.whl")).stem / "raw/server.log").unlink()
    with pytest.raises(ValueError, match="logs missing"):
        qualifier.verify_evidence(wheels, evidence, VERSION, DIGEST, SOURCE)


def test_missing_wheel_slot_is_not_acceptance(qualifier, measured_wheels):
    wheels, evidence, _ = measured_wheels
    next(wheels.glob("*.whl")).unlink()
    with pytest.raises(ValueError, match="two ARM64"):
        qualifier.verify_evidence(wheels, evidence, VERSION, DIGEST, SOURCE)


def test_x64_wheel_is_not_an_arm64_slot(qualifier, measured_wheels):
    wheels, evidence, _ = measured_wheels
    wheel = next(wheels.glob("*.whl"))
    wheel.rename(wheel.with_name(wheel.name.replace("aarch64", "x86_64")))
    with pytest.raises(ValueError, match="matrix mismatch"):
        qualifier.verify_evidence(wheels, evidence, VERSION, DIGEST, SOURCE)


def test_parent_environment_cannot_spoof_an_rcc_created_context(
    qualifier, tmp_path, monkeypatch
):
    monkeypatch.setenv("RCC_VERSION", "fake-outer-version")
    monkeypatch.setenv("VIRTUAL_ENV", "/shared/unrelated-venv")
    environment = qualifier.isolated_rcc_environment(tmp_path / "private", SOURCE)
    assert "RCC_VERSION" not in environment
    assert "VIRTUAL_ENV" not in environment
    assert environment["ROBOCORP_HOME"] == str(tmp_path / "private")
    assert environment["ACTIONS_CANDIDATE_SOURCE_SHA"] == SOURCE


def test_only_declared_native_python_abis_have_pinned_rcc_recipes(qualifier):
    assert qualifier.PYTHON_PINS == {
        "cp312": "python=3.12.15",
        "cp313": "python=3.13.9=*_cp313",
    }


def test_version_marker_does_not_allow_install_outside_private_rcc_prefix(
    qualifier, tmp_path, monkeypatch, capsys
):
    wheel = tmp_path / "actions_runtime-1.1.1-cp312-cp312-linux_aarch64.whl"
    wheel.write_bytes(b"not installed")
    monkeypatch.setattr(qualifier.platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(qualifier.sys, "platform", "linux")
    monkeypatch.setenv("RCC_VERSION", VERSION)
    monkeypatch.setenv("ROBOCORP_HOME", str(tmp_path / "private-rcc"))
    monkeypatch.setattr(
        qualifier.sys, "argv", ["smoke", "--install-wheel", str(wheel), str(tmp_path)]
    )
    with pytest.raises(SystemExit) as error:
        qualifier.main()
    assert error.value.code == 2
    assert "real private RCC environment" in capsys.readouterr().err
    assert not (tmp_path / "arm64-wheel-evidence").exists()
