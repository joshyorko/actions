"""One reviewed, nonpublishing Linux consumer of retained Runtime release bytes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path

BASE = Path("/workspace/engineering/pr221-current618-linux-consumer-preflight")
CHECKOUT = Path("/workspace/engineering/pr282")
GUARD_CHECKOUT = Path("/workspace/engineering/pr311")
CHECKOUT_ROOTS = tuple(
    Path(value)
    for value in [
        "/workspace/actions",
        "/workspace/engineering",
        "/workspace/engineering/campaign-checkpoint",
        "/workspace/engineering/pr282",
        "/workspace/engineering/pr290",
        "/workspace/engineering/pr299",
        "/workspace/engineering/pr302",
        "/workspace/engineering/pr305",
        "/workspace/engineering/pr306",
        "/workspace/engineering/pr307",
        "/workspace/engineering/pr308",
        "/workspace/engineering/pr309",
        "/workspace/engineering/pr310",
        "/workspace/engineering/pr311",
        "/workspace/engineering/rcc-public",
    ]
)
ATTEMPT = Path(
    "/workspace/engineering/pr221-current618-linux-consumer-preflight/installed-linux-current618-90a785d8-3"
)
WHEEL = Path(
    "/workspace/engineering/pr221-current618-linux-consumer-preflight/linux-platform-input-v5/actions_runtime-1.0.3-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
)
WHEEL_SHA = "90a785d81ca1158ab58a3feb0eabc1b3b3dabb6e395f2f503337c2cf53e986d6"
WHEEL_PYTHON_COUNT = 202
ARCHIVE = Path(
    "/workspace/engineering/pr221-current618-wheel-integrity-owned/original-11697353355.zip"
)
PRODUCER = {
    "run_id": 38126987514,
    "attempt": 1,
    "artifact_id": 11697353355,
    "artifact_zip_bytes": 28299039,
    "artifact_zip_sha256": "fc4018e6e7ed4a0e47c4f5888d36d55655216ca22ebd965f29ce9f1130938f8c",
    "api_head": "6181b044c75de35386f1ae30e71725398b6a7feb",
    "checkout": "e7666eacf2687f65050b97a88e791f8d0ce4cd20",
    "tree": "99ac5309add45af65049546dd3a99f357884cf3b",
    "parents": [
        "a70993fafc99a9f94041485542d5a720797ca394",
        "6181b044c75de35386f1ae30e71725398b6a7feb",
    ],
    "source_candidate": "6181b044c75de35386f1ae30e71725398b6a7feb",
    "source_tree": "99ac5309add45af65049546dd3a99f357884cf3b",
    "event": "pull_request",
    "publication": False,
    "actual_integration_sha": "6181b044c75de35386f1ae30e71725398b6a7feb",
    "actual_integration_tree": "99ac5309add45af65049546dd3a99f357884cf3b",
    "build_is_actual_integration_job": False,
    "scope": "Original currentLinux pair only; selectedcp312consumer; fullseven/mac/windows/aggregate/tag/publication HOLD",
}
SOURCES = {
    "floor": (
        Path(
            "/workspace/engineering/pr282/action_server/scripts/verify_published_runtime_floor.py"
        ),
        "f1ad142a6cd83ca1a71ed0a6183d558a6d72f00f073b492ce0d18e563a067193",
    ),
    "publisher": (
        Path(
            "/workspace/engineering/pr282/action_server/scripts/publish_verified_runtime.py"
        ),
        "236ed21dcb50b3c3934f5e15b29e61d6a7b712ed65e7dcf7cd72785d4f8fa26c",
    ),
    "guard": (
        Path(
            "/workspace/engineering/pr311/action_server/tests/contract_tests/test_active_contracts.py"
        ),
        "b76ec605e343e8bec7dea6e230dad3f516eabc4fd90a2769638b0d9111a6ade0",
    ),
    "process": (
        Path(
            "/workspace/engineering/pr282/action_server/src/actions/server/_common/process.py"
        ),
        "f432e65a488bf06862e548dc45342d3c1fb5ea7fcc26f6371d98aae124ffc082",
    ),
    "rcc": (
        Path("/workspace/actions-cloud/bin/rcc"),
        "7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428",
    ),
    "artifact_review": (
        Path(
            "/workspace/engineering/pr221-current618-wheel-integrity-owned/OWNERFINAL-current618-partial-distribution-integrity-v2.json"
        ),
        "9b406fdf505871e6790d7a4233d0b8c075ae6f170f2c5b7a954bbca0f0d46236",
    ),
    "inspection": (
        Path(
            "/workspace/engineering/pr221-current618-wheel-integrity-owned/safe-data-only-integrity-inspection.json"
        ),
        "ec30816fa8826fb6f93ee088cea3e290a146d7d367a4b74205be4ba441f367a8",
    ),
    "input_manifest": (
        Path(
            "/workspace/engineering/pr221-current618-linux-consumer-preflight/input-and-source-admission-v5.json"
        ),
        "596942a7c85fe6f742777454d6d1a76c1bc3e8c29ed88f693eea28af856d7c34",
    ),
    "input_gate": (
        Path(
            "/workspace/engineering/pr221-current618-linux-consumer-preflight/current-input-admission-v4.py"
        ),
        "1edf96b6b801de5e7b8c1c7c284a636cec44bc06fcb45adb6e1781e519b3a8f6",
    ),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_source_bytes(bindings=SOURCES) -> None:
    for name, (path, expected) in bindings.items():
        assert digest(path) == expected, f"{name} source bytes changed: {path}"


def load(name: str):
    path, expected = SOURCES[name]
    assert digest(path) == expected, f"{name} source bytes changed"
    spec = importlib.util.spec_from_file_location("retained_runtime_" + name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def admit_current_inputs() -> dict:
    assert_source_bytes()
    manifest = json.loads(SOURCES["input_manifest"][0].read_text())
    return load("input_gate").admit(ARCHIVE, WHEEL, manifest, CHECKOUT)


def bind_inventory(wheel: Path, inventory: dict, prefix: Path, guard) -> list:
    assert inventory["prefix"] == str(prefix.resolve())
    assert (
        inventory["prefix"] != inventory["base_prefix"]
    ), "not a fresh virtual environment"
    assert inventory["wheel_sha256"] == digest(wheel), "selected wheel digest mismatch"
    assert inventory["runtime_version"] == "1.0.3"
    assert set(inventory["modules"]) == {
        "actions",
        "actions.server",
        "actions.mcp",
        "actions_http",
    }
    for path in inventory["modules"].values():
        assert (
            Path(path).resolve().is_relative_to(prefix.resolve())
        ), "module origin outside clean environment"
    floor = load("floor")
    for checkout in CHECKOUT_ROOTS:
        floor.assert_no_checkout_imports(
            checkout, inventory["sys_path"], inventory["modules"]
        )
    members = {name: Path(value) for name, value in inventory["members"].items()}
    bound = guard._assert_installed_runtime_wheel_has_no_private_core_imports(
        wheel, members, prefix=prefix, checkout=CHECKOUT
    )
    for checkout in CHECKOUT_ROOTS:
        for _, path, _ in bound:
            assert not path.is_relative_to(
                checkout.resolve()
            ), "checkout member admitted"
    return [
        {"member": name, "path": str(path), "sha256": sha} for name, path, sha in bound
    ]


INVENTORY_CODE = r"""
import hashlib, json, pathlib, sys
from importlib.metadata import distribution
import actions, actions.server, actions.mcp, actions_http
runtime = distribution('actions-runtime')
assert runtime.files is not None
members = {str(member): str(runtime.locate_file(member).resolve())
           for member in runtime.files if str(member).endswith('.py')}
print(json.dumps({'prefix': sys.prefix, 'base_prefix': sys.base_prefix,
                  'runtime_version': runtime.version, 'members': members,
                  'sys_path': [str(pathlib.Path.cwd()) if not value else value for value in sys.path],
                  'modules': {name: module.__file__ for name, module in {
                      'actions': actions, 'actions.server': actions.server,
                      'actions.mcp': actions.mcp, 'actions_http': actions_http}.items()},
                  'wheel_sha256': hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest()}, sort_keys=True))
"""


def worker(temporary: Path) -> None:
    assert_source_bytes()
    input_admission = admit_current_inputs()
    floor, guard = load("floor"), load("guard")
    environment = floor.isolated_environment()
    python = temporary / "venv/bin/python"
    report = ATTEMPT / "pip-install-report.json"
    assert not python.exists()
    subprocess.run(
        [sys.executable, "-m", "venv", str(temporary / "venv")],
        check=True,
        cwd=temporary,
        env=environment,
    )
    command = floor.install_command(python, WHEEL, report)
    (ATTEMPT / "install-argv.json").write_text(json.dumps(command, indent=2) + "\n")
    subprocess.run(command, check=True, cwd=temporary, env=environment)
    floor.verify_installed(python, temporary, report)
    result = subprocess.run(
        [str(python), "-c", INVENTORY_CODE, str(WHEEL)],
        check=True,
        cwd=temporary,
        env=environment,
        capture_output=True,
        text=True,
    )
    inventory = json.loads(result.stdout)
    (ATTEMPT / "installed-inventory-raw.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    )
    members = bind_inventory(WHEEL, inventory, temporary / "venv", guard)
    with zipfile.ZipFile(WHEEL) as archive:
        expected_count = sum(name.endswith(".py") for name in archive.namelist())
    assert expected_count == WHEEL_PYTHON_COUNT and len(members) == expected_count
    public = floor.verify_public_package_report(report)
    version = subprocess.run(
        [str(python), "-m", "actions.server", "version"],
        check=True,
        cwd=temporary,
        env=environment,
        capture_output=True,
        text=True,
    )
    (ATTEMPT / "cli-version.stdout.log").write_text(version.stdout)
    (ATTEMPT / "cli-version.stderr.log").write_text(version.stderr)
    assert (
        version.stdout.strip() == "1.0.3"
    ), f"unexpected CLI version: {version.stdout!r}"
    proof = {
        "status": "passed",
        "case_count": 1,
        "skips": 0,
        "producer": PRODUCER,
        "input_admission": input_admission,
        "runtime_wheel": {
            "path": str(WHEEL),
            "sha256": WHEEL_SHA,
            "python_member_count": expected_count,
        },
        "public_dependencies": public,
        "members": members,
        "inventory_sha256": digest(ATTEMPT / "installed-inventory-raw.json"),
        "pip_report_sha256": digest(report),
        "cli_version": version.stdout.strip(),
        "limits": [
            "Linux cp312 only",
            "original e766 PR producer; tree equals actual618; selected215 tracked payloads only",
            "two Linux wheels available; full seven-artifact/tag/publication gate HOLD",
            "generated OAuth required inputs measured EMPTY; authority/content HOLD even if imports pass",
            "no tag provenance, upload, publication or Runtime service/browser proof",
            "Core1.0.2 public floor; historical Core1.0.3/193-member proof remains separate",
        ],
    }
    (ATTEMPT / "consumer-proof.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n"
    )


def cleanup_is_complete(result: dict) -> bool:
    return all(
        result.get(name) is True
        for name in (
            "wrapper_reaped",
            "descendant_snapshot_complete",
            "descendant_reap_complete",
            "temporary_removed",
        )
    ) and all(
        result.get(name) == []
        for name in (
            "cleanup_errors",
            "active_readers",
            "observed_live_children",
            "observed_zombie_children",
        )
    )


def finish(primary_error: Exception | None, result: dict) -> None:
    if primary_error is not None:
        if not cleanup_is_complete(result):
            primary_error.add_note(
                "Cleanup also failed; see execution-cleanup-receipt.json."
            )
        raise primary_error.with_traceback(primary_error.__traceback__)
    if not cleanup_is_complete(result):
        raise RuntimeError(
            "Owned cleanup incomplete; see execution-cleanup-receipt.json."
        )


def supervisor() -> None:
    started = time.monotonic()
    import psutil

    assert sys.platform == "linux" and sys.version_info[:2] == (3, 12)
    assert_source_bytes()
    assert digest(WHEEL) == WHEEL_SHA
    archive = ARCHIVE
    assert archive.stat().st_size == PRODUCER["artifact_zip_bytes"]
    assert digest(archive) == PRODUCER["artifact_zip_sha256"]
    input_admission = admit_current_inputs()
    assert load("floor").select_runtime_wheel(WHEEL.parent) == WHEEL
    from actions.server._common import process as process_helpers

    assert Path(process_helpers.__file__).resolve() == SOURCES["process"][0].resolve()
    assert not ATTEMPT.exists(), "never overwrite an earlier acceptance attempt"
    ATTEMPT.mkdir(mode=0o700)
    (ATTEMPT / "input-admission.json").write_text(
        json.dumps(input_admission, indent=2, sort_keys=True) + "\n"
    )
    temporary = Path(tempfile.mkdtemp(prefix="rt103-current618-", dir="/tmp"))
    temporary.chmod(0o700)
    environment = load("floor").isolated_environment()
    for name in list(environment):
        if (
            any(part in name.upper() for part in ("TOKEN", "PASSWORD", "SECRET"))
            or name in ("VIRTUAL_ENV", "CONDA_PREFIX", "POETRY_ACTIVE", "PYPI")
            or name.startswith(("PIP_", "TWINE_"))
        ):
            environment.pop(name, None)
    environment.update(
        {
            "OMP_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2",
            "MKL_NUM_THREADS": "2",
            "PYTHONUNBUFFERED": "1",
        }
    )
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        str(temporary),
    ]
    identity = {
        "producer": PRODUCER,
        "runner_sha256": digest(Path(__file__)),
        "argv": command,
        "supervisor_python": sys.executable,
        "temporary_root": str(temporary),
        "source_bindings": {
            name: {"path": str(path), "sha256": sha}
            for name, (path, sha) in SOURCES.items()
        },
        "overall_process_deadline_seconds": 600,
        "worker_deadline_seconds": 595,
        "cleanup_seconds": 5,
    }
    (ATTEMPT / "attempt-identity.json").write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n"
    )
    captured, identities, errors = [], set(), []
    snapshot_complete = True
    process = None
    primary_error = None
    result = {
        "status": "failed",
        "cleanup_errors": [],
        "active_readers": [],
        "limits": ["point-in-time captured descendants; no universal adoption proof"],
    }
    try:
        with (
            (ATTEMPT / "worker.stdout.log").open("w") as stdout,
            (ATTEMPT / "worker.stderr.log").open("w") as stderr,
        ):
            process = subprocess.Popen(
                command,
                cwd=temporary,
                env=environment,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            identity["worker"] = {
                "pid": process.pid,
                "create_time": psutil.Process(process.pid).create_time(),
            }
            (ATTEMPT / "attempt-identity.json").write_text(
                json.dumps(identity, indent=2, sort_keys=True) + "\n"
            )
            deadline = started + 595
            while process.poll() is None:
                try:
                    for child in process_helpers.snapshot_process_descendants(
                        process.pid
                    ):
                        key = (child.pid, child.create_time())
                        if key not in identities:
                            identities.add(key)
                            captured.append(child)
                except psutil.NoSuchProcess:
                    if process.poll() is None:
                        snapshot_complete = False
                except Exception as error:
                    errors.append(str(error))
                    snapshot_complete = False
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired(command, 595)
                time.sleep(0.05)
            assert (
                process.returncode == 0
            ), f"consumer worker exited {process.returncode}; see retained primary stdout/stderr"
            assert (
                json.loads((ATTEMPT / "consumer-proof.json").read_text())["status"]
                == "passed"
            )
            result["status"] = "passed"
    except Exception as error:
        primary_error = error
        (ATTEMPT / "supervisor-error.log").write_text(traceback.format_exc())
    finally:
        if process is not None:
            try:
                cleanup = process_helpers.force_kill_process_tree_until(
                    process,
                    captured,
                    min(started + 600, time.monotonic() + 5),
                    snapshot_complete_before_call=snapshot_complete,
                )
                result.update(
                    {
                        "wrapper_reaped": cleanup.wrapper_reaped,
                        "descendant_snapshot_complete": cleanup.descendant_snapshot_complete,
                        "descendant_reap_complete": cleanup.descendant_reap_complete,
                        "observed_live_children": list(cleanup.live_descendant_pids),
                        "observed_zombie_children": list(
                            cleanup.zombie_descendant_pids
                        ),
                        "cleanup_errors": errors + list(cleanup.errors),
                        "observed_descendants": [
                            {"pid": pid, "create_time": created}
                            for pid, created in sorted(identities)
                        ],
                    }
                )
            except Exception as error:
                result["cleanup_errors"].append(
                    f"owned process cleanup raised: {error}"
                )
                (ATTEMPT / "cleanup-error.log").write_text(traceback.format_exc())
        else:
            result["cleanup_errors"].append("worker did not start")
        if result.get("wrapper_reaped") and not result.get("observed_live_children"):
            try:
                shutil.rmtree(temporary)
            except Exception as error:
                result["cleanup_errors"].append(f"owned temporary removal: {error}")
        result["temporary_removed"] = not temporary.exists()
        result["elapsed_seconds"] = time.monotonic() - started
        if not cleanup_is_complete(result):
            result["status"] = "failed"
        (ATTEMPT / "execution-cleanup-receipt.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        )
        for filename, stream in [
            ("worker.stdout.log", sys.stdout),
            ("worker.stderr.log", sys.stderr),
        ]:
            path = ATTEMPT / filename
            if path.exists():
                stream.write(path.read_text())
                stream.flush()
    finish(primary_error, result)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker(Path(sys.argv[2]))
    else:
        assert len(sys.argv) == 1
        supervisor()
