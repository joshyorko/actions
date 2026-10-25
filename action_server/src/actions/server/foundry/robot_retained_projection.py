"""Hash-bound Robot SQL metadata only, never source verification or authority.

Execution still verifies retained archive bytes outside SQL. Public output streams
still verify provider seals. This projection does neither and opens no provider.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from uuid import uuid5

from jsonschema.exceptions import SchemaError

from actions.server._portable_paths import portable_path_collision_key
from actions.server.deployments.source_manifest import _validated_parts
from actions.server.foundry.models import FoundryPackageRevision
from actions.server.foundry.robot_execution import _schema
from actions.server.foundry.robot_journal import _closed_pairs
from actions.server.foundry.robot_package_admission import (
    ADMISSION_SCHEMA,
    MAX_ARCHIVE,
    MAX_MANIFEST,
    SCHEMA,
    canonical,
    digest,
)
from actions.server.foundry.robot_package_builder import (
    DirectRobotPlan,
    RccRobotPlan,
    _json,
)
from actions.server.run_outputs.service import FenceRejected
from actions.server.run_outputs.types import ExecutionSnapshot, SealReceipt


def _load(raw, *, canonical_bytes=False):
    if not isinstance(raw, str) or len(raw.encode()) > MAX_MANIFEST:
        raise ValueError("bounded Robot metadata required")
    value = json.loads(
        raw,
        object_pairs_hook=_closed_pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")),
    )
    if canonical_bytes and canonical(value) != raw.encode():
        raise ValueError("canonical Robot metadata required")
    return value


def _closed(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError("closed Robot metadata required")


def _integer(value, lower, upper):
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not lower <= value <= upper
    ):
        raise ValueError("bounded integer required")


def _validation_metadata(carrier, identity):
    """Decode closed receipt/seal metadata without verifying unread blob bytes.

    Identity comes from the already validated retained Package, never the
    carrier. Artifact loading must still verify XML/RCC bytes outside SQL.
    """
    fields = {
        "stdout": ("stdoutDigest", 256 * 1024),
        "stderr": ("stderrDigest", 256 * 1024),
        "output_xml": ("outputXmlDigest", 1024 * 1024),
        "rcc_receipt": ("rccReceiptDigest", 1024 * 1024),
    }
    _closed(carrier, {"schemaVersion", "receipt", "validation", *fields})
    if (
        carrier["schemaVersion"] != "actions.robot-validation-storage/v1"
        or carrier["validation"] not in ("passed", "failed")
        or not isinstance(carrier["receipt"], str)
        or len(carrier["receipt"].encode()) > 16384
    ):
        raise ValueError("closed bounded Robot validation carrier required")
    try:
        receipt = _load(carrier["receipt"], canonical_bytes=True)
    except FenceRejected:
        raise ValueError("duplicate Robot validation receipt key") from None
    _closed(
        receipt,
        {
            *identity,
            "schemaVersion",
            "validationKind",
            "validation",
            "execution",
            "exitCode",
            *(field for field, _ in fields.values()),
        },
    )
    # Ordinary equality treats bool/int/float as equivalent. Retained receipts
    # must preserve the exact scalar types of their immutable identity.
    expected = dict(
        identity,
        schemaVersion="actions.robot-dryrun-validation/v1",
        validationKind="robot-dryrun",
        validation=carrier["validation"],
        execution="not-qualified",
        exitCode=0 if carrier["validation"] == "passed" else 1,
    )
    if any(_json(receipt[key]) != _json(value) for key, value in expected.items()):
        raise ValueError("Robot validation receipt identity differs")
    seals = {}
    for name, (field, limit) in fields.items():
        value = carrier[name]
        if name == "rcc_receipt" and identity["runtimeKind"] == "direct":
            if value is not None or receipt[field] is not None:
                raise ValueError("direct Robot validation has RCC evidence")
            seals[name] = None
            continue
        seal = SealReceipt.model_validate(value)
        if (
            _json(seal.model_dump(mode="json")) != _json(value)
            or seal.size > limit
            or (name in ("output_xml", "rcc_receipt") and seal.size == 0)
            or seal.digest != receipt[field]
        ):
            raise ValueError("Robot validation diagnostic seal differs")
        seals[name] = seal
    return receipt, seals


@dataclass(frozen=True)
class RetainedRobotProjection:
    snapshot: ExecutionSnapshot
    suite_path: str
    suite_name: str
    task_name: str
    source_digest: str
    input_schema: bytes
    output_schema: bytes
    plan: DirectRobotPlan | RccRobotPlan


def robot_projection_if_present(db, snapshot):
    """Identify supported Robot metadata without registry/provider reads.

    None means the scoped row has a non-Robot manifest; its own decoder remains
    responsible. Missing, duplicate or malformed rows never mean non-Robot.
    """
    snapshot = ExecutionSnapshot.model_validate(snapshot)
    ref = snapshot.capability.package_revision
    rows = db.all(
        FoundryPackageRevision,
        where="workspace_id=? AND package_id=? AND revision_id=?",
        values=[
            str(ref.workspace_id.root),
            str(ref.package_id.root),
            ref.revision_id.root,
        ],
    )
    if len(rows) != 1:
        raise FenceRejected("unique retained Package required")
    try:
        row = rows[0]
        manifest = _load(row.manifest_json, canonical_bytes=True)
        if not isinstance(manifest, dict):
            raise ValueError("Package object required")
        schema = manifest.get("schemaVersion")
        if schema != SCHEMA:
            if isinstance(schema, str) and schema.startswith("actions.robot-package/"):
                raise ValueError("unsupported Robot Package version")
            return None
        return _project(row, manifest, snapshot)
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        UnicodeError,
        RecursionError,
        OverflowError,
        SchemaError,
    ):
        raise FenceRejected("retained Robot metadata unavailable or differs") from None


def retained_robot_projection(db, snapshot):
    projected = robot_projection_if_present(db, snapshot)
    if projected is None:
        raise FenceRejected("retained Robot Package required")
    return projected


def _project(row, manifest, snapshot):
    ref = snapshot.capability.package_revision
    _closed(
        manifest,
        {
            "schemaVersion",
            "identity",
            "capabilityId",
            "robotManifest",
            "inputSchema",
            "outputSchema",
            "plan",
            "revisionDigest",
        },
    )
    identity = manifest["identity"]
    _closed(identity, {"packageId", "logicalName"})
    if not isinstance(identity["packageId"], str) or not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_.-]{0,127}", identity["packageId"]
    ):
        raise ValueError("portable Robot Package key required")
    unsigned = {
        key: value for key, value in manifest.items() if key != "revisionDigest"
    }
    if (
        manifest["revisionDigest"] != ref.revision_id.root
        or digest(canonical([SCHEMA, unsigned])) != ref.revision_id.root
        or str(
            uuid5(ref.workspace_id.root, "actions.package/v1:" + identity["packageId"])
        )
        != str(ref.package_id.root)
        or row.id != str(uuid5(ref.package_id.root, ref.revision_id.root))
        or manifest["capabilityId"] != "robot.task"
        or snapshot.capability.capability_id.root != "robot.task"
        or snapshot.runtime_plan.package_revision != ref
        or snapshot.capability_authority != "package-revision"
        or snapshot.action_id
        != str(uuid5(ref.package_id.root, snapshot.capability.model_dump_json()))
    ):
        raise ValueError("Robot Package/reference preimage differs")
    builder = _load(manifest["robotManifest"])
    _closed(
        builder,
        {
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
        },
    )
    plan_value = _load(manifest["plan"])
    if not isinstance(plan_value, dict):
        raise ValueError("Robot plan object required")
    if plan_value.get("runtime_kind") == "direct":
        plan = DirectRobotPlan()
    elif plan_value.get("runtime_kind") == "rcc":
        for key in ("package_yaml_digest", "specification_digest", "artifact_digest"):
            if not isinstance(plan_value.get(key), str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", plan_value[key]
            ):
                raise ValueError("measured RCC digest required")
        if plan_value.get("rcc_version") != "v18.19.3":
            raise ValueError("unsupported RCC version")
        plan = RccRobotPlan(
            plan_value["package_yaml_digest"],
            plan_value["specification_digest"],
            plan_value["artifact_digest"],
            plan_value["rcc_version"],
        )
    else:
        raise ValueError("unsupported Robot runtime")
    if (
        _json(asdict(plan)) != manifest["plan"].encode()
        or snapshot.runtime_kind != plan.runtime_kind
    ):
        raise ValueError("exact pinned Robot plan required")
    for name in (identity["logicalName"], builder["suiteName"], builder["taskName"]):
        if (
            not isinstance(name, str)
            or not 1 <= len(name) <= 256
            or any(ord(c) < 32 for c in name)
        ):
            raise ValueError("bounded Robot identity required")
    inventory = _load(row.source_inventory_json, canonical_bytes=True)
    _closed(inventory, {"sourcePolicyVersion", "entries"})
    _integer(inventory["sourcePolicyVersion"], 1, 1)
    entries = inventory["entries"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 256:
        raise ValueError("bounded source inventory required")
    paths = []
    collisions = set()
    total = 0
    for entry in entries:
        _closed(entry, {"path", "mode", "size", "sha256"})
        _validated_parts(entry["path"])
        _integer(entry["mode"], 0o644, 0o755)
        if entry["mode"] not in (0o644, 0o755):
            raise ValueError("normalized source mode required")
        _integer(entry["size"], 0, 512 * 1024)
        if not isinstance(entry["sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", entry["sha256"]
        ):
            raise ValueError("source digest required")
        key = portable_path_collision_key(entry["path"])
        if key in collisions or any(
            parent.as_posix() in paths
            for parent in PurePosixPath(entry["path"]).parents
        ):
            raise ValueError("unique portable source paths required")
        collisions.add(key)
        paths.append(entry["path"])
        total += entry["size"]
    if (
        paths != sorted(paths)
        or total > 2 * 1024 * 1024
        or builder["suitePath"] not in paths
        or not builder["suitePath"].endswith(".robot")
    ):
        raise ValueError("Robot source selection differs")
    admission = _load(row.build_evidence_json, canonical_bytes=True)
    _closed(
        admission,
        {"schemaVersion", "source", "validation"}
        if isinstance(admission, dict) and "validation" in admission
        else {"schemaVersion", "source"},
    )
    if admission["schemaVersion"] != ADMISSION_SCHEMA:
        raise ValueError("Robot admission version differs")
    seal = SealReceipt.model_validate(admission["source"])
    if seal.size > MAX_ARCHIVE or seal.digest != row.source_artifact_digest:
        raise ValueError("Robot retained source seal differs")
    if isinstance(plan, RccRobotPlan):
        package_entries = [
            entry for entry in entries if entry["path"] == "package.yaml"
        ]
        if (
            len(package_entries) != 1
            or "sha256:" + package_entries[0]["sha256"] != plan.package_yaml_digest
        ):
            raise ValueError("RCC source manifest differs")
    input_schema = manifest["inputSchema"].encode()
    if _json(_schema(input_schema)) != input_schema:
        raise ValueError("canonical Robot input schema required")
    output_schema = _json(
        {
            "type": "object",
            "properties": {
                "suite": {"const": builder["suiteName"]},
                "task": {"const": builder["taskName"]},
                "status": {"enum": ["PASS", "FAIL"]},
            },
            "required": ["suite", "task", "status"],
            "additionalProperties": False,
        }
    )
    expected = {
        "kind": "robot",
        "logicalName": identity["logicalName"],
        "sourceInventoryDigest": digest(row.source_inventory_json.encode()),
        "sourceDigest": row.source_artifact_digest,
        "suitePath": builder["suitePath"],
        "suiteName": builder["suiteName"],
        "taskName": builder["taskName"],
        "inputSchemaDigest": digest(input_schema),
        "outputSchemaDigest": digest(output_schema),
        "planDigest": digest(manifest["plan"].encode()),
        "discriminator": plan.discriminator,
    }
    if (
        _json(expected) != manifest["robotManifest"].encode()
        or output_schema != manifest["outputSchema"].encode()
        or expected["planDigest"] != snapshot.runtime_plan.plan_digest.root
        or expected["inputSchemaDigest"] != snapshot.capability_schema_digest
    ):
        raise ValueError("Robot source/schema/plan preimages differ")
    if "validation" in admission:
        _validation_metadata(
            admission["validation"],
            dict(
                packageRevisionId=ref.revision_id.root,
                sourceDigest=row.source_artifact_digest,
                planDigest=expected["planDigest"],
                runtimeKind=plan.runtime_kind,
                suitePath=builder["suitePath"],
                suiteName=builder["suiteName"],
                taskName=builder["taskName"],
                robotVersion=plan.robot_version,
                pythonVersion=list(plan.python_version),
                platformTag=plan.platform_tag,
            ),
        )
    return RetainedRobotProjection(
        snapshot,
        builder["suitePath"],
        builder["suiteName"],
        builder["taskName"],
        row.source_artifact_digest,
        input_schema,
        output_schema,
        plan,
    )
