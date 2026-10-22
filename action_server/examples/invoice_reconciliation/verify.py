"""Negative probes for this owned demo only; restore grants and activation.

Run after the explicit approved execution. This is a synthetic control-plane
experiment, never an operator command for an existing Runtime deployment.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4, uuid5

import httpx2

from actions.server._models import Run, load_db
from actions.server.canvas_lifecycle import CanvasRevisionStore
from actions.server.data_queries.generated import validate_invoice_revision
from actions.server.run_outputs.models import RunAccessGrant, RunAdmission, RunPin
from actions.server.run_outputs.service import RunOutputControlPlane, RunOutputService
from actions.server.run_outputs.types import Actor, ExecutionSnapshot, OutputRef


def verify(root: Path, url: str):
    marker = json.loads((root / "demo.json").read_text())
    if (
        marker.get("version") != "actions.synthetic-reconciliation-demo/v1"
        or root.is_symlink()
        or urlsplit(url).hostname != "127.0.0.1"
    ):
        raise ValueError("owned loopback synthetic demo only")
    actor = Actor(principal_id=str(uuid5(UUID(marker["id"]), "operator")))
    receipt = {"status": "FAIL", "synthetic_only": True, "checks": {}}
    with httpx2.Client(base_url=url) as client, load_db(root / "business.sqlite") as db:
        html = client.get("/").text
        match = re.search(r"const token=(\"[^\"]+\")", html)
        token = json.loads(match[1])
        headers = {"origin": url, "x-owned-demo": token}
        state = client.get("/owned-demo/state").json()
        assert state["execution_phase"] == "completed" and state["run_count"] == 2
        before = [(run.id, run.status, run.result) for run in db.all(Run)]
        with httpx2.Client(base_url=url) as anonymous:
            assert anonymous.get("/owned-demo/state").status_code == 403
            assert (
                anonymous.post(
                    "/owned-demo/execute", json={"mode": "run"}, headers=headers
                ).status_code
                == 403
            )
        receipt["checks"]["anonymous_denied"] = True
        assert (
            client.post(
                "/owned-demo/execute",
                json={"mode": "run"},
                headers={**headers, "origin": "https://untrusted.invalid"},
            ).status_code
            == 403
        )
        receipt["checks"]["foreign_origin_denied"] = True
        pin = db.first(
            RunPin, "SELECT * FROM run_pin WHERE run_id=?", [state["query_run_id"]]
        )
        admission = db.first(
            RunAdmission,
            "SELECT * FROM run_admission WHERE id=?",
            [pin.run_admission_id],
        )
        snapshot = ExecutionSnapshot.model_validate_json(admission.snapshot_json)
        assert snapshot.canvas_application.app_id == str(
            uuid5(UUID(marker["id"]), "app")
        )
        grants = db.all(
            RunAccessGrant, where="principal_id=?", values=[actor.principal_id]
        )
        assert len(grants) == 1
        control = RunOutputControlPlane(db)
        control.revoke(actor, snapshot.deployment)
        try:
            denied = client.get("/owned-demo/state")
            assert (
                denied.status_code == 403
            ), f"revoked actor returned {denied.status_code}"
            receipt["checks"]["persisted_revocation_denied"] = True
        finally:
            control.grant(
                actor, snapshot.deployment, set(json.loads(grants[0].operations_json))
            )
        outputs = RunOutputService(db, {})

        def authorize(grant, operation):
            if (
                grant.actor != actor
                or grant.workspace_id != snapshot.workspace_id
                or grant.app_id != snapshot.canvas_application.app_id
                or grant.deployment_revision_id != snapshot.deployment.revision_id.root
            ):
                return False
            try:
                outputs._authorize(
                    actor,
                    snapshot,
                    "read" if operation in ("invoke", "read_resource") else "execute",
                )
                return True
            except Exception:
                return False

        store = CanvasRevisionStore(
            root / "generated", validator=validate_invoice_revision, authorize=authorize
        )
        old = store.pin_active(
            actor,
            snapshot.workspace_id,
            snapshot.deployment.revision_id.root,
            snapshot.canvas_application.app_id,
        )
        files = dict(old.files)
        inputs = json.loads(files["invoice.json"])
        inputs["inputs"]["min_days"] = 1
        files["invoice.json"] = json.dumps(inputs).encode()
        changed = store.stage(
            actor, old.workspace_id, old.deployment_revision_id, old.app_id, files
        )
        store.activate(
            actor,
            old.workspace_id,
            old.deployment_revision_id,
            old.app_id,
            changed.revision_id,
            expected_current=old.revision_id,
        )
        run = db.first(Run, "SELECT * FROM run WHERE id=?", [state["worker_run_id"]])
        output = OutputRef.model_validate(json.loads(run.result)["outputs"][0])
        uri = url + f"/api/workspaces/{snapshot.workspace_id}/outputs/{output.handle}"
        try:
            denied = client.post(
                "/owned-demo/download", json={"uri": uri}, headers=headers
            )
            assert denied.status_code == 404, denied.status_code
            receipt["checks"]["inactive_revision_artifact_denied"] = True
        finally:
            assert (
                store.rollback(
                    actor,
                    old.workspace_id,
                    old.deployment_revision_id,
                    old.app_id,
                    expected_current=changed.revision_id,
                )
                == old.revision_id
            )
        restored = client.post(
            "/owned-demo/download", json={"uri": uri}, headers=headers
        )
        assert restored.status_code == 200
        receipt["checks"]["rollback_restores_same_artifact"] = True
        receipt["artifact_sha256"] = hashlib.sha256(restored.content).hexdigest()
        wrong = url + f"/api/workspaces/{uuid4()}/outputs/{output.handle}"
        assert (
            client.post(
                "/owned-demo/download", json={"uri": wrong}, headers=headers
            ).status_code
            == 403
        )
        receipt["checks"]["foreign_workspace_denied"] = True
        after = [(run.id, run.status, run.result) for run in db.all(Run)]
        assert sorted(before) == sorted(after)
        receipt["checks"]["business_run_audit_unchanged"] = True
        receipt["state"] = client.get("/owned-demo/state").json()
        receipt["status"] = "PASS"
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.state, args.url.rstrip("/"))
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "checks": result["checks"]}))
