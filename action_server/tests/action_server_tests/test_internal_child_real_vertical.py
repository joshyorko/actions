"""Opt-in installed Core/RCC Action-to-Robot vertical through MCP Task admission.

This test consumes exact installed Runtime/Core/Work Items host wheels and two
externally prepared, task-owned RCC caches. It never publishes an RCC
environment itself. MCP protocol handling runs in-process; the generated
Action and Robot run in RCC.
"""

from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
import re
import sys
import time
import tomllib
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
from action_server_tests.test_internal_child_admission import (
    _grant_deployment_ref,
    _grant_refs,
    _reference_grants_for_package,
)
from action_server_tests.test_internal_child_admission import (  # noqa: F811
    admitted as admitted,
)
from action_server_tests.test_robot_package_admission import request_for
from contract_tests.test_package_revision_compiler import _entry
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolRequestParams, Request, Tool
from pydantic import TypeAdapter

from actions.server._models import Run, RunStatus
from actions.server.deployments.foundry_values import (
    CapabilityPlanPolicy,
    DeploymentSpecification,
    InternalRobotBinding,
    InternalRobotDelegationPolicy,
)
from actions.server.deployments.ids import DeploymentId
from actions.server.deployments.package_revision_compiler import (
    PinnedRccPackageBuildExecutor,
    load_prepared_rcc_environment,
)
from actions.server.foundry.mcp import CanvasCaller
from actions.server.foundry.robot_execution import RccRobotPreparation
from actions.server.foundry.robot_runtime_profile import RuntimeCapabilityRunner
from actions.server.foundry.robot_runtime_runner import PinnedRobotRunner
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
from actions.server.mcp.task_wire import TASK_EXTENSION
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import RunChildLineage, RunOutput, RunTaskReceipt
from actions.server.run_outputs.service import RunOutputControlPlane, _one
from actions.server.run_outputs.task_host import DetachedTaskHost
from actions.server.run_outputs.task_service import TaskPolicy, TaskService
from actions.server.run_outputs.types import OutputRef

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or os.environ.get("ACTIONS_INTERNAL_CHILD_REAL_RCC") != "1",
    reason="Linux and explicit real-RCC opt-in required",
)

_OPT_IN = "ACTIONS_INTERNAL_CHILD_REAL_RCC"
_ACTION_RECEIPT = "ACTIONS_INTERNAL_CHILD_ACTION_RCC_RECEIPT"
_ROBOT_RECEIPT = "ACTIONS_INTERNAL_CHILD_ROBOT_RCC_RECEIPT"
_CORE_WHEEL = "ACTIONS_INTERNAL_CHILD_CORE_WHEEL"
_CORE_SHA256 = "ACTIONS_INTERNAL_CHILD_CORE_WHEEL_SHA256"
_RUNTIME_WHEEL = "ACTIONS_INTERNAL_CHILD_RUNTIME_WHEEL"
_RUNTIME_SHA256 = "ACTIONS_INTERNAL_CHILD_RUNTIME_WHEEL_SHA256"
_WORK_ITEMS_WHEEL = "ACTIONS_INTERNAL_CHILD_WORK_ITEMS_WHEEL"
_WORK_ITEMS_SHA256 = "ACTIONS_INTERNAL_CHILD_WORK_ITEMS_WHEEL_SHA256"
_RCC = "ACTIONS_RUNTIME_RCC_BINARY"
_ROBOT_MARKER = "ACTIONS340_CHILD_ROBOT_E2E"


def _required_inputs() -> tuple[Path, Path, Path, str, Path, Path, str, Path, str]:
    if os.environ.get(_OPT_IN) != "1":
        pytest.skip(f"set {_OPT_IN}=1 to run the real Action-to-Robot vertical")
    values = {
        _ACTION_RECEIPT: os.environ.get(_ACTION_RECEIPT, ""),
        _ROBOT_RECEIPT: os.environ.get(_ROBOT_RECEIPT, ""),
        _CORE_WHEEL: os.environ.get(_CORE_WHEEL, ""),
        _CORE_SHA256: os.environ.get(_CORE_SHA256, ""),
        _RUNTIME_WHEEL: os.environ.get(_RUNTIME_WHEEL, ""),
        _RUNTIME_SHA256: os.environ.get(_RUNTIME_SHA256, ""),
        _WORK_ITEMS_WHEEL: os.environ.get(_WORK_ITEMS_WHEEL, ""),
        _WORK_ITEMS_SHA256: os.environ.get(_WORK_ITEMS_SHA256, ""),
        _RCC: os.environ.get(_RCC, ""),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        pytest.fail("opt-in real vertical missing prerequisites: " + ", ".join(missing))
    action_receipt = Path(values[_ACTION_RECEIPT]).resolve(strict=True)
    robot_receipt = Path(values[_ROBOT_RECEIPT]).resolve(strict=True)
    core_wheel = Path(values[_CORE_WHEEL]).resolve(strict=True)
    runtime_wheel = Path(values[_RUNTIME_WHEEL]).resolve(strict=True)
    work_items_wheel = Path(values[_WORK_ITEMS_WHEEL]).resolve(strict=True)
    rcc = Path(values[_RCC]).resolve(strict=True)
    expected_hashes = {
        _CORE_WHEEL: values[_CORE_SHA256],
        _RUNTIME_WHEEL: values[_RUNTIME_SHA256],
        _WORK_ITEMS_WHEEL: values[_WORK_ITEMS_SHA256],
    }
    if (
        not action_receipt.is_file()
        or not robot_receipt.is_file()
        or not core_wheel.is_file()
        or not runtime_wheel.is_file()
        or not work_items_wheel.is_file()
        or not rcc.is_file()
        or not os.access(rcc, os.X_OK)
        or any(
            not re.fullmatch(r"[0-9a-f]{64}", digest)
            for digest in expected_hashes.values()
        )
    ):
        pytest.fail("opt-in real vertical prerequisite path or hash is invalid")
    for path, expected in (
        (core_wheel, expected_hashes[_CORE_WHEEL]),
        (runtime_wheel, expected_hashes[_RUNTIME_WHEEL]),
        (work_items_wheel, expected_hashes[_WORK_ITEMS_WHEEL]),
    ):
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            pytest.fail(f"host candidate wheel SHA-256 differs: {path.name}")
    return (
        action_receipt,
        robot_receipt,
        core_wheel,
        expected_hashes[_CORE_WHEEL],
        rcc,
        runtime_wheel,
        expected_hashes[_RUNTIME_WHEEL],
        work_items_wheel,
        expected_hashes[_WORK_ITEMS_WHEEL],
    )


def _verify_installed_wheel(
    wheel_path: Path,
    expected_wheel_hash: str,
    distribution_name: str,
    import_name: str,
    expected_version: str | None = None,
) -> str:
    """Prove the current pytest process imports every package from its exact wheel."""
    if hashlib.sha256(wheel_path.read_bytes()).hexdigest() != expected_wheel_hash:
        pytest.fail(f"{distribution_name} wheel hash changed")
    try:
        with zipfile.ZipFile(wheel_path) as archive:
            members = set(archive.namelist())
            metadata_names = [n for n in members if n.endswith(".dist-info/METADATA")]
            if len(metadata_names) != 1:
                pytest.fail(f"{distribution_name} wheel metadata is ambiguous")
            metadata = archive.read(metadata_names[0]).decode("utf-8", errors="strict")
            names = re.findall(r"(?mi)^Name: ([^\r\n]+)\s*$", metadata)
            versions = re.findall(r"(?mi)^Version: ([^\r\n]+)\s*$", metadata)
            if (
                len(names) != 1
                or names[0].lower().replace("_", "-") != distribution_name
            ):
                pytest.fail(f"wheel is not {distribution_name}")
            if len(versions) != 1 or (
                expected_version and versions[0] != expected_version
            ):
                pytest.fail(f"{distribution_name} wheel version differs from expected")
            wheel_version = versions[0]
            package_members = {
                name
                for name in members
                if not name.endswith(".dist-info/RECORD")
                and not name.endswith(".dist-info/WHEEL")
                and not name.endswith(".dist-info/METADATA")
                and ".dist-info/" not in name
            }
            dist = importlib.metadata.distribution(distribution_name)
            if dist.version != wheel_version:
                pytest.fail(f"installed {distribution_name} version differs from wheel")
            installed_files = {
                str(item).replace("\\", "/"): item for item in (dist.files or [])
            }
            module = importlib.import_module(import_name)
            if module.__file__ is None:
                raise AssertionError(f"{import_name} has no module file")
            module_path = Path(module.__file__).resolve()
            relevant = sorted(package_members)
            if not relevant:
                pytest.fail(f"{distribution_name} wheel has no files for {import_name}")
            for name in relevant:
                item = installed_files.get(name)
                if item is None:
                    raise AssertionError(
                        f"installed {distribution_name} omits wheel member {name}"
                    )
                installed_path = Path(str(dist.locate_file(item))).resolve()
                if (
                    not installed_path.is_file()
                    or installed_path.read_bytes() != archive.read(name)
                ):
                    pytest.fail(
                        f"installed {distribution_name} bytes differ for {name}"
                    )
            module_candidates = [
                Path(str(dist.locate_file(installed_files[n]))).resolve()
                for n in relevant
                if n.endswith("/__init__.py") or n.endswith(".py")
            ]
            if module_path not in module_candidates:
                pytest.fail(
                    f"{import_name} import is not owned by installed {distribution_name}"
                )
            return wheel_version
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
        raise AssertionError(f"{distribution_name} wheel is unreadable: {exc}") from exc


def _verify_host_wheel_origins(inputs) -> None:
    (
        _,
        _,
        core_wheel,
        core_hash,
        _,
        runtime_wheel,
        runtime_hash,
        work_items_wheel,
        work_items_hash,
    ) = inputs
    _verify_installed_wheel(
        runtime_wheel, runtime_hash, "actions-runtime", "actions.server"
    )
    _verify_installed_wheel(
        core_wheel, core_hash, "actions-core", "actions.internal_runtime"
    )
    _verify_installed_wheel(
        work_items_wheel, work_items_hash, "actions-work-items", "actions.work_items"
    )


def _wheel_identity(core_wheel: Path) -> tuple[str, dict[str, dict[str, object]]]:
    """Read exact wheel payload hashes and validate its own RECORD table."""
    try:
        with zipfile.ZipFile(core_wheel) as archive:
            names = set(archive.namelist())
            metadata_names = [
                name for name in names if name.endswith(".dist-info/METADATA")
            ]
            record_names = [
                name for name in names if name.endswith(".dist-info/RECORD")
            ]
            if len(metadata_names) != 1 or len(record_names) != 1:
                pytest.fail("candidate Core wheel metadata inventory is ambiguous")
            metadata = archive.read(metadata_names[0]).decode("utf-8", errors="strict")
            if not re.search(r"(?mi)^Name: actions[-_]core\s*$", metadata):
                pytest.fail("candidate wheel is not the actions-core distribution")
            version_matches = re.findall(r"(?mi)^Version: ([^\r\n]+)\s*$", metadata)
            if len(version_matches) != 1:
                pytest.fail("candidate Core wheel has no unique Version field")
            version = version_matches[0]
            raw_record = archive.read(record_names[0]).decode("utf-8", errors="strict")
            rows: dict[str, tuple[str, str]] = {}
            for row in csv.reader(io.StringIO(raw_record)):
                if len(row) != 3 or row[0] in rows:
                    pytest.fail("candidate Core wheel RECORD is malformed")
                rows[row[0]] = (row[1], row[2])
            wheel_members = names - {record_names[0]}
            if set(rows) != names:
                pytest.fail("candidate Core wheel RECORD inventory differs")
            result: dict[str, dict[str, object]] = {}
            for name in sorted(wheel_members):
                content = archive.read(name)
                digest = hashlib.sha256(content).digest()
                record_hash = "sha256=" + base64.urlsafe_b64encode(
                    digest
                ).decode().rstrip("=")
                if rows[name] != (record_hash, str(len(content))):
                    pytest.fail(f"candidate wheel RECORD does not bind {name}")
                result[name] = {
                    "sha256": digest.hex(),
                    "record_hash": record_hash,
                    "size": len(content),
                }
            if rows[record_names[0]] != ("", ""):
                pytest.fail("candidate Core wheel RECORD self-entry is invalid")
            return version, result
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
        raise AssertionError(
            f"candidate Core wheel metadata is unreadable: {exc}"
        ) from exc


def _load_prepared(
    receipt_path: Path,
    *,
    core_wheel: Path | None = None,
    expected_hash: str | None = None,
    core_version: str | None = None,
):
    prepared = load_prepared_rcc_environment(receipt_path)
    manifest_path = receipt_path.with_name("package.yaml")
    manifest = manifest_path.read_bytes()
    if hashlib.sha256(
        manifest
    ).hexdigest() != prepared.package_yaml_digest.removeprefix("sha256:"):
        pytest.fail("prepared receipt does not bind its adjacent exact package.yaml")
    text = manifest.decode("utf-8", errors="strict")
    if core_wheel is not None:
        if expected_hash is None or core_version is None:
            raise AssertionError("complete candidate Core identity required")
        if not re.search(
            rf"(?m)^\s*-\s*actions-core={re.escape(core_version)}\s*$", text
        ):
            pytest.fail("prepared RCC package.yaml does not exact-pin candidate Core")
        # RCC v18.19.3's Python package resolver uses Product.Home()/wheels as
        # --find-links. The preparer stages the wheel there before publish;
        # presence is diagnostic only. Installed-file/RECORD checks prove
        # which bytes the Action artifact actually contains.
        cached_wheel = prepared.robocorp_home / "wheels" / core_wheel.name
        if (
            prepared.robocorp_home.is_symlink()
            or not prepared.robocorp_home.is_dir()
            or cached_wheel.is_symlink()
            or not cached_wheel.is_file()
            or hashlib.sha256(cached_wheel.read_bytes()).hexdigest() != expected_hash
        ):
            pytest.fail("prepared RCC home does not contain the exact candidate wheel")
    return prepared, manifest


def _verify_core_wheel_matches_source(core_wheel: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    source_root = repository_root / "actions" / "src"
    project = tomllib.loads(
        (repository_root / "actions" / "pyproject.toml").read_text(encoding="utf-8")
    )
    try:
        with zipfile.ZipFile(core_wheel) as archive:
            metadata_names = [
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_names) != 1:
                pytest.fail("candidate Core wheel metadata is ambiguous")
            metadata = archive.read(metadata_names[0]).decode("utf-8", errors="strict")
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
        pytest.fail(f"candidate Core wheel metadata is unreadable: {exc}")
    wheel_version = re.search(r"(?mi)^Version: ([^\r\n]+)\s*$", metadata)
    if (
        wheel_version is None
        or wheel_version.group(1) != project["tool"]["poetry"]["version"]
    ):
        pytest.fail("candidate Core wheel version differs from current source project")
    members = (
        "actions/internal_runtime/__init__.py",
        "actions/internal_runtime/_context.py",
        "actions/internal_runtime/_fd_transport.py",
        "actions/internal_runtime/_models.py",
    )
    try:
        with zipfile.ZipFile(core_wheel) as archive:
            for member in members:
                if archive.read(member) != (source_root / member).read_bytes():
                    pytest.fail(f"candidate wheel source differs for {member}")
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
        pytest.fail(f"candidate Core wheel is not a readable source wheel: {exc}")


def _action_source(
    core_version: str, core_hash: str, wheel_files: dict[str, dict[str, object]]
) -> bytes:
    return (
        "import base64, csv, hashlib, importlib, io\n"
        "from importlib.metadata import distribution\n"
        "from pathlib import Path\n"
        "from actions import action\n"
        "from actions.internal_runtime import submit_child_run\n"
        f"EXPECTED_VERSION = {core_version!r}\n"
        f"EXPECTED_SHA256 = {core_hash!r}\n"
        f"EXPECTED_WHEEL_FILES = {wheel_files!r}\n"
        "@action\n"
        "def delegate(value: str) -> dict[str, str]:\n"
        "    dist = distribution('actions-core')\n"
        "    if dist.version != EXPECTED_VERSION:\n"
        "        raise AssertionError('candidate Core version differs')\n"
        "    module = Path(__import__('actions').__file__).resolve()\n"
        "    files = {str(p): Path(dist.locate_file(p)).resolve() for p in (dist.files or [])}\n"
        "    if files.get('actions/__init__.py') != module:\n"
        "        raise AssertionError('candidate Core distribution ownership missing')\n"
        "    installed_record = dist.read_text('RECORD')\n"
        "    if not installed_record:\n"
        "        raise AssertionError('installed Core has no RECORD')\n"
        "    rows = {}\n"
        "    for row in csv.reader(io.StringIO(installed_record)):\n"
        "        if len(row) != 3 or row[0] in rows:\n"
        "            raise AssertionError('installed Core RECORD is malformed')\n"
        "        rows[row[0]] = (row[1], row[2])\n"
        "    for name, expected in EXPECTED_WHEEL_FILES.items():\n"
        "        path = files.get(name)\n"
        "        if path is None:\n"
        "            raise AssertionError('candidate wheel member missing from installed distribution')\n"
        "        content = path.read_bytes()\n"
        "        digest = hashlib.sha256(content).digest()\n"
        "        record_hash = 'sha256=' + base64.urlsafe_b64encode(digest).decode().rstrip('=')\n"
        "        if len(content) != expected['size'] or digest.hex() != expected['sha256'] or rows.get(name) != (record_hash, str(len(content))) or record_hash != expected['record_hash']:\n"
        "            raise AssertionError('installed Core payload or RECORD differs from candidate wheel')\n"
        "    dist_info_prefix = next(name.rsplit('/', 1)[0] + '/' for name in EXPECTED_WHEEL_FILES if name.endswith('.dist-info/METADATA'))\n"
        "    allowed_generated = {dist_info_prefix + name for name in ('RECORD', 'INSTALLER', 'REQUESTED', 'direct_url.json')}\n"
        "    for name in files:\n"
        "        if '__pycache__' in name.split('/') and name.endswith('.pyc'):\n"
        "            continue\n"
        "        if name.startswith('actions/') and name not in EXPECTED_WHEEL_FILES:\n"
        "            raise AssertionError('installed Core has an unexpected package file')\n"
        "        if name.startswith(dist_info_prefix) and name not in EXPECTED_WHEEL_FILES and name not in allowed_generated:\n"
        "            raise AssertionError('installed Core has unexpected distribution metadata')\n"
        "    runtime_module = importlib.import_module('actions.internal_runtime')\n"
        "    if Path(runtime_module.__file__).resolve() != files.get('actions/internal_runtime/__init__.py'):\n"
        "        raise AssertionError('internal Runtime API was not loaded from candidate Core')\n"
        "    child = submit_child_run('scan', key='real-vertical-' + value, inputs={'value': value})\n"
        "    return {'child_run_id': child.id, 'core_wheel_sha256': EXPECTED_SHA256}\n"
    ).encode("utf-8")


@pytest.fixture
def real_vertical_inputs():
    inputs = _required_inputs()
    _verify_host_wheel_origins(inputs)
    return inputs


def test_real_mcp_action_submits_detached_rcc_robot(
    real_vertical_inputs,
    admitted,  # noqa: F811
    foundry_package_store,
    tmp_path,
):
    (
        action_receipt_path,
        robot_receipt_path,
        core_wheel,
        core_hash,
        rcc,
        _runtime_wheel,
        _runtime_hash,
        _work_items_wheel,
        _work_items_hash,
    ) = real_vertical_inputs
    _verify_core_wheel_matches_source(core_wheel)
    core_version, wheel_files = _wheel_identity(core_wheel)
    action_prepared, action_manifest = _load_prepared(
        action_receipt_path,
        core_wheel=core_wheel,
        expected_hash=core_hash,
        core_version=core_version,
    )
    robot_prepared, robot_manifest = _load_prepared(robot_receipt_path)
    if action_receipt_path == robot_receipt_path:
        pytest.fail("Action and Robot require separately bound prepared receipts")

    c = admitted
    registry = c.registry
    actor = c.actor
    workspace = c.workspace
    refs = c.parent_spec

    # Replace the admission fixture's synthetic executor only for this new
    # exact real-RCC Package build. The fixture's existing Package remains
    # untouched and is not used as execution evidence.
    executor = PinnedRccPackageBuildExecutor(action_prepared)
    executor._rcc_binary = rcc
    registry._executor = executor
    action_entries = [
        _entry("package.yaml", action_manifest),
        _entry(
            "generated_actions.py",
            _action_source(core_version, core_hash, wheel_files),
        ),
        _entry(
            "tests/test_generated_action.py",
            b"from generated_actions import delegate\n\n"
            b"import unittest\n\n"
            b"class GeneratedActionTests(unittest.TestCase):\n"
            b"    def test_delegate_is_importable(self):\n"
            b"        self.assertTrue(callable(delegate))\n",
        ),
    ]
    compilation = registry.compile_trusted_source(
        action_entries,
        logical_package_key="actions340-real-child-parent-" + uuid4().hex,
        logical_name="Actions 340 real internal child parent",
        trusted_actor=actor,
        workspace_id=workspace,
        application_id=c.parent_revision.ref.deployment_id,
    )
    if not compilation.evidence.ready or compilation.compiled_package is None:
        pytest.fail("real parent Package did not compile through prepared RCC")
    action_package = registry.admit_compiled(
        actor, workspace, compilation.compiled_package
    )
    _grant_refs(
        db=c.db,
        workspace_id=workspace,
        actor=actor,
        refs=_reference_grants_for_package(registry, action_package),
    )
    action_capability = registry.capability_refs(action_package)[0]
    action_plan = registry.get_capability(action_capability).runtime_plans[0]

    from actions.server.foundry.robot_package_builder import RobotPackageRequest

    robot_data = request_for("rcc").model_dump(mode="json", by_alias=True)
    robot_data["logicalName"] = "Actions 340 real internal child Robot"
    robot_data["taskName"] = "Owned"
    robot_data["files"] = [
        {
            "path": "task.robot",
            "content": "*** Tasks ***\nOwned\n    Log To Console    ACTIONS340_CHILD_ROBOT_E2E\n",
        },
        {"path": "package.yaml", "content": robot_manifest.decode("utf-8")},
    ]
    robot_request = RobotPackageRequest.model_validate(robot_data)
    robot_evidence = registry.prepare_trusted_robot(
        robot_request,
        logical_package_key="actions340-real-child-robot-" + uuid4().hex,
        trusted_actor=actor,
        workspace_id=workspace,
        application_id=c.parent_revision.ref.deployment_id,
        preparation=RccRobotPreparation(rcc, robot_prepared),
    )
    robot_package = registry.admit_robot(actor, workspace, robot_evidence)
    _grant_refs(
        db=c.db,
        workspace_id=workspace,
        actor=actor,
        refs=_reference_grants_for_package(registry, robot_package),
    )
    robot_capability = registry.capability_refs(robot_package)[0]
    robot_plan = registry.get_capability(robot_capability).runtime_plans[0]

    robot_deployment = c.deployments.create(
        actor,
        workspace,
        DeploymentId(str(uuid4())),
        DeploymentSpecification(
            package_revisions=(robot_package,),
            capability_plans=(
                CapabilityPlanPolicy(
                    capability=robot_capability,
                    mode="locked",
                    allowed_plans=(robot_plan,),
                    default_plan=robot_plan,
                ),
            ),
            bindings=(),
            worker=refs.worker,
            policy=refs.policy,
            output_provider=refs.output_provider,
        ),
        idempotency_key="actions340-real-child-robot-" + uuid4().hex,
    )
    _grant_deployment_ref(c.db, workspace, actor, robot_deployment.ref)
    child_policy = InternalRobotDelegationPolicy(
        parent_capability=action_capability,
        bindings=(
            InternalRobotBinding(
                name="scan",
                target_deployment=robot_deployment.ref,
                target_capability=robot_capability,
                target_runtime_plan=robot_plan,
            ),
        ),
        max_children=1,
        parent_exit="allow-authorized-detach",
    )
    parent_deployment = c.deployments.create(
        actor,
        workspace,
        DeploymentId(str(uuid4())),
        DeploymentSpecification(
            package_revisions=(action_package,),
            capability_plans=(
                CapabilityPlanPolicy(
                    capability=action_capability,
                    mode="locked",
                    allowed_plans=(action_plan,),
                    default_plan=action_plan,
                ),
            ),
            # This generated parent has no provider requirements. Do not copy
            # unrelated bindings from the admission fixture's synthetic package.
            bindings=(),
            worker=refs.worker,
            policy=refs.policy,
            output_provider=refs.output_provider,
            model_published_capabilities=(action_capability,),
            internal_robot_delegations=(child_policy,),
        ),
        idempotency_key="actions340-real-child-parent-" + uuid4().hex,
    )
    _grant_deployment_ref(c.db, workspace, actor, parent_deployment.ref)

    control = RunOutputControlPlane(c.db, capabilities=registry)
    control.register(
        c.deployments.resolve(
            actor, workspace, parent_deployment.ref.deployment_id, action_capability
        ).snapshot
    )
    control.grant(actor, parent_deployment.ref, {"execute", "read", "cancel"})
    control.grant(actor, robot_deployment.ref, {"execute", "read", "cancel"})

    snapshot = c.deployments.resolve(
        actor, workspace, parent_deployment.ref.deployment_id, action_capability
    ).snapshot
    c.outputs.providers[snapshot.provider_key] = foundry_package_store
    robot_snapshot = c.deployments.resolve(
        actor, workspace, robot_deployment.ref.deployment_id, robot_capability
    ).snapshot
    c.outputs.providers[robot_snapshot.provider_key] = foundry_package_store
    authority = DetachedActions(c.deployments, c.outputs)
    execution_root = tmp_path / "real-action-robot-execution"
    execution_root.mkdir(mode=0o700)
    from actions.server.foundry.generic_execution_port import PinnedGenericRccRunner

    capability_runner = RuntimeCapabilityRunner(
        PinnedGenericRccRunner(action_prepared, rcc, execution_root / "action"),
        rcc_robot=PinnedRobotRunner(
            RccRobotPreparation(rcc, robot_prepared), execution_root / "robot"
        ),
    )
    host = DetachedTaskHost(
        authority,
        actor=actor,
        worker_id=str(uuid4()),
        profile=snapshot.worker,
        prepared=action_prepared,
        rcc=rcc,
        execution_root=execution_root,
        policy=TaskPolicy("actions340-real-child/v1", 600000, 8),
        capability_runner=capability_runner,
    )
    tasks = TaskService(
        authority,
        readiness=host,
        policy=host.policy,
    )

    class Canvas:
        catalog_identity = "actions340-internal-child-real-vertical"
        uri = "ui://actions340/internal-child.html"

        async def principal(self, ctx):
            request = getattr(ctx, "request", None)
            return (
                CanvasCaller(actor, str(workspace.root), "model")
                if request is not None
                and request.headers.get("authorization") == "Bearer owned-fixture-only"
                else None
            )

        async def tools(self, ctx):
            if await self.principal(ctx) is None:
                return []
            return [
                Tool(
                    name="capability_invoke",
                    input_schema={
                        "type": "object",
                        "properties": {"mode": {"const": "sync"}},
                        "required": ["mode"],
                        "additionalProperties": True,
                    },
                )
            ]

    helper = McpServerSetupHelper(canvas_foundry=Canvas(), task_service=tasks)
    app = helper.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=helper.transport_security,
    )
    from actions.server.mcp.gateway_metadata import McpRequestMetadataMiddleware

    gateway = McpRequestMetadataMiddleware(app)

    try:
        host.start()

        async def submit_through_mcp():
            import httpx2

            async with app.router.lifespan_context(app):
                async with httpx2.AsyncClient(
                    transport=httpx2.ASGITransport(app=gateway),
                    base_url="http://127.0.0.1:8000",
                    headers={"authorization": "Bearer owned-fixture-only"},
                ) as http:
                    async with streamable_http_client(
                        "http://127.0.0.1:8000/mcp", http_client=http
                    ) as streams:
                        async with ClientSession(
                            streams[0],
                            streams[1],
                            extensions={TASK_EXTENSION: {}},
                        ) as session:
                            await session.discover()
                            return await session.send_request(
                                Request(
                                    method="tools/call",
                                    params=CallToolRequestParams(
                                        name="capability_invoke",
                                        arguments={
                                            "mode": "detached",
                                            "snapshot": snapshot.model_dump(
                                                mode="json"
                                            ),
                                            "inputs": {"value": "vertical"},
                                            "idempotencyKey": "actions340-child-vertical",
                                        },
                                    ),
                                ),
                                TypeAdapter(dict),
                            )

        created = asyncio.run(submit_through_mcp())
        parent_id = created["taskId"]
        assert created["resultType"] == "task"
        deadline = time.monotonic() + 240
        child_id = None
        while time.monotonic() < deadline:
            with c.db.connect():
                lineage = c.db.all(
                    RunChildLineage,
                    where="parent_run_id=?",
                    values=[parent_id],
                )
                parent = _one(c.db, Run, parent_id)
                if lineage:
                    child_id = lineage[0].child_run_id
                    child = _one(c.db, Run, child_id)
                    if parent.status in (
                        RunStatus.PASSED,
                        RunStatus.FAILED,
                    ) and child.status in (
                        RunStatus.PASSED,
                        RunStatus.FAILED,
                    ):
                        break
            time.sleep(0.1)
        else:
            pytest.fail("bounded parent/Robot child execution observation timed out")
        assert len(lineage) == 1
        assert lineage[0].binding_name == "scan"
        assert parent.status == RunStatus.PASSED
        assert child.status == RunStatus.PASSED
        assert parent_id != child_id
        assert not c.db.all(RunTaskReceipt, where="run_id=?", values=[child_id])
        output_rows = c.db.all(
            RunOutput,
            where="run_id=? AND state='final'",
            values=[child_id],
        )
        assert {row.name for row in output_rows} >= {
            "robot-output.xml",
            "robot-stdout.log",
        }
        captured = {}
        for row in output_rows:
            ref = OutputRef(
                workspace_id=str(workspace.root),
                run_id=child_id,
                output_id=row.id,
            )
            with c.outputs.resolve(actor, str(workspace.root), ref.handle) as output:
                captured[row.name] = output.read()
        assert _ROBOT_MARKER.encode() in captured["robot-stdout.log"]
        assert (
            _ROBOT_MARKER.encode() in captured["robot-output.xml"]
            or b"<robot" in captured["robot-output.xml"]
        )
        parent_output_rows = c.db.all(
            RunOutput,
            where="run_id=? AND state='final' AND name='generated-action-result.json'",
            values=[parent_id],
        )
        assert len(parent_output_rows) == 1
        parent_ref = OutputRef(
            workspace_id=str(workspace.root),
            run_id=parent_id,
            output_id=parent_output_rows[0].id,
        )
        with c.outputs.resolve(actor, str(workspace.root), parent_ref.handle) as output:
            action_result = json.loads(output.read())
        assert action_result == {
            "child_run_id": child_id,
            "core_wheel_sha256": core_hash,
        }
    finally:
        assert host.close(30), "real Task host failed to settle"
