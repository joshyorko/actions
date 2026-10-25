"""Closed measured Robot Package carrier; no compilation or execution claim."""
from __future__ import annotations

import hashlib
import json
import re
import stat
import zipfile
from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Literal

from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.ids import PackageRevisionId
from actions.server.deployments.package_revision_compiler import (
    _deterministic_source_archive,
    snapshot_source_entries,
)
from actions.server.deployments.source_manifest import SuppliedSourceEntry
from actions.server.foundry.robot_execution import _schema
from actions.server.foundry.robot_package_builder import (
    DirectRobotPlan,
    RccRobotPlan,
    RobotPackageRequest,
    VerifiedRobotPackage,
    _json,
)

SCHEMA = "actions.robot-package/v1"
ADMISSION_SCHEMA = "actions.local-robot-package-admission/v1"
MAX_ARCHIVE = 2 * 1024 * 1024 + 65536
MAX_MANIFEST = 512 * 1024


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return canonicalize_json(json.dumps(value, allow_nan=False).encode())


@dataclass(frozen=True)
class AdmittedRobotPackage:
    manifest_json: bytes
    package_revision_id: PackageRevisionId
    logical_package_key: str
    capability_id: str
    robot: VerifiedRobotPackage

    @property
    def source_archive(self) -> bytes:
        return self.robot.source_archive


@dataclass(frozen=True)
class RobotAdmissionEvidence:
    package: AdmittedRobotPackage
    verification: Literal["source-and-plan-verified"] = "source-and-plan-verified"
    execution: Literal["not-qualified"] = "not-qualified"


def assemble_robot_admission(
    robot: VerifiedRobotPackage, logical_package_key: str
) -> AdmittedRobotPackage:
    if (
        not isinstance(logical_package_key, str)
        or re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,127}", logical_package_key) is None
    ):
        raise ValueError("portable logical Package key required")
    unsigned = {
        "schemaVersion": SCHEMA,
        "identity": {
            "packageId": logical_package_key,
            "logicalName": robot.logical_name,
        },
        "capabilityId": "robot.task",
        "robotManifest": robot.manifest.decode("utf-8"),
        "inputSchema": robot.input_schema.decode("utf-8"),
        "outputSchema": robot.output_schema.decode("utf-8"),
        "plan": robot.plan_payload.decode("utf-8"),
    }
    revision = PackageRevisionId(digest(canonical([SCHEMA, unsigned])))
    raw = canonical({**unsigned, "revisionDigest": revision.root})
    if len(raw) > MAX_MANIFEST:
        raise ValueError("Robot manifest exceeds bound")
    return AdmittedRobotPackage(raw, revision, logical_package_key, "robot.task", robot)


def decode_robot_admission(raw: bytes, archive_bytes: bytes) -> AdmittedRobotPackage:
    """Recompute portable preimages without consulting an executable or provider."""
    if (
        len(raw) > MAX_MANIFEST
        or len(archive_bytes) > MAX_ARCHIVE
        or canonicalize_json(raw) != raw
    ):
        raise ValueError("bounded canonical Robot manifest required")
    value = json.loads(raw)
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schemaVersion",
            "identity",
            "capabilityId",
            "robotManifest",
            "inputSchema",
            "outputSchema",
            "plan",
            "revisionDigest",
        }
        or value["schemaVersion"] != SCHEMA
    ):
        raise ValueError("closed Robot manifest required")
    identity = value["identity"]
    if not isinstance(identity, dict) or set(identity) != {"packageId", "logicalName"}:
        raise ValueError("closed Robot Package identity required")
    for key in ("robotManifest", "inputSchema", "outputSchema", "plan"):
        if not isinstance(value[key], str):
            raise ValueError("immutable JSON byte encoding required")
    manifest = json.loads(value["robotManifest"])
    plan_value = json.loads(value["plan"])
    if not isinstance(manifest, dict) or set(manifest) != {
        "kind",
        "logicalName",
        "sourceInventoryDigest",
        "sourceDigest",
        "suitePath",
        "suiteName",
        "taskName",
        "inputSchemaDigest",
        "outputSchemaDigest",
        "planDigest",
        "discriminator",
    }:
        raise ValueError("closed Robot builder manifest required")
    if not isinstance(plan_value, dict):
        raise ValueError("closed Robot plan required")
    if plan_value.get("runtime_kind") == "direct":
        plan: DirectRobotPlan | RccRobotPlan = DirectRobotPlan()
    elif plan_value.get("runtime_kind") == "rcc":
        keys = ("package_yaml_digest", "specification_digest", "artifact_digest")
        for key in keys:
            if (
                not isinstance(plan_value.get(key), str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", plan_value[key]) is None
            ):
                raise ValueError("measured RCC identity required")
        if plan_value.get("rcc_version") != "v18.19.3":
            raise ValueError("unsupported RCC version")
        plan = RccRobotPlan(
            plan_value["package_yaml_digest"],
            plan_value["specification_digest"],
            plan_value["artifact_digest"],
            plan_value["rcc_version"],
        )
    else:
        raise ValueError("unknown Robot plan")
    if _json(asdict(plan)) != value["plan"].encode():
        raise ValueError("Robot plan encoding differs")
    files = []
    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        infos = archive.infolist()
        if (
            not 1 <= len(infos) <= 256
            or sum(info.file_size for info in infos) > 2 * 1024 * 1024
        ):
            raise ValueError("bounded Robot source inventory required")
        for info in infos:
            mode = info.external_attr >> 16
            if (
                info.is_dir()
                or info.compress_type != zipfile.ZIP_STORED
                or info.flag_bits & 1
                or not stat.S_ISREG(mode)
                or info.file_size > 512 * 1024
            ):
                raise ValueError("invalid Robot source archive member")
            files.append(
                SuppliedSourceEntry(
                    info.filename, "file", archive.read(info), stat.S_IMODE(mode)
                )
            )
    source = snapshot_source_entries(files, protected_input_names=())
    if _deterministic_source_archive(source) != archive_bytes:
        raise ValueError("Robot source archive differs from inventory")
    request = RobotPackageRequest.model_validate_json(
        _json(
            {
                "kind": "robot",
                "logicalName": identity["logicalName"],
                "files": [
                    {"path": f.path, "content": f.content.decode("utf-8")}
                    for f in source.files
                ],
                "suitePath": manifest["suitePath"],
                "suiteName": manifest["suiteName"],
                "taskName": manifest["taskName"],
                "inputSchema": json.loads(value["inputSchema"]),
                "runtimeKind": plan.runtime_kind,
            }
        )
    )
    file_map = {f.path: f.content for f in source.files}
    if (
        request.suite_path not in file_map
        or not request.suite_path.endswith(".robot")
        or any(
            any(ord(c) < 32 for c in name)
            for name in (request.logical_name, request.suite_name, request.task_name)
        )
    ):
        raise ValueError("invalid retained Robot identity")
    if (
        isinstance(plan, RccRobotPlan)
        and digest(file_map.get("package.yaml", b"")) != plan.package_yaml_digest
    ):
        raise ValueError("RCC package.yaml differs")
    input_schema = value["inputSchema"].encode()
    _schema(input_schema)
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
    expected = _json(
        {
            "kind": "robot",
            "logicalName": request.logical_name,
            "sourceInventoryDigest": source.digest,
            "sourceDigest": digest(archive_bytes),
            "suitePath": request.suite_path,
            "suiteName": request.suite_name,
            "taskName": request.task_name,
            "inputSchemaDigest": digest(input_schema),
            "outputSchemaDigest": digest(output_schema),
            "planDigest": digest(value["plan"].encode()),
            "discriminator": plan.discriminator,
        }
    )
    if (
        expected != value["robotManifest"].encode()
        or output_schema != value["outputSchema"].encode()
    ):
        raise ValueError("Robot builder evidence differs")
    robot = VerifiedRobotPackage(
        request.logical_name,
        source,
        archive_bytes,
        digest(archive_bytes),
        request.suite_path,
        request.suite_name,
        request.task_name,
        input_schema,
        output_schema,
        plan,
        value["plan"].encode(),
        digest(value["plan"].encode()),
        expected,
        digest(expected),
    )
    measured = assemble_robot_admission(robot, identity["packageId"])
    if measured.manifest_json != raw:
        raise ValueError("Robot Package revision differs")
    return measured
