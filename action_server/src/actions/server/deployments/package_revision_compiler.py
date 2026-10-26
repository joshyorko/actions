"""Bounded, explicit source inputs for Package Revision compilation.

This module currently snapshots caller-supplied generated source bytes. The
inventory digest identifies only the canonical path/mode/size/content-hash
inventory; it is not a source archive digest, Package Revision ID, Runtime Plan
digest, authorization decision, or code-execution boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Protocol, cast

import yaml

from actions.server._rcc_runtime_adapter import (
    RCC_CONTRACT_VERSION,
    RCC_VERSION,
    RccRuntimeDescriptor,
    build_exec_command,
    parse_published_artifact_details,
)
from actions.server.deployments import canonical, ids, source_manifest, source_staging
from actions.server.deployments.foundry_values import WorkItemDeclaration
from actions.server.deployments.logical_bindings import (
    LogicalBindingRequirement,
    normalize_requirements,
)

MAX_COMPILER_SOURCE_ENTRIES = 32
MAX_COMPILER_SOURCE_FILES = 16
MAX_COMPILER_SOURCE_FILE_BYTES = 512 * 1024
MAX_COMPILER_SOURCE_TOTAL_BYTES = 2 * 1024 * 1024
MAX_COMPILER_METADATA_BYTES = 512 * 1024
MAX_RCC_OUTPUT_BYTES = 1024 * 1024
RCC_BUILD_TIMEOUT_SECONDS = 600
PACKAGE_SCHEMA_VERSION = "actions.package-revision/v1-draft"
PACKAGE_BINDINGS_SCHEMA_VERSION = "actions.package-revision/v2-bindings-draft"
PACKAGE_INVOCATIONS_SCHEMA_VERSION = "actions.package-revision/v3-invocations-draft"
KNOWLEDGE_CORE_RANGE = ">=1.1.0a4,<2.0.0"
KNOWLEDGE_RUNTIME_RANGE = ">=1.1.0a39,<2.0.0"
RUNTIME_PLAN_SCHEMA_VERSION = 1
RUNTIME_PLAN_ADAPTER_SCHEMA_ID = "actions.rcc-environment-specification"
RUNTIME_PLAN_ADAPTER_SCHEMA_VERSION = "v1-draft"
COMPILER_NORMALIZATION_VERSION = "actions-foundry-normalizer/v1-draft"
COMPILER_VERSION = "actions-package-compiler/v1"
CANONICALIZER_VERSION = "actions-canonical-json/v1"
RCC_ADAPTER_VERSION_RANGE = "==18.19.3"
_PACKAGE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_CAPABILITY_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{0,127}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_DEPENDENCY_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9_.-]*)(?P<version>==|=)(?P<pin>[0-9]+(?:\.[0-9]+)*(?:[A-Za-z][0-9A-Za-z]*(?:[.+_-][0-9A-Za-z]+)*)?)$"
)


def _package_schema(requirements):
    if any(requirement.invocations is not None for requirement in requirements):
        return PACKAGE_INVOCATIONS_SCHEMA_VERSION
    return PACKAGE_BINDINGS_SCHEMA_VERSION if requirements else PACKAGE_SCHEMA_VERSION


def _validate_invocation_compatibility(requirements, compatibility, environment):
    if _package_schema(requirements) != PACKAGE_INVOCATIONS_SCHEMA_VERSION:
        return
    from actions.server.data_queries.knowledge_operations import knowledge_contract

    for requirement in requirements:
        if requirement.invocations is not None:
            for operation in requirement.operations:
                knowledge_contract(operation)
    # Retain the original draft pin and the qualified owned Core replacement.
    # Do not silently bless an older SDK or an unqualified future context reader.
    core = [
        item["constraint"]
        for item in environment
        if item["kind"] == "python-package" and item["name"] == "actions-core"
    ]
    if core not in (["==1.1.0a4"], ["==1.1.0a7"], ["==1.1.0a8"]) or compatibility != {
        "actionsCoreRange": KNOWLEDGE_CORE_RANGE,
        "actionsRuntimeRange": KNOWLEDGE_RUNTIME_RANGE,
    }:
        raise ValueError(
            "mapped Knowledge requires a qualified Core a4/a7/a8 pin and Runtime a39 contract"
        )


@dataclass(frozen=True)
class SourceByteFile:
    """One selected regular file in the canonical source-byte snapshot."""

    path: str
    mode: int
    content: bytes


@dataclass(frozen=True)
class SourceByteSnapshot:
    """Immutable selected bytes and their canonical source inventory identity."""

    inventory: source_manifest.ProposedInventoryValidation
    digest: str
    files: tuple[SourceByteFile, ...]


class TrustedDeveloperExecutionAdmission(Enum):
    """Explicit caller acknowledgment that generated code will be executed.

    This documents developer intent. It is not an authorization system or a
    security sandbox; the generated Action and its tests run as trusted code.
    """

    TRUSTED = "trusted-developer-execution"


@dataclass(frozen=True)
class PackageCompilationPolicy:
    """Trusted package metadata supplied by the owning Runtime integration."""

    package_id: str
    logical_name: str
    actions_runtime_range: str
    actions_core_range: str
    compiler_normalization_version: str = COMPILER_NORMALIZATION_VERSION
    rcc_adapter_version_range: str = RCC_ADAPTER_VERSION_RANGE
    work_items: WorkItemDeclaration = WorkItemDeclaration()
    logical_requirements: tuple[LogicalBindingRequirement, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.work_items, WorkItemDeclaration):
            raise ValueError("typed Work Item declaration required")
        WorkItemDeclaration.model_validate(self.work_items)
        object.__setattr__(
            self,
            "logical_requirements",
            normalize_requirements(self.logical_requirements),
        )
        if not isinstance(self.package_id, str) or not _PACKAGE_ID_RE.fullmatch(
            self.package_id
        ):
            raise ValueError("package_id is not valid for the existing Package schema")
        for field_name, value in (
            ("logical_name", self.logical_name),
            ("actions_runtime_range", self.actions_runtime_range),
            ("actions_core_range", self.actions_core_range),
            ("compiler_normalization_version", self.compiler_normalization_version),
            ("rcc_adapter_version_range", self.rcc_adapter_version_range),
        ):
            if not isinstance(value, str) or not value or len(value) > 128:
                raise ValueError(f"{field_name} must be bounded non-empty text")
        if self.compiler_normalization_version != COMPILER_NORMALIZATION_VERSION:
            raise ValueError("unsupported compiler normalization version")
        if self.rcc_adapter_version_range != RCC_ADAPTER_VERSION_RANGE:
            raise ValueError("this compiler supports only pinned RCC 18.19.3")


@dataclass(frozen=True)
class RccBuildIdentity:
    """RCC's environment specification and local artifact identities."""

    specification_digest: str
    artifact_digest: str

    def __post_init__(self) -> None:
        for digest in (self.specification_digest, self.artifact_digest):
            if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
                raise ValueError("RCC build identities must be sha256 digests")


@dataclass(frozen=True)
class PreparedRccEnvironment:
    """Trusted-host RCC cache prepared for one exact package.yaml byte string.

    The cache home is local process evidence and is never copied into a Package
    manifest or compilation receipt. The generated-code child receives only
    the cache path and RCC's no-build flag; it receives no proxy or account
    settings.
    """

    robocorp_home: Path
    package_yaml_digest: str
    build_identity: RccBuildIdentity
    rcc_version: str = RCC_VERSION

    def __post_init__(self) -> None:
        if (
            not isinstance(self.robocorp_home, Path)
            or not self.robocorp_home.is_absolute()
        ):
            raise ValueError("prepared RCC home must be an absolute local path")
        if not isinstance(self.package_yaml_digest, str) or not _DIGEST_RE.fullmatch(
            self.package_yaml_digest
        ):
            raise ValueError("prepared RCC manifest identity must be a sha256 digest")
        if self.rcc_version != RCC_VERSION:
            raise ValueError("prepared RCC cache must use pinned RCC 18.19.3")

    def to_receipt_bytes(self) -> bytes:
        """Serialize the local preparation evidence without timestamps."""
        return _canonical_json(
            {
                "schemaVersion": "actions.prepared-rcc-cache/v1",
                "rccVersion": self.rcc_version,
                "packageYamlDigest": self.package_yaml_digest,
                "specificationDigest": self.build_identity.specification_digest,
                "artifactDigest": self.build_identity.artifact_digest,
                "robocorpHome": str(self.robocorp_home),
            }
        )


def load_prepared_rcc_environment(receipt_file: Path) -> PreparedRccEnvironment:
    """Read a bounded local receipt from trusted-host RCC preparation."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(receipt_file, flags)
    except OSError as exc:
        raise ValueError("prepared RCC receipt is unavailable") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("prepared RCC receipt must be a regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(8 * 1024 + 1)
    finally:
        os.close(fd)
    if len(raw) > 8 * 1024:
        raise ValueError("prepared RCC receipt exceeds its size limit")
    try:
        value = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("prepared RCC receipt is invalid JSON") from exc
    if not isinstance(value, dict) or set(value) != {
        "schemaVersion",
        "rccVersion",
        "packageYamlDigest",
        "specificationDigest",
        "artifactDigest",
        "robocorpHome",
    }:
        raise ValueError("prepared RCC receipt has an unsupported shape")
    if value["schemaVersion"] != "actions.prepared-rcc-cache/v1":
        raise ValueError("prepared RCC receipt version is unsupported")
    if _canonical_json(value) != raw:
        raise ValueError("prepared RCC receipt bytes are not canonical")
    if not isinstance(value["robocorpHome"], str) or len(value["robocorpHome"]) > 4096:
        raise ValueError("prepared RCC home path is invalid")
    try:
        return PreparedRccEnvironment(
            robocorp_home=Path(value["robocorpHome"]),
            package_yaml_digest=value["packageYamlDigest"],
            build_identity=RccBuildIdentity(
                specification_digest=value["specificationDigest"],
                artifact_digest=value["artifactDigest"],
            ),
            rcc_version=value["rccVersion"],
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("prepared RCC receipt contains invalid identities") from exc


@dataclass(frozen=True)
class RuntimePlanHeader:
    """Portable #129-compatible header for the one declared RCC plan."""

    plan_digest: ids.PlanDigest
    runtime_kind: str
    plan_schema_version: int
    contract_id: str
    adapter_version_range: str
    required_features: tuple[str, ...]
    compatibility_identity_digest: str


@dataclass(frozen=True)
class CompiledPackageRevision:
    """Immutable portable manifest and source/plan payloads from one build."""

    manifest_json: bytes
    source_archive: bytes
    source_inventory_digest: str
    source_artifact_digest: str
    package_revision_id: ids.PackageRevisionId
    runtime_plan_header: RuntimePlanHeader
    runtime_plan_payload: bytes
    adapter_specification_payload: bytes
    input_schema_payload: bytes
    output_schema_payload: bytes
    rcc_specification_digest: str
    rcc_artifact_digest: str


@dataclass(frozen=True)
class CompilationReceipt:
    """Stable, path-free compiler result evidence."""

    source_inventory_digest: str
    source_artifact_digest: str
    status: Literal["succeeded", "failed"]
    build_status: Literal["not-run", "passed", "failed"]
    import_status: Literal["not-run", "passed", "failed"]
    test_status: Literal["not-run", "passed", "failed"]
    failure_code: str | None = None
    package_revision_digest: str | None = None
    runtime_plan_digest: str | None = None
    rcc_specification_digest: str | None = None
    rcc_artifact_digest: str | None = None

    def to_bytes(self) -> bytes:
        value = {
            "schemaVersion": "actions.compiler-receipt/v1-draft",
            "compilerVersion": COMPILER_VERSION,
            "rccVersion": RCC_VERSION,
            "sourceInventoryDigest": self.source_inventory_digest,
            "sourceArtifactDigest": self.source_artifact_digest,
            "status": self.status,
            "phases": {
                "build": self.build_status,
                "import": self.import_status,
                "test": self.test_status,
            },
            "failureCode": self.failure_code,
            "packageRevisionDigest": self.package_revision_digest,
            "runtimePlanDigest": self.runtime_plan_digest,
            "rccSpecificationDigest": self.rcc_specification_digest,
            "rccArtifactDigest": self.rcc_artifact_digest,
        }
        return canonical.canonicalize_json(
            json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )


@dataclass(frozen=True)
class CompilationOutcome:
    compiled_package: CompiledPackageRevision | None
    receipt: CompilationReceipt


def verify_compilation_outcome(outcome: CompilationOutcome) -> CompiledPackageRevision:
    """Verify successful phase evidence and every portable compiled preimage.

    This is an integrity check over compiler output, not caller authorization.
    A trusted host must still admit the selected source and persist the verified
    bytes through the common Package registry.
    """
    if (
        not isinstance(outcome, CompilationOutcome)
        or not isinstance(outcome.receipt, CompilationReceipt)
        or outcome.compiled_package is None
    ):
        raise ValueError("successful compiler output is required")
    receipt = outcome.receipt
    if (
        receipt.status != "succeeded"
        or (receipt.build_status, receipt.import_status, receipt.test_status)
        != ("passed", "passed", "passed")
        or receipt.failure_code is not None
    ):
        raise ValueError("all compiler phases must have passed")
    compiled = outcome.compiled_package
    verify_compiled_package_revision(compiled)
    if (
        receipt.source_inventory_digest != compiled.source_inventory_digest
        or receipt.source_artifact_digest != compiled.source_artifact_digest
        or receipt.package_revision_digest != compiled.package_revision_id.root
        or receipt.runtime_plan_digest != compiled.runtime_plan_header.plan_digest.root
        or receipt.rcc_specification_digest != compiled.rcc_specification_digest
        or receipt.rcc_artifact_digest != compiled.rcc_artifact_digest
    ):
        raise ValueError("compiler receipt does not match compiled package identities")
    return compiled


def verify_compiled_package_revision(compiled: CompiledPackageRevision) -> None:
    """Recompute archive, manifest, plan, schema and adapter payload identities."""
    try:
        _verify_compiled_package_revision(compiled)
    except Exception as exc:
        if (
            isinstance(exc, ValueError)
            and str(exc) == "compiled package integrity check failed"
        ):
            raise
        raise ValueError("compiled package integrity check failed") from None


def _verify_compiled_package_revision(compiled: CompiledPackageRevision) -> None:
    if not isinstance(compiled, CompiledPackageRevision):
        raise ValueError("compiled package has the wrong type")
    if not _DIGEST_RE.fullmatch(compiled.source_inventory_digest):
        raise ValueError("source inventory identity is invalid")
    if not _DIGEST_RE.fullmatch(
        compiled.rcc_specification_digest
    ) or not _DIGEST_RE.fullmatch(compiled.rcc_artifact_digest):
        raise ValueError("RCC build identities are invalid")
    if len(compiled.source_archive) > MAX_COMPILER_SOURCE_TOTAL_BYTES + 64 * 1024:
        raise ValueError("source archive exceeds its size limit")

    from io import BytesIO

    with zipfile.ZipFile(BytesIO(compiled.source_archive), "r") as archive:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_COMPILER_SOURCE_FILES:
            raise ValueError("source archive entry count is invalid")
        supplied: list[source_manifest.SuppliedSourceEntry] = []
        seen_names: set[str] = set()
        for info in infos:
            mode_with_type = info.external_attr >> 16
            if (
                info.filename in seen_names
                or info.is_dir()
                or info.compress_type != zipfile.ZIP_STORED
                or info.file_size > MAX_COMPILER_SOURCE_FILE_BYTES
                or info.compress_size != info.file_size
                or not stat.S_ISREG(mode_with_type)
                or info.flag_bits & 1
            ):
                raise ValueError("source archive entry is not canonical")
            seen_names.add(info.filename)
            content = archive.read(info)
            if len(content) != info.file_size:
                raise ValueError("source archive entry length is invalid")
            supplied.append(
                source_manifest.SuppliedSourceEntry(
                    info.filename,
                    "file",
                    content,
                    stat.S_IMODE(mode_with_type),
                )
            )
    snapshot = snapshot_source_entries(supplied, protected_input_names=[])
    if (
        snapshot.digest != compiled.source_inventory_digest
        or _deterministic_source_archive(snapshot) != compiled.source_archive
        or _sha256_digest(compiled.source_archive) != compiled.source_artifact_digest
    ):
        raise ValueError("source archive preimage does not match")

    manifest = _canonical_object(compiled.manifest_json, MAX_COMPILER_METADATA_BYTES)
    if set(manifest) != {
        "schemaVersion",
        "identity",
        "sourceArtifact",
        "compatibility",
        "capabilities",
        "logicalBindingRequirements",
        "runtimePlans",
    } or manifest["schemaVersion"] not in (
        PACKAGE_SCHEMA_VERSION,
        PACKAGE_BINDINGS_SCHEMA_VERSION,
        PACKAGE_INVOCATIONS_SCHEMA_VERSION,
    ):
        raise ValueError("Package manifest shape is invalid")
    if _canonical_json(manifest) != compiled.manifest_json:
        raise ValueError("Package manifest bytes are not canonical")

    source_artifact = manifest["sourceArtifact"]
    if source_artifact != {
        "digest": compiled.source_artifact_digest,
        "mediaType": "application/vnd.actions.package-source+zip",
        "byteLength": len(compiled.source_archive),
    }:
        raise ValueError("Package source artifact does not match")

    identity = manifest["identity"]
    if not isinstance(identity, dict) or set(identity) != {
        "packageId",
        "logicalName",
        "compilerNormalizationVersion",
        "revisionDigest",
    }:
        raise ValueError("Package identity shape is invalid")
    manifest_without_digest = json.loads(compiled.manifest_json)
    package_digest = manifest_without_digest["identity"].pop("revisionDigest")
    if (
        not isinstance(package_digest, str)
        or package_digest
        != _canonical_digest([manifest["schemaVersion"], manifest_without_digest])
        or compiled.package_revision_id.root != package_digest
        or identity["compilerNormalizationVersion"] != COMPILER_NORMALIZATION_VERSION
    ):
        raise ValueError("Package revision preimage does not match")

    capabilities = manifest["capabilities"]
    plans = manifest["runtimePlans"]
    if not isinstance(capabilities, list) or len(capabilities) != 1:
        raise ValueError("Package must contain exactly one capability")
    if not isinstance(plans, list) or len(plans) != 1:
        raise ValueError("Package must contain exactly one Runtime Plan")
    capability = capabilities[0]
    plan = plans[0]
    if not isinstance(capability, dict) or not isinstance(plan, dict):
        raise ValueError("Package capability and Runtime Plan must be objects")
    raw_requirements = manifest["logicalBindingRequirements"]
    if not isinstance(raw_requirements, list):
        raise ValueError("logical requirement list required")
    requirements = normalize_requirements(
        tuple(
            LogicalBindingRequirement.model_validate_json(json.dumps(value))
            for value in raw_requirements
        )
    )
    expected_schema = _package_schema(requirements)
    if manifest["schemaVersion"] != expected_schema:
        raise ValueError("Package schema and logical requirement presence differ")
    if raw_requirements != [
        value.model_dump(mode="json") for value in requirements
    ] or capability.get("bindingRequirementIds") != [
        value.id for value in requirements
    ]:
        raise ValueError("capability logical requirement identity differs")
    plan_without_digest = dict(plan)
    plan_digest = plan_without_digest.pop("digest")
    if (
        not isinstance(plan_digest, str)
        or plan_digest
        != _canonical_digest(["actions.runtime-plan/v1-draft", plan_without_digest])
        or compiled.runtime_plan_header.plan_digest.root != plan_digest
        or compiled.runtime_plan_payload != _canonical_json(plan_without_digest)
    ):
        raise ValueError("Runtime Plan preimage does not match")

    WorkItemDeclaration.model_validate(
        {
            "mode": capability.get("mode"),
            "allow_outputs": capability.get("allowOutputs"),
        }
    )
    if (
        capability.get("kind") != "action"
        or plan_without_digest.get("schemaVersion") != RUNTIME_PLAN_SCHEMA_VERSION
        or plan_without_digest.get("runtimeKind") != "rcc"
        or plan_without_digest.get("contractId") != RCC_CONTRACT_VERSION
        or capability.get("compatiblePlanDigests") != [plan_digest]
        or plan_without_digest.get("compatibleCapabilityIds") != [capability.get("id")]
    ):
        raise ValueError("Package capability and Runtime Plan do not agree")
    header = compiled.runtime_plan_header
    if (
        header.runtime_kind != plan_without_digest["runtimeKind"]
        or header.plan_schema_version != plan_without_digest["schemaVersion"]
        or header.contract_id != plan_without_digest["contractId"]
        or header.adapter_version_range != plan_without_digest["adapterVersionRange"]
        or header.required_features != tuple(plan_without_digest["requiredFeatures"])
    ):
        raise ValueError("Runtime Plan header does not match its payload")
    expected_header_digest = _canonical_digest(
        {
            "domain": "actions.runtime-plan-compatibility/v1-draft",
            "canonicalizer_version": CANONICALIZER_VERSION,
            "plan_schema_version": header.plan_schema_version,
            "runtime_kind": header.runtime_kind,
            "contract_id": header.contract_id,
            "adapter_version_range": header.adapter_version_range,
            "required_features": list(header.required_features),
        }
    )
    if header.compatibility_identity_digest != expected_header_digest:
        raise ValueError("Runtime Plan compatibility identity does not match")

    input_schema = _canonical_object(
        compiled.input_schema_payload, MAX_COMPILER_METADATA_BYTES
    )
    from actions.server.deployments.logical_bindings import validate_invocation_inputs

    validate_invocation_inputs(requirements, input_schema)
    if expected_schema == PACKAGE_INVOCATIONS_SCHEMA_VERSION:
        _validate_invocation_compatibility(
            requirements, manifest["compatibility"], _validate_package_inputs(snapshot)
        )
    output_schema = _canonical_object(
        compiled.output_schema_payload, MAX_COMPILER_METADATA_BYTES
    )
    if (
        _canonical_json(input_schema) != compiled.input_schema_payload
        or _canonical_json(output_schema) != compiled.output_schema_payload
        or capability.get("inputSchemaDigest")
        != _schema_digest(input_schema, "actions.input-schema/v1-draft")
        or capability.get("outputSchemaDigest")
        != _schema_digest(output_schema, "actions.output-schema/v1-draft")
    ):
        raise ValueError("Action schema payload does not match its identity")

    adapter = _canonical_object(
        compiled.adapter_specification_payload, MAX_COMPILER_METADATA_BYTES
    )
    adapter_specification = plan_without_digest["adapterSpecification"]
    if (
        _canonical_json(adapter) != compiled.adapter_specification_payload
        or adapter_specification
        != {
            "schemaId": RUNTIME_PLAN_ADAPTER_SCHEMA_ID,
            "schemaVersion": RUNTIME_PLAN_ADAPTER_SCHEMA_VERSION,
            "payloadDigest": _sha256_digest(compiled.adapter_specification_payload),
        }
        or adapter.get("schemaVersion") != RUNTIME_PLAN_ADAPTER_SCHEMA_VERSION
        or not _DIGEST_RE.fullmatch(adapter.get("specificationDigest", ""))
        or adapter.get("environmentRequirements")
        != plan_without_digest.get("environmentRequirements")
    ):
        raise ValueError("Runtime Plan adapter payload does not match")
    entrypoint = adapter.get("entrypoint")
    if (
        not isinstance(entrypoint, dict)
        or set(entrypoint) != {"module", "actionName"}
        or not isinstance(entrypoint["module"], str)
        or not isinstance(entrypoint["actionName"], str)
        or capability.get("id") != _capability_id(entrypoint["actionName"])
    ):
        raise ValueError("Action adapter entrypoint does not match")
    if adapter["specificationDigest"] != compiled.rcc_specification_digest:
        raise ValueError("RCC specification identity does not match")


def _canonical_object(payload: bytes, limit: int) -> dict[str, Any]:
    if not isinstance(payload, bytes) or len(payload) > limit:
        raise ValueError("canonical payload exceeds its size limit")
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("canonical payload is invalid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("canonical payload must be an object")
    return value


class PackageBuildExecutor(Protocol):
    """Boundary for the three fixed, bounded RCC package phases."""

    @property
    def rcc_version(self) -> str:
        ...

    def build_environment(
        self, package_yaml: Path, workspace: Path
    ) -> RccBuildIdentity:
        ...

    def import_action(
        self, build: RccBuildIdentity, package_dir: Path, workspace: Path
    ) -> dict[str, Any]:
        ...

    def run_tests(
        self, build: RccBuildIdentity, package_dir: Path, workspace: Path
    ) -> None:
        ...


def snapshot_source_entries(
    entries: Iterable[source_manifest.SuppliedSourceEntry],
    *,
    protected_input_names: Iterable[str],
) -> SourceByteSnapshot:
    """Validate and snapshot a bounded explicit set of source entries.

    The returned digest is SHA-256 over the existing canonical source inventory
    bytes. The function consumes at most ``MAX_COMPILER_SOURCE_ENTRIES`` values
    and retains at most ``MAX_COMPILER_SOURCE_TOTAL_BYTES`` of regular-file
    content. Files are ordered by the existing source-manifest policy.
    """
    if isinstance(entries, (str, bytes)):
        raise TypeError("entries must be an iterable of separate values")

    protected = _bounded_names(protected_input_names, "protected input names")
    supplied: list[source_manifest.SuppliedSourceEntry] = []
    source_file_count = 0
    total_source_bytes = 0
    for entry in entries:
        if len(supplied) >= MAX_COMPILER_SOURCE_ENTRIES:
            raise ValueError("compiler source entries exceed the entry limit")
        if not isinstance(entry, source_manifest.SuppliedSourceEntry):
            raise TypeError("entries must be SuppliedSourceEntry values")
        if entry.kind == "file":
            source_file_count += 1
            if source_file_count > MAX_COMPILER_SOURCE_FILES:
                raise ValueError("compiler source files exceed the file limit")
            if not isinstance(entry.content, bytes):
                raise ValueError("regular-file entries require supplied bytes")
            if len(entry.content) > MAX_COMPILER_SOURCE_FILE_BYTES:
                raise ValueError("compiler source file exceeds the byte limit")
            total_source_bytes += len(entry.content)
            if total_source_bytes > MAX_COMPILER_SOURCE_TOTAL_BYTES:
                raise ValueError("compiler source entries exceed the byte limit")
        supplied.append(entry)

    inventory = source_manifest.validate_proposed_inventory(
        supplied, protected_input_names=protected
    )
    content_by_path = {
        entry.path: entry.content
        for entry in supplied
        if entry.kind == "file" and isinstance(entry.content, bytes)
    }
    files = tuple(
        SourceByteFile(
            path=entry.path, mode=entry.mode, content=content_by_path[entry.path]
        )
        for entry in inventory.entries
    )
    digest = "sha256:" + hashlib.sha256(inventory.canonical_json).hexdigest()
    return SourceByteSnapshot(inventory=inventory, digest=digest, files=files)


def stage_source_snapshot(
    source_root_fd: int,
    destination_fd: int,
    entries: Iterable[source_manifest.SuppliedSourceEntry],
    *,
    selected_file_names: Iterable[str],
    protected_input_names: Iterable[str],
) -> SourceByteSnapshot:
    """Stage and verify the exact explicit generated bytes beneath borrowed FDs.

    The caller supplies an opened source root and an empty, owner-private staging
    destination. ``source_staging`` validates both filesystem boundaries and
    confirms the copied bytes; this function additionally requires their
    canonical inventories to match the caller's immutable byte inputs.
    """
    selected = _bounded_names(selected_file_names, "selected file names")
    protected = _bounded_names(protected_input_names, "protected input names")
    snapshot = snapshot_source_entries(entries, protected_input_names=protected)
    expected_names = tuple(entry.path for entry in snapshot.files)
    if tuple(sorted(selected)) != expected_names:
        raise ValueError("selected paths do not match explicit source bytes")
    if len(set(selected)) != len(selected):
        raise ValueError("selected source paths contain duplicates")

    staged = source_staging.stage_selected_files(
        source_root_fd,
        destination_fd,
        selected,
        protected_input_names=protected,
    )
    expected_inventory = snapshot.inventory.canonical_json
    if (
        staged.source.inventory.canonical_json != expected_inventory
        or staged.inventory.canonical_json != expected_inventory
    ):
        raise ValueError("staged source does not match explicit source bytes")
    return snapshot


def _bounded_names(names: Iterable[str], label: str) -> tuple[str, ...]:
    if isinstance(names, (str, bytes)):
        raise TypeError(f"{label} must be an iterable of separate values")
    values: list[str] = []
    for name in names:
        if len(values) >= MAX_COMPILER_SOURCE_ENTRIES:
            raise ValueError(f"{label} exceed the entry limit")
        if not isinstance(name, str):
            raise TypeError(f"{label} must contain text")
        values.append(name)
    return tuple(values)


def compile_generated_python_action(
    entries: Iterable[source_manifest.SuppliedSourceEntry],
    policy: PackageCompilationPolicy,
    *,
    protected_input_names: Iterable[str],
    admission: TrustedDeveloperExecutionAdmission | None,
    executor: PackageBuildExecutor | None = None,
    execution_root: Path | None = None,
) -> CompilationOutcome:
    """Compile one trusted generated Python Action through a pinned local RCC.

    The caller must explicitly pass ``TrustedDeveloperExecutionAdmission.TRUSTED``.
    This only records developer intent; RCC/Holotree is not a malicious-code
    sandbox. The child environment contains no inherited credentials, no
    provider URL and no external account context. All three RCC phases are
    bounded by fixed source limits and the pinned command timeout.
    """
    snapshot = snapshot_source_entries(
        entries, protected_input_names=protected_input_names
    )
    source_inventory_digest = snapshot.digest
    source_archive = _deterministic_source_archive(snapshot)
    source_artifact_digest = _sha256_digest(source_archive)
    if admission is not TrustedDeveloperExecutionAdmission.TRUSTED:
        return CompilationOutcome(
            None,
            _failure_receipt(
                source_inventory_digest,
                source_artifact_digest,
                failure_code="trusted_execution_not_admitted",
                failed_phase=None,
            ),
        )

    try:
        environment_requirements = _validate_package_inputs(snapshot)
    except (TypeError, ValueError, yaml.YAMLError):
        return CompilationOutcome(
            None,
            _failure_receipt(
                source_inventory_digest,
                source_artifact_digest,
                failure_code="package_input_invalid",
                failed_phase=None,
            ),
        )

    active_executor: PackageBuildExecutor = executor or PinnedRccPackageBuildExecutor()
    if active_executor.rcc_version != RCC_VERSION:
        return CompilationOutcome(
            None,
            _failure_receipt(
                source_inventory_digest,
                source_artifact_digest,
                failure_code="unsupported_rcc_version",
                failed_phase=None,
            ),
        )

    temp_root = str(execution_root) if execution_root is not None else None
    try:
        with tempfile.TemporaryDirectory(
            prefix="actions-package-compiler-", dir=temp_root
        ) as temp_directory:
            workspace = Path(temp_directory)
            package_dir = workspace / "package"
            package_dir.mkdir(mode=0o700)
            _write_source_snapshot(snapshot, package_dir)

            try:
                build = active_executor.build_environment(
                    package_dir / "package.yaml", workspace
                )
            except Exception:
                return CompilationOutcome(
                    None,
                    _failure_receipt(
                        source_inventory_digest,
                        source_artifact_digest,
                        failure_code="rcc_build_failed",
                        failed_phase="build",
                    ),
                )

            try:
                imported = active_executor.import_action(build, package_dir, workspace)
                (
                    action_name,
                    module_name,
                    input_schema,
                    output_schema,
                ) = _validate_action_metadata(imported, package_dir)
            except Exception:
                return CompilationOutcome(
                    None,
                    _failure_receipt(
                        source_inventory_digest,
                        source_artifact_digest,
                        failure_code="action_import_failed",
                        failed_phase="import",
                    ),
                )

            try:
                active_executor.run_tests(build, package_dir, workspace)
            except Exception:
                return CompilationOutcome(
                    None,
                    _failure_receipt(
                        source_inventory_digest,
                        source_artifact_digest,
                        failure_code="action_tests_failed",
                        failed_phase="test",
                    ),
                )

            compiled = _assemble_compiled_package(
                snapshot=snapshot,
                source_archive=source_archive,
                policy=policy,
                environment_requirements=environment_requirements,
                action_name=action_name,
                module_name=module_name,
                input_schema=input_schema,
                output_schema=output_schema,
                build=build,
            )
            receipt = CompilationReceipt(
                source_inventory_digest=source_inventory_digest,
                source_artifact_digest=source_artifact_digest,
                status="succeeded",
                build_status="passed",
                import_status="passed",
                test_status="passed",
                package_revision_digest=compiled.package_revision_id.root,
                runtime_plan_digest=compiled.runtime_plan_header.plan_digest.root,
                rcc_specification_digest=compiled.rcc_specification_digest,
                rcc_artifact_digest=compiled.rcc_artifact_digest,
            )
            return CompilationOutcome(compiled, receipt)
    except (OSError, ValueError):
        return CompilationOutcome(
            None,
            _failure_receipt(
                source_inventory_digest,
                source_artifact_digest,
                failure_code="compiler_workspace_failed",
                failed_phase=None,
            ),
        )


def _failure_receipt(
    source_inventory_digest: str,
    source_artifact_digest: str,
    *,
    failure_code: str,
    failed_phase: Literal["build", "import", "test"] | None,
) -> CompilationReceipt:
    build_status: Literal["not-run", "passed", "failed"] = "not-run"
    import_status: Literal["not-run", "passed", "failed"] = "not-run"
    test_status: Literal["not-run", "passed", "failed"] = "not-run"
    if failed_phase == "build":
        build_status = "failed"
    elif failed_phase == "import":
        build_status = "passed"
        import_status = "failed"
    elif failed_phase == "test":
        build_status = "passed"
        import_status = "passed"
        test_status = "failed"
    return CompilationReceipt(
        source_inventory_digest=source_inventory_digest,
        source_artifact_digest=source_artifact_digest,
        status="failed",
        build_status=build_status,
        import_status=import_status,
        test_status=test_status,
        failure_code=failure_code,
    )


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError("duplicate package.yaml mapping key")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _validate_package_inputs(
    snapshot: SourceByteSnapshot,
) -> tuple[dict[str, str], ...]:
    files = {item.path: item for item in snapshot.files}
    package_file = files.get("package.yaml")
    if package_file is None:
        raise ValueError("package.yaml is required")
    if not any(
        item.path.startswith("tests/") and item.path.endswith(".py")
        for item in snapshot.files
    ):
        raise ValueError("one or more Python tests are required")

    package = yaml.load(package_file.content.decode("utf-8"), Loader=_UniqueKeyLoader)
    if not isinstance(package, dict) or set(package) != {
        "name",
        "description",
        "dependencies",
    }:
        raise ValueError(
            "package.yaml must contain only name, description and dependencies"
        )
    if (
        not isinstance(package["name"], str)
        or not package["name"]
        or len(package["name"]) > 128
        or not isinstance(package["description"], str)
        or len(package["description"]) > 512
    ):
        raise ValueError("package.yaml metadata is invalid")

    dependencies = package["dependencies"]
    if not isinstance(dependencies, dict) or set(dependencies) - {
        "conda-forge",
        "pypi",
    }:
        raise ValueError("package dependencies must use conda-forge and pypi only")
    normalized: list[dict[str, str]] = []
    for channel, kind in (
        ("conda-forge", None),
        ("pypi", "python-package"),
    ):
        packages = dependencies.get(channel, [])
        if (
            not isinstance(packages, list)
            or len(packages) > MAX_COMPILER_SOURCE_ENTRIES
        ):
            raise ValueError("package dependency list is invalid or too large")
        for package_spec in packages:
            if not isinstance(package_spec, str) or len(package_spec) > 256:
                raise ValueError("package dependency is invalid")
            match = _DEPENDENCY_RE.fullmatch(package_spec)
            if match is None:
                raise ValueError("dependencies must be exact version pins")
            name = match.group("name").lower()
            version = match.group("pin")
            req_kind = kind or (
                "python-version" if name == "python" else "system-package"
            )
            normalized.append(
                {
                    "kind": req_kind,
                    "name": name,
                    "constraint": f"=={version}",
                }
            )
    if not any(
        item["kind"] == "python-version" and item["name"] == "python"
        for item in normalized
    ):
        raise ValueError("package environment must pin a Python version")
    keys = [(item["kind"], item["name"]) for item in normalized]
    if len(set(keys)) != len(keys):
        raise ValueError("package environment contains duplicate dependency names")
    requirements = tuple(
        sorted(
            normalized,
            key=lambda item: (item["kind"], item["name"], item["constraint"]),
        )
    )
    return requirements


def _write_source_snapshot(snapshot: SourceByteSnapshot, package_dir: Path) -> None:
    root = package_dir.resolve()
    # Canonical source and archive identity retain POSIX modes on every host.
    # Windows workspace files preserve bytes; mode bits do not establish ACLs.
    fchmod: Callable[[int, int], None] | None = None
    if os.name != "nt":
        candidate = getattr(os, "fchmod", None)
        if not callable(candidate):
            raise RuntimeError("POSIX source snapshot materialization requires fchmod")
        fchmod = cast(Callable[[int, int], None], candidate)
    for item in snapshot.files:
        target = package_dir.joinpath(*PurePosixPath(item.path).parts)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        resolved_parent = target.parent.resolve()
        if root not in (resolved_parent, *resolved_parent.parents):
            raise ValueError("source path escaped the compiler workspace")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(target, flags, item.mode)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(item.content)
            if fchmod is not None:
                fchmod(fd, item.mode)
        finally:
            os.close(fd)


def _validate_action_metadata(
    metadata: dict[str, Any], package_dir: Path
) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    if not isinstance(metadata, dict):
        raise ValueError("Action metadata must be an object")
    actions = metadata.get("actions")
    if not isinstance(actions, list) or len(actions) != 1:
        raise ValueError("the compiler vertical requires exactly one Action")
    action = actions[0]
    if not isinstance(action, dict):
        raise ValueError("Action metadata entry must be an object")
    name = action.get("name")
    source_file = action.get("file")
    input_schema = action.get("input_schema")
    output_schema = action.get("output_schema")
    if (
        not isinstance(name, str)
        or not name.isidentifier()
        or not name.isascii()
        or not isinstance(source_file, str)
        or not isinstance(input_schema, dict)
        or not isinstance(output_schema, dict)
    ):
        raise ValueError("Action name, source file and schemas must be explicit")
    source_path = Path(source_file).resolve()
    root = package_dir.resolve()
    if root not in source_path.parents or not source_path.is_file():
        raise ValueError("Action source must resolve inside the staged package")
    relative = source_path.relative_to(root).with_suffix("").as_posix()
    module = relative.replace("/", ".")
    if any(not part.isidentifier() or not part.isascii() for part in module.split(".")):
        raise ValueError("Action module path is not portable")
    return name, module, input_schema, output_schema


def _canonical_json(value: object) -> bytes:
    return canonical.canonicalize_json(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


def _extract_json_object(
    output: bytes, *, required_keys: tuple[str, ...]
) -> dict[str, Any]:
    try:
        text = output.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("RCC output is not UTF-8") from exc
    decoder = json.JSONDecoder()
    matches: list[dict[str, Any]] = []
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and all(key in value for key in required_keys):
            matches.append(value)
    if len(matches) != 1:
        raise ValueError("RCC output did not contain one matching JSON object")
    return matches[0]


def _parse_rcc_exec_result(output: bytes) -> dict[str, Any]:
    """Parse RCC env-exec's single JSON result without scanning nested objects."""
    try:
        value = json.loads(output)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("RCC execution output is not one JSON result") from exc
    if not isinstance(value, dict) or "artifactDigest" not in value:
        raise ValueError("RCC execution output is not one artifact result")
    return value


def _canonical_digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value)).hexdigest()


def _sha256_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _schema_digest(schema: dict[str, Any], domain: str) -> str:
    return _canonical_digest(
        {
            "domain": domain,
            "canonicalizer_version": CANONICALIZER_VERSION,
            "schema": schema,
        }
    )


def _deterministic_source_archive(snapshot: SourceByteSnapshot) -> bytes:
    from io import BytesIO

    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for item in snapshot.files:
            info = zipfile.ZipInfo(item.path, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = (stat.S_IFREG | item.mode) << 16
            info.flag_bits = 0
            archive.writestr(info, item.content)
    return output.getvalue()


def _capability_id(action_name: str) -> str:
    result = f"action.{action_name}"
    if not _CAPABILITY_ID_RE.fullmatch(result):
        raise ValueError("Action name cannot be represented by the Package schema")
    return result


def _assemble_compiled_package(
    *,
    snapshot: SourceByteSnapshot,
    source_archive: bytes,
    policy: PackageCompilationPolicy,
    environment_requirements: tuple[dict[str, str], ...],
    action_name: str,
    module_name: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    build: RccBuildIdentity,
) -> CompiledPackageRevision:
    source_inventory_digest = snapshot.digest
    source_artifact_digest = _sha256_digest(source_archive)
    capability_id = _capability_id(action_name)
    input_schema_payload = _canonical_json(input_schema)
    output_schema_payload = _canonical_json(output_schema)
    environment_values = list(environment_requirements)
    features = ["task.exec"]
    entrypoint = {"module": module_name, "actionName": action_name}
    adapter_payload = {
        "schemaVersion": RUNTIME_PLAN_ADAPTER_SCHEMA_VERSION,
        "specificationDigest": build.specification_digest,
        "entrypoint": entrypoint,
        "environmentRequirements": environment_values,
    }
    adapter_payload_bytes = _canonical_json(adapter_payload)
    capability = {
        "id": capability_id,
        "kind": "action",
        "mode": policy.work_items.mode,
        "allowOutputs": policy.work_items.allow_outputs,
        "inputSchemaDigest": _schema_digest(
            input_schema, "actions.input-schema/v1-draft"
        ),
        "outputSchemaDigest": _schema_digest(
            output_schema, "actions.output-schema/v1-draft"
        ),
        "compatiblePlanDigests": [],
        "bindingRequirementIds": [
            requirement.id for requirement in policy.logical_requirements
        ],
    }
    adapter_specification = {
        "schemaId": RUNTIME_PLAN_ADAPTER_SCHEMA_ID,
        "schemaVersion": RUNTIME_PLAN_ADAPTER_SCHEMA_VERSION,
        "payloadDigest": _sha256_digest(adapter_payload_bytes),
    }
    runtime_plan_without_digest = {
        "schemaVersion": RUNTIME_PLAN_SCHEMA_VERSION,
        "runtimeKind": "rcc",
        "contractId": RCC_CONTRACT_VERSION,
        "adapterVersionRange": policy.rcc_adapter_version_range,
        "requiredFeatures": features,
        "compatibleCapabilityIds": [capability_id],
        "environmentRequirements": environment_values,
        "adapterSpecification": adapter_specification,
    }
    plan_digest_text = _canonical_digest(
        ["actions.runtime-plan/v1-draft", runtime_plan_without_digest]
    )
    capability["compatiblePlanDigests"] = [plan_digest_text]
    compatibility = {
        "actionsRuntimeRange": policy.actions_runtime_range,
        "actionsCoreRange": policy.actions_core_range,
    }
    runtime_plan = {
        "digest": plan_digest_text,
        **runtime_plan_without_digest,
    }
    from actions.server.deployments.logical_bindings import validate_invocation_inputs

    validate_invocation_inputs(policy.logical_requirements, input_schema)
    _validate_invocation_compatibility(
        policy.logical_requirements, compatibility, environment_requirements
    )
    package_schema = _package_schema(policy.logical_requirements)
    manifest_without_revision_digest: dict[str, Any] = {
        "schemaVersion": package_schema,
        "identity": {
            "packageId": policy.package_id,
            "logicalName": policy.logical_name,
            "compilerNormalizationVersion": policy.compiler_normalization_version,
        },
        "sourceArtifact": {
            "digest": source_artifact_digest,
            "mediaType": "application/vnd.actions.package-source+zip",
            "byteLength": len(source_archive),
        },
        "compatibility": compatibility,
        "capabilities": [capability],
        "logicalBindingRequirements": [
            requirement.model_dump(mode="json")
            for requirement in policy.logical_requirements
        ],
        "runtimePlans": [runtime_plan],
    }
    package_revision_id_text = _canonical_digest(
        [package_schema, manifest_without_revision_digest]
    )
    manifest = {
        **manifest_without_revision_digest,
        "identity": {
            **manifest_without_revision_digest["identity"],
            "revisionDigest": package_revision_id_text,
        },
    }
    compatibility_header_digest = _canonical_digest(
        {
            "domain": "actions.runtime-plan-compatibility/v1-draft",
            "canonicalizer_version": CANONICALIZER_VERSION,
            "plan_schema_version": RUNTIME_PLAN_SCHEMA_VERSION,
            "runtime_kind": "rcc",
            "contract_id": RCC_CONTRACT_VERSION,
            "adapter_version_range": policy.rcc_adapter_version_range,
            "required_features": features,
        }
    )
    header = RuntimePlanHeader(
        plan_digest=ids.PlanDigest(plan_digest_text),
        runtime_kind="rcc",
        plan_schema_version=RUNTIME_PLAN_SCHEMA_VERSION,
        contract_id=RCC_CONTRACT_VERSION,
        adapter_version_range=policy.rcc_adapter_version_range,
        required_features=tuple(features),
        compatibility_identity_digest=compatibility_header_digest,
    )
    return CompiledPackageRevision(
        manifest_json=_canonical_json(manifest),
        source_archive=source_archive,
        source_inventory_digest=source_inventory_digest,
        source_artifact_digest=source_artifact_digest,
        package_revision_id=ids.PackageRevisionId(package_revision_id_text),
        runtime_plan_header=header,
        runtime_plan_payload=_canonical_json(runtime_plan_without_digest),
        adapter_specification_payload=adapter_payload_bytes,
        input_schema_payload=input_schema_payload,
        output_schema_payload=output_schema_payload,
        rcc_specification_digest=build.specification_digest,
        rcc_artifact_digest=build.artifact_digest,
    )


class PinnedRccPackageBuildExecutor:
    """Run fixed package build/import/test commands through bundled RCC.

    The environment is allow-listed and local-only. Generated package code and
    tests execute as trusted developer code. This executor provides bounded
    source and time inputs, not operating-system isolation.
    """

    def __init__(
        self, prepared_environment: PreparedRccEnvironment | None = None
    ) -> None:
        self._rcc_binary = Path(__file__).resolve().parents[1] / "bin" / "rcc-18.19.3"
        self._rcc_home: Path | None = None
        self._prepared_environment = prepared_environment

    @property
    def rcc_version(self) -> str:
        return RCC_VERSION

    def build_environment(
        self, package_yaml: Path, workspace: Path
    ) -> RccBuildIdentity:
        prepared = self._prepared_environment
        if prepared is None:
            self._rcc_home = workspace / "robocorp-home"
            self._rcc_home.mkdir(mode=0o700)
        else:
            try:
                package_yaml_digest = _sha256_digest(package_yaml.read_bytes())
            except OSError as exc:
                raise RuntimeError("prepared RCC manifest is unavailable") from exc
            if package_yaml_digest != prepared.package_yaml_digest:
                raise RuntimeError("prepared RCC manifest identity mismatch")
            if not prepared.robocorp_home.is_dir():
                raise RuntimeError("prepared RCC cache is unavailable")
            self._rcc_home = prepared.robocorp_home
        self._create_execution_dirs(workspace)
        version = self._run([str(self._rcc_binary), "--version"], workspace, timeout=15)
        try:
            reported_version = version.decode("ascii", errors="strict").strip()
        except UnicodeDecodeError as exc:
            raise RuntimeError("bundled RCC version output is not ASCII") from exc
        if reported_version != RCC_VERSION:
            raise RuntimeError("bundled RCC version mismatch")
        publish_command = [str(self._rcc_binary)]
        if prepared is not None:
            publish_command.append("--no-build")
        publish_command.extend(
            [
                "env",
                "publish",
                "--environment",
                str(package_yaml),
                "--json",
                "--provider",
                "local",
            ]
        )
        raw = self._run(
            publish_command,
            workspace,
            timeout=RCC_BUILD_TIMEOUT_SECONDS,
        )
        try:
            payload = _extract_json_object(
                raw, required_keys=("specificationDigest", "artifactDigest")
            )
            published = parse_published_artifact_details(payload)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "RCC did not return stable package build identities"
            ) from exc
        build = RccBuildIdentity(
            specification_digest=published.specification_digest,
            artifact_digest=published.artifact_digest,
        )
        if prepared is not None and build != prepared.build_identity:
            raise RuntimeError("prepared RCC cache identity mismatch")
        return build

    def import_action(
        self, build: RccBuildIdentity, package_dir: Path, workspace: Path
    ) -> dict[str, Any]:
        metadata_file = workspace / "action-metadata.json"
        helper = (
            "import sys\n"
            "from io import StringIO\n"
            "from actions._commands import metadata\n"
            "source, destination = sys.argv[1], sys.argv[2]\n"
            "output = StringIO()\n"
            "status = metadata(path=source, __stream__=output)\n"
            "if status != 0: raise SystemExit(72)\n"
            f"data = output.getvalue().encode('utf-8')\n"
            f"if len(data) > {MAX_COMPILER_METADATA_BYTES}: raise SystemExit(73)\n"
            "with open(destination, 'xb') as stream: stream.write(data)\n"
        )
        self._run_exec(
            build,
            package_dir,
            workspace,
            ["python", "-c", helper, str(package_dir), str(metadata_file)],
        )
        raw = metadata_file.read_bytes()
        if len(raw) > MAX_COMPILER_METADATA_BYTES:
            raise RuntimeError("Action metadata exceeds the compiler output limit")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise RuntimeError("Action metadata is not an object")
        return value

    def run_tests(
        self, build: RccBuildIdentity, package_dir: Path, workspace: Path
    ) -> None:
        helper = (
            "import io, sys, unittest\n"
            "package_dir, tests_dir = sys.argv[1], sys.argv[2]\n"
            "sys.path.insert(0, package_dir)\n"
            "suite = unittest.defaultTestLoader.discover("
            "tests_dir, pattern='test_*.py', top_level_dir=tests_dir)\n"
            "runner = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0)\n"
            "result = runner.run(suite)\n"
            "if result.testsRun == 0: raise SystemExit(74)\n"
            "raise SystemExit(0 if result.wasSuccessful() else 75)\n"
        )
        self._run_exec(
            build,
            package_dir,
            workspace,
            ["python", "-c", helper, str(package_dir), str(package_dir / "tests")],
        )

    def _run_exec(
        self,
        build: RccBuildIdentity,
        package_dir: Path,
        workspace: Path,
        command: list[str],
    ) -> None:
        if self._rcc_home is None:
            raise RuntimeError("RCC environment was not built")
        trust_carrier = self._rcc_home / "artifacts" / "v1" / "trust"
        trust_carrier.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = RccRuntimeDescriptor(
            artifact_digest=build.artifact_digest,
            provider_reference="local",
        )
        argv = build_exec_command(
            self._rcc_binary,
            descriptor,
            command,
            receipt_file=None,
            local_trust_carrier=trust_carrier,
        )
        if self._prepared_environment is not None:
            argv.insert(1, "--no-build")
        raw = self._run(argv, workspace, timeout=RCC_BUILD_TIMEOUT_SECONDS)
        try:
            value = _parse_rcc_exec_result(raw)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError("RCC execution returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise RuntimeError("RCC execution result is not an object")
        exit_code = value.get("exitCode", value.get("exit_code", 0))
        if isinstance(exit_code, bool) or exit_code != 0:
            raise RuntimeError("RCC generated-code phase failed")
        returned_digest = value.get("artifactDigest", value.get("artifact_digest"))
        if returned_digest is not None and returned_digest != build.artifact_digest:
            raise RuntimeError("RCC execution returned a different artifact identity")

    def _run(self, argv: list[str], workspace: Path, *, timeout: int) -> bytes:
        if not self._rcc_binary.is_file() or not os.access(self._rcc_binary, os.X_OK):
            raise RuntimeError("pinned bundled RCC executable is unavailable")
        try:
            completed = subprocess.run(
                argv,
                cwd=workspace,
                env=self._child_environment(workspace),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                shell=False,
                timeout=timeout,
                close_fds=True,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("bounded RCC command did not complete") from exc
        if completed.returncode != 0:
            raise RuntimeError("RCC returned a nonzero status")
        if len(completed.stdout) > MAX_RCC_OUTPUT_BYTES:
            raise RuntimeError("RCC output exceeds the compiler output limit")
        return completed.stdout

    def _create_execution_dirs(self, workspace: Path) -> None:
        if self._rcc_home is None:
            raise RuntimeError("RCC home is unavailable")
        for name in ("home", "actions-home", "tmp"):
            (workspace / name).mkdir(mode=0o700)

    def _child_environment(self, workspace: Path) -> dict[str, str]:
        if self._rcc_home is None:
            raise RuntimeError("RCC home is unavailable")
        path_entries = os.defpath.split(os.pathsep)
        if sys.platform.startswith("linux"):
            # RCC's Linux worker-capability probe resolves ldconfig through PATH.
            path_entries = ["/usr/sbin", "/sbin", *path_entries]
        environment = {
            "HOME": str(workspace / "home"),
            "PATH": os.pathsep.join(dict.fromkeys(path_entries)),
            "ROBOCORP_HOME": str(self._rcc_home),
            "ACTIONS_HOME": str(workspace / "actions-home"),
            "TMPDIR": str(workspace / "tmp"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        if self._prepared_environment is not None:
            environment["RCC_NO_BUILD"] = "1"
        return environment
