"""Pure Robot package evidence construction, never admission or execution.

The authorized host must verify this outcome and retain its exact identity before
admitting it. A value constructed here is not a grant or a successful run receipt.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from actions.server.deployments.package_revision_compiler import (
    SourceByteSnapshot,
    _deterministic_source_archive,
    snapshot_source_entries,
)
from actions.server.deployments.source_manifest import SuppliedSourceEntry
from actions.server.foundry.robot_execution import (
    ADAPTER_VERSION,
    DISCRIMINATOR,
    ROBOT_VERSION,
    DirectRobotPreparation,
    RccRobotPreparation,
    _schema,
)


def _json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def _digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


class RobotSourceFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    path: str
    content: str


class RobotPackageRequest(BaseModel):
    """Untrusted authoring request; never accepts host authority or identities."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    kind: Literal["robot"]
    logical_name: str = Field(alias="logicalName", min_length=1, max_length=256)
    files: tuple[RobotSourceFile, ...] = Field(min_length=1, max_length=256)
    suite_path: str = Field(alias="suitePath", min_length=1, max_length=4096)
    suite_name: str = Field(alias="suiteName", min_length=1, max_length=256)
    task_name: str = Field(alias="taskName", min_length=1, max_length=256)
    input_schema: dict[str, JsonValue] = Field(alias="inputSchema")
    runtime_kind: Literal["direct", "rcc"] = Field(alias="runtimeKind")


@dataclass(frozen=True)
class DirectRobotPlan:
    runtime_kind: Literal["direct"] = "direct"
    adapter_version: str = ADAPTER_VERSION
    robot_version: str = ROBOT_VERSION
    python_version: tuple[int, int] = (3, 12)
    platform_tag: str = "linux-x86_64"
    discriminator: str = DISCRIMINATOR


@dataclass(frozen=True)
class RccRobotPlan:
    package_yaml_digest: str
    specification_digest: str
    artifact_digest: str
    rcc_version: str
    runtime_kind: Literal["rcc"] = "rcc"
    adapter_version: str = ADAPTER_VERSION
    robot_version: str = ROBOT_VERSION
    python_version: tuple[int, int] = (3, 12)
    platform_tag: str = "linux-x86_64"
    discriminator: str = DISCRIMINATOR


@dataclass(frozen=True)
class VerifiedRobotPackage:
    logical_name: str
    source: SourceByteSnapshot
    source_archive: bytes
    source_digest: str
    suite_path: str
    suite_name: str
    task_name: str
    input_schema: bytes
    output_schema: bytes
    plan: DirectRobotPlan | RccRobotPlan
    plan_payload: bytes
    plan_digest: str
    manifest: bytes
    package_digest: str


def build_robot_package(
    request: RobotPackageRequest,
    *,
    preparation: DirectRobotPreparation | RccRobotPreparation,
) -> VerifiedRobotPackage:
    """Measure supplied bytes; preparation is host-only, never request content.

    This does not import libraries, discover executable tasks or claim build/test
    success. Exact suite/task resolution is rechecked by the pinned executor.
    """
    from dataclasses import asdict

    # Revalidate even model_construct inputs; snapshot mutable schema immediately.
    request = RobotPackageRequest.model_validate_json(
        request.model_dump_json(by_alias=True)
    )
    input_schema = _json(request.input_schema)
    _schema(input_schema)
    path = PurePosixPath(request.suite_path)
    if path.as_posix() != request.suite_path or path.suffix != ".robot":
        raise ValueError("exact Robot suite path required")
    for name in (request.logical_name, request.suite_name, request.task_name):
        if any(ord(c) < 32 for c in name):
            raise ValueError("control characters in Robot identity")
    source = snapshot_source_entries(
        (
            SuppliedSourceEntry(f.path, "file", f.content.encode(), 0o600)
            for f in request.files
        ),
        protected_input_names=(),
    )
    files = {f.path: f.content for f in source.files}
    if request.suite_path not in files:
        raise ValueError("selected suite is absent from retained source")
    if request.runtime_kind == "direct":
        if type(preparation) is not DirectRobotPreparation:
            raise ValueError("direct plan requires direct host preparation")
        plan: DirectRobotPlan | RccRobotPlan = DirectRobotPlan()
    else:
        if type(preparation) is not RccRobotPreparation:
            raise ValueError("RCC plan requires retained host preparation")
        env = preparation.environment
        if (
            "package.yaml" not in files
            or _digest(files["package.yaml"]) != env.package_yaml_digest
        ):
            raise ValueError("retained RCC package.yaml identity differs")
        plan = RccRobotPlan(
            env.package_yaml_digest,
            env.build_identity.specification_digest,
            env.build_identity.artifact_digest,
            env.rcc_version,
        )
    output_schema = _json(
        {
            "type": "object",
            "properties": {
                "suite": {"const": request.suite_name},
                "task": {"const": request.task_name},
                "status": {"enum": ["PASS", "FAIL"]},
            },
            "required": ["suite", "task", "status"],
            "additionalProperties": False,
        }
    )
    archive = _deterministic_source_archive(source)
    plan_payload = _json(asdict(plan))
    manifest = _json(
        {
            "kind": "robot",
            "logicalName": request.logical_name,
            "sourceInventoryDigest": source.digest,
            "sourceDigest": _digest(archive),
            "suitePath": request.suite_path,
            "suiteName": request.suite_name,
            "taskName": request.task_name,
            "inputSchemaDigest": _digest(input_schema),
            "outputSchemaDigest": _digest(output_schema),
            "planDigest": _digest(plan_payload),
            "discriminator": DISCRIMINATOR,
        }
    )
    return VerifiedRobotPackage(
        request.logical_name,
        source,
        archive,
        _digest(archive),
        request.suite_path,
        request.suite_name,
        request.task_name,
        input_schema,
        output_schema,
        plan,
        plan_payload,
        _digest(plan_payload),
        manifest,
        _digest(manifest),
    )


def verify_robot_package(
    package: VerifiedRobotPackage,
    *,
    preparation: DirectRobotPreparation | RccRobotPreparation,
) -> VerifiedRobotPackage:
    """Recompute all measured evidence; host still owns authorization/admission."""
    request = RobotPackageRequest.model_validate_json(
        _json(
            {
                "kind": "robot",
                "logicalName": package.logical_name,
                "files": [
                    {"path": f.path, "content": f.content.decode()}
                    for f in package.source.files
                ],
                "suitePath": package.suite_path,
                "suiteName": package.suite_name,
                "taskName": package.task_name,
                "inputSchema": json.loads(package.input_schema),
                "runtimeKind": package.plan.runtime_kind,
            }
        )
    )
    expected = build_robot_package(request, preparation=preparation)
    if package != expected:
        raise ValueError("Robot package evidence differs from measured source/plan")
    return expected
