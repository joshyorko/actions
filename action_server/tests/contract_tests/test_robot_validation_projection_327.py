"""SQL-only validation-carrier checks, not Robot execution qualification."""
# Imported pytest fixtures retain their original dependency graph.
# ruff: noqa: F811
import json
from copy import deepcopy
from uuid import uuid4

import pytest
from action_server_tests.test_robot_package_admission import admitted as admitted
from action_server_tests.test_robot_package_admission import (
    disable_feedback as disable_feedback,
)
from action_server_tests.test_robot_runtime_runner import case as case

from actions.server.foundry import robot_retained_projection as projection
from actions.server.foundry.models import FoundryPackageRevision
from actions.server.foundry.robot_package_admission import canonical, digest
from actions.server.run_outputs.service import FenceRejected

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def carrier(identity):
    value = {
        "schemaVersion": "actions.robot-validation-storage/v1",
        "validation": "passed",
    }
    receipt = dict(
        identity,
        schemaVersion="actions.robot-dryrun-validation/v1",
        validationKind="robot-dryrun",
        validation="passed",
        execution="not-qualified",
        exitCode=0,
    )
    for name, field in (
        ("stdout", "stdoutDigest"),
        ("stderr", "stderrDigest"),
        ("output_xml", "outputXmlDigest"),
        ("rcc_receipt", "rccReceiptDigest"),
    ):
        if name == "rcc_receipt" and identity["runtimeKind"] == "direct":
            value[name] = receipt[field] = None
        else:
            raw = name.encode()
            value[name] = dict(
                object_ref=str(uuid4()), digest=digest(raw), size=len(raw)
            )
            receipt[field] = digest(raw)
    value["receipt"] = canonical(receipt).decode()
    return value


@pytest.fixture(params=["direct", "rcc"])
def metadata(request):
    identity = dict(
        packageRevisionId="sha256:" + "a" * 64,
        sourceDigest="sha256:" + "b" * 64,
        planDigest="sha256:" + "c" * 64,
        runtimeKind=request.param,
        suitePath="task.robot",
        suiteName="Task",
        taskName="Owned",
        robotVersion="7.4.2",
        pythonVersion=[3, 12],
        platformTag="linux-x86_64",
    )
    return identity, carrier(identity)


def test_validation_projection_read_sql_only(case, monkeypatch):
    c = case
    row = c.db.all(FoundryPackageRevision)[0]
    manifest = json.loads(row.manifest_json)
    builder, plan = json.loads(manifest["robotManifest"]), json.loads(manifest["plan"])
    identity = dict(
        packageRevisionId=manifest["revisionDigest"],
        sourceDigest=row.source_artifact_digest,
        planDigest=builder["planDigest"],
        runtimeKind=plan["runtime_kind"],
        suitePath=builder["suitePath"],
        suiteName=builder["suiteName"],
        taskName=builder["taskName"],
        robotVersion=plan["robot_version"],
        pythonVersion=plan["python_version"],
        platformTag=plan["platform_tag"],
    )
    admission = json.loads(row.build_evidence_json)
    historical = projection.retained_robot_projection(c.db, c.service.snapshot)
    admission["validation"] = carrier(identity)
    with c.db.transaction():
        c.db.update_by_id(
            FoundryPackageRevision,
            row.id,
            {"build_evidence_json": canonical(admission).decode()},
        )

    def forbidden(*args, **kwargs):
        pytest.fail("provider/registry I/O in SQL metadata projection")

    monkeypatch.setattr(c.provider, "open", forbidden)
    monkeypatch.setattr(c.registry, "load_verified", forbidden)
    monkeypatch.setattr(c.registry, "schema_for", forbidden)
    with c.db.transaction():
        assert (
            projection.retained_robot_projection(c.db, c.service.snapshot) == historical
        )
        admission["validation"]["receipt"] = "{}"
        c.db.update_by_id(
            FoundryPackageRevision,
            row.id,
            {"build_evidence_json": canonical(admission).decode()},
        )
        with pytest.raises(FenceRejected):
            projection.retained_robot_projection(c.db, c.service.snapshot)


def test_closed_validation_metadata(metadata):
    identity, value = metadata
    projection._validation_metadata(value, identity)
    value["validation"] = "failed"
    receipt = json.loads(value["receipt"])
    receipt.update(validation="failed", exitCode=1)
    value["receipt"] = canonical(receipt).decode()
    projection._validation_metadata(value, identity)


@pytest.mark.parametrize(
    "field",
    [
        "packageRevisionId",
        "sourceDigest",
        "planDigest",
        "runtimeKind",
        "suitePath",
        "suiteName",
        "taskName",
        "robotVersion",
        "pythonVersion",
        "platformTag",
        "schemaVersion",
        "validationKind",
        "validation",
        "execution",
        "exitCode",
        "stdoutDigest",
        "stderrDigest",
        "outputXmlDigest",
        "rccReceiptDigest",
    ],
)
def test_receipt_preimage_mutation_rejected(metadata, field):
    identity, value = metadata
    receipt = json.loads(value["receipt"])
    receipt[field] = "changed"
    value["receipt"] = canonical(receipt).decode()
    with pytest.raises(ValueError):
        projection._validation_metadata(value, identity)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "extra",
        "missing",
        "noncanonical",
        "nonfinite",
        "exit-bool",
        "exit-float",
        "python-bool",
        "python-float",
        "receipt-large",
        "receipt-null",
        "carrier-extra",
        "carrier-missing",
        "carrier-validation",
        "rcc-presence",
        "xml-empty",
        "seal-extra",
        "seal-bool",
        "seal-float",
        "seal-large",
        "seal-digest",
    ],
)
def test_closed_carrier_mutations_rejected(metadata, mutation):
    identity, original = metadata
    value = deepcopy(original)
    receipt = json.loads(value["receipt"])
    if mutation == "duplicate":
        value["receipt"] = value["receipt"][:-1] + ',"exitCode":0}'
    elif mutation == "noncanonical":
        value["receipt"] = " " + value["receipt"]
    elif mutation == "nonfinite":
        value["receipt"] = value["receipt"].replace('"exitCode":0', '"exitCode":NaN')
    elif mutation == "receipt-large":
        value["receipt"] = " " * 16385
    elif mutation == "receipt-null":
        value["receipt"] = None
    elif mutation.startswith("carrier-"):
        if mutation == "carrier-extra":
            value["extra"] = None
        elif mutation == "carrier-missing":
            del value["stdout"]
        else:
            value["validation"] = "failed"
    elif mutation == "rcc-presence":
        value["rcc_receipt"] = value["stdout"] if value["rcc_receipt"] is None else None
    elif mutation == "xml-empty":
        value["output_xml"]["size"] = 0
    elif mutation.startswith("seal-"):
        if mutation == "seal-extra":
            value["stdout"]["extra"] = None
        elif mutation == "seal-bool":
            value["stdout"]["size"] = True
        elif mutation == "seal-float":
            value["stdout"]["size"] = 1.0
        elif mutation == "seal-large":
            value["stdout"]["size"] = 256 * 1024 + 1
        else:
            value["stdout"]["digest"] = "sha256:" + "f" * 64
    else:
        if mutation == "extra":
            receipt["extra"] = None
        elif mutation == "missing":
            del receipt["exitCode"]
        elif mutation == "exit-bool":
            receipt["exitCode"] = False
        elif mutation == "exit-float":
            receipt["exitCode"] = 0.0
        elif mutation == "python-bool":
            receipt["pythonVersion"] = [True, 12]
        elif mutation == "python-float":
            receipt["pythonVersion"] = [3.0, 12]
        # Keep float spelling so the decoder must enforce types before JCS.
        value["receipt"] = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    with pytest.raises(ValueError):
        projection._validation_metadata(value, identity)
