"""Closed sealed validation diagnostics; consistency is not issuance authority."""
from __future__ import annotations

from actions.server.foundry.robot_package_admission import digest
from actions.server.foundry.robot_validation import (
    LOG_LIMIT,
    XML_LIMIT,
    RobotValidationResult,
    verify_robot_validation,
)
from actions.server.run_outputs.types import SealReceipt

_FIELDS = {
    "stdout": LOG_LIMIT,
    "stderr": LOG_LIMIT,
    "output_xml": XML_LIMIT,
    "rcc_receipt": XML_LIMIT,
}
_SCHEMA = "actions.robot-validation-storage/v1"


def preimage(result: RobotValidationResult) -> tuple:
    return tuple(
        getattr(result, name)
        for name in (
            "receipt_json",
            "stdout",
            "stderr",
            "output_xml",
            "rcc_receipt",
            "validation",
            "validation_kind",
            "execution",
        )
    )


def stage_validation(provider, package, result):
    verify_robot_validation(package, result)
    staged = []
    carrier = {
        "schemaVersion": _SCHEMA,
        "receipt": result.receipt_json.decode("utf-8"),
        "validation": result.validation,
    }
    try:
        for name in _FIELDS:
            content = getattr(result, name)
            if content is None:
                carrier[name] = None
                continue
            item = provider.stage(
                content[i : i + 65536] for i in range(0, len(content), 65536)
            )
            staged.append(item)
            if item.receipt.digest != digest(content) or item.receipt.size != len(
                content
            ):
                raise ValueError("Robot validation stage differs")
            carrier[name] = item.receipt.model_dump(mode="json")
        return carrier, staged
    except BaseException:
        for item in staged:
            provider.discard(item)
        raise


def load_validation(provider, package, carrier):
    if (
        not isinstance(carrier, dict)
        or set(carrier) != {"schemaVersion", "receipt", "validation", *_FIELDS}
        or carrier["schemaVersion"] != _SCHEMA
        or not isinstance(carrier["receipt"], str)
        or len(carrier["receipt"].encode()) > 16384
        or carrier["validation"] not in ("passed", "failed")
    ):
        raise ValueError("closed Robot validation carrier required")
    values = {}
    for name, limit in _FIELDS.items():
        value = carrier[name]
        if value is None and name == "rcc_receipt":
            values[name] = None
            continue
        seal = SealReceipt.model_validate(value)
        if seal.model_dump(mode="json") != value or seal.size > limit:
            raise ValueError("Robot validation seal bound differs")
        with provider.open(seal.object_ref, seal.digest, seal.size) as reader:
            content = reader.read(seal.size + 1)
        if len(content) != seal.size or digest(content) != seal.digest:
            raise ValueError("Robot validation bytes differ")
        values[name] = content
    result = RobotValidationResult(
        carrier["receipt"].encode(), **values, validation=carrier["validation"]
    )
    return verify_robot_validation(package, result)
