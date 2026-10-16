"""Qualification-only orchestration; never publish or touch the protected owner run."""
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import runtime_release_qualification_support as support

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "action_server/scripts"))
button = importlib.import_module("runtime_release_button")

QA_BRANCH = "qualification/runtime-release-recovery-20261016"
QA_WORKFLOW = ".github/workflows/runtime-release-recovery-qualification.yml"
CREATION_CONTROLLER = 38977026656
CREATION_SHA = "89f27ea4283dc8d7e123bb217a2fba1d36e64716"

PROTECTED_OWNER = 38951733318
# Created by the successful qualification run38977026656; never infer another target.
DISPOSABLE_PREPARATION = 38977611441
REPORT = Path("recovery-qualification-report.json")


def authorize_disposable(proof, manifest, digest, request):
    run_id = proof.get("disposable_preparation_run_id")
    support.require(
        run_id != PROTECTED_OWNER, "protected owner preparation cannot be destroyed"
    )
    support.require(
        run_id == DISPOSABLE_PREPARATION,
        "only the explicitly created rehearsal may be destroyed",
    )
    support.require(
        isinstance(run_id, int)
        and not isinstance(run_id, bool)
        and run_id > 0
        and proof.get("status") == "PASS"
        and proof.get("purpose") == "disposable-recovery-rehearsal"
        and isinstance(proof.get("creation_controller_run_id"), int)
        and proof["creation_controller_run_id"] > 0
        and proof["creation_controller_run_id"] == CREATION_CONTROLLER
        and proof.get("creation_controller_sha") == CREATION_SHA
        and support.re.fullmatch(
            r"[0-9a-f]{40}", proof.get("creation_controller_sha", "")
        ),
        "fresh explicit disposable creation receipt required",
    )
    support.dispatch_input(
        "prepare",
        request["source_sha"],
        request["qualification_sha"],
        request["version"],
    )
    bundles = proof.get("bundles", [])
    support.require(len(bundles) == 1, "exactly one disposable bundle required")
    bundle = bundles[0]
    support.require(
        bundle.get("label") == "disposable"
        and bundle.get("run_id") == run_id
        and bundle.get("manifest_sha256") == digest
        and support.re.fullmatch(r"[0-9a-f]{64}", digest)
        and manifest.get("preparation_run_id") == run_id
        and manifest.get("preparation_run_attempt") == 1,
        "disposable manifest/run/digest identity mismatch",
    )
    for field in ("source_sha", "qualification_sha", "version"):
        support.require(
            manifest.get(field) == bundle.get(field) == request[field],
            "disposable source/version identity mismatch",
        )
    return run_id


def verify_creation(proof):
    created = support.api(
        f"repos/{support.REPO}/actions/runs/{CREATION_CONTROLLER}/attempts/1"
    )
    support.require(
        created.get("id") == CREATION_CONTROLLER
        and created.get("head_sha") == CREATION_SHA == proof["creation_controller_sha"]
        and created.get("run_attempt") == 1
        and created.get("path") == QA_WORKFLOW
        and created.get("head_branch") == QA_BRANCH
        and created.get("event") == "push"
        and created.get("status") == "completed"
        and created.get("conclusion") == "success"
        and created.get("repository", {}).get("full_name") == support.REPO
        and created.get("head_repository", {}).get("full_name") == support.REPO,
        "disposable creation controller identity mismatch",
    )


def latest_disposable(manifest):
    run = support.api(f"repos/{support.REPO}/actions/runs/{DISPOSABLE_PREPARATION}")
    support.require(
        run.get("id") == DISPOSABLE_PREPARATION
        and run.get("run_attempt") == 1
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and run.get("path") == ".github/workflows/runtime-release-prepare.yml"
        and run.get("event") == "workflow_dispatch"
        and run.get("head_branch") == "community"
        and run.get("head_sha") == manifest["controller_sha"]
        and run.get("repository", {}).get("full_name") == support.REPO
        and run.get("head_repository", {}).get("full_name") == support.REPO,
        "disposable preparation is already rerun or changed; inspect actual outcome before another request",
    )
    return run


def destroy_disposable(report, request, proof, manifest, digest):
    run_id = authorize_disposable(proof, manifest, digest, request)
    verify_creation(proof)
    latest_disposable(manifest)
    record = button.verify_recovery(ROOT, digest, manifest, run_id)
    support.require(
        "sha256:" + record["original_archive_sha256"]
        == proof["bundles"][0]["artifact_digest"],
        "disposable backup ZIP does not match its created original artifact",
    )
    original = support.api(
        f"repos/{support.REPO}/actions/artifacts/{proof['bundles'][0]['artifact_id']}"
    )
    support.require(
        original.get("id") == proof["bundles"][0]["artifact_id"]
        and original.get("digest") == proof["bundles"][0]["artifact_digest"]
        and original.get("workflow_run", {}).get("id") == run_id,
        "disposable original artifact changed before the destructive test",
    )
    # Verify again after downloading the backups. Never repeat an existing rerun.
    latest_disposable(manifest)
    current = support.api(f"repos/{support.REPO}/git/ref/heads/community")
    support.require(
        current["object"]["sha"] == manifest["controller_sha"],
        "community moved; do not replay the original preparation controller",
    )
    endpoint = f"repos/{support.REPO}/actions/runs/{DISPOSABLE_PREPARATION}/rerun"
    support.ALLOWED_WRITES.add(endpoint)
    report["destructive_operation"] = {
        "target_run_id": run_id,
        "expected_previous_attempt": 1,
        "requested_attempt": 2,
        "outcome": "request uncertain",
        "verified_backup_runs": [item["run_id"] for item in record["backups"]],
    }
    support.snapshot(report)
    # Exactly one POST; an exception preserves uncertainty and is never retried here.
    support.api(endpoint, method="POST")
    report["destructive_operation"]["outcome"] = "accepted"
    support.snapshot(report)
    run = support.wait_run(run_id, attempt=2)
    support.result(report, "disposable-preparation-rerun", run)
    support.require(
        run["conclusion"] == "failure", "disposable rerun must refuse rebuilding"
    )
    support.assert_log_marker(run_id, "prepare", "never rerun preparation")
    support.require(
        support.api(
            f"repos/{support.REPO}/actions/artifacts/{original['id']}", missing=True
        )
        is None,
        "disposable original artifact still exists; loss was not demonstrated",
    )
    attempt = support.api(f"repos/{support.REPO}/actions/runs/{run_id}/attempts/1")
    support.require(
        attempt["conclusion"] == "success", "original successful attempt identity lost"
    )
    button.verify_recovery(ROOT, digest, manifest, run_id)
    report["destructive_operation"].update(
        outcome="original artifact absent; original attempt successful; both backups readable",
        original_artifact_id=original["id"],
    )
    support.snapshot(report)


def qa_controller():
    support.require(
        os.environ.get("GITHUB_REPOSITORY") == support.REPO
        and os.environ.get("GITHUB_REF") == f"refs/heads/{QA_BRANCH}"
        and os.environ.get("GITHUB_WORKFLOW_REF")
        == f"{support.REPO}/{QA_WORKFLOW}@refs/heads/{QA_BRANCH}"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1",
        "use a fresh current qualification controller; never rerun a destructive request",
    )
    button.git(
        ROOT,
        "fetch",
        "--no-tags",
        "origin",
        f"refs/heads/{QA_BRANCH}:refs/remotes/origin/{QA_BRANCH}",
    )
    support.require(
        button.git(ROOT, "rev-parse", "HEAD")
        == os.environ.get("GITHUB_WORKFLOW_SHA")
        == button.git(ROOT, "rev-parse", f"origin/{QA_BRANCH}"),
        "qualification controller is stale",
    )


def owner_snapshot():
    run = support.api(f"repos/{support.REPO}/actions/runs/{PROTECTED_OWNER}")
    items = support.api(
        f"repos/{support.REPO}/actions/runs/{PROTECTED_OWNER}/artifacts?per_page=100"
    )["artifacts"]
    expected = [item for item in items if item["id"] == 12069321636]
    support.require(
        run["run_attempt"] == 1
        and run["conclusion"] == "success"
        and len(expected) == 1,
        "protected owner preparation changed",
    )
    artifact = expected[0]
    support.require(
        artifact["digest"]
        == "sha256:bbe3d066fb082c1dc61a8916af549bf9a7b66369f36866a2b37a8256a95524e5"
        and not artifact["expired"],
        "protected owner artifact changed",
    )
    return {
        "run_id": PROTECTED_OWNER,
        "run_attempt": run["run_attempt"],
        "artifact_id": artifact["id"],
        "artifact_digest": artifact["digest"],
        "size_in_bytes": artifact["size_in_bytes"],
    }


def verify_tested_code(request):
    revision = request["repair_source_sha"]
    support.require(
        support.re.fullmatch(r"[0-9a-f]{40}", revision), "exact repair source required"
    )
    button.git(ROOT, "fetch", "--no-tags", "origin", revision)
    result = {}
    for path in (
        "action_server/scripts/runtime_release_button.py",
        "action_server/scripts/runtime_release_backup.py",
        "action_server/scripts/runtime_release_backup_workflow.yml",
    ):
        expected = button.git(ROOT, "rev-parse", f"{revision}:{path}")
        support.require(
            button.git(ROOT, "hash-object", str(ROOT / path)) == expected,
            "qualification code differs from reviewable repair",
        )
        result[path] = expected
    original = json.loads(
        button.git(
            ROOT, "show", f"{revision}:action_server/release-bundle-backups.json"
        )
    )
    registry = json.loads((ROOT / button.RECOVERY_REGISTRY).read_text())
    owner = [
        row
        for row in registry["bundles"]
        if row["preparation_run_id"] == PROTECTED_OWNER
    ]
    support.require(
        owner == original["bundles"], "qualification altered reviewed owner registry"
    )
    return result


def expect_refusal(report, label, function, marker):
    try:
        function()
    except button.ReleaseError as error:
        support.require(
            marker in str(error),
            f"negative control {label} failed for unexpected reason: {error}",
        )
        report.setdefault("negative_controls", []).append(
            {"label": label, "result": "PASS", "refusal": str(error)}
        )
        support.snapshot(report)
        return
    raise support.QualificationError(f"negative control {label} unexpectedly passed")


def negative_controls(report, args, manifest):
    for label, changes, marker in [
        (
            "wrong-manifest-digest",
            {
                "manifest_sha256": ("0" if args.manifest_sha256[0] != "0" else "1")
                + args.manifest_sha256[1:]
            },
            "reviewed manifest digest mismatch",
        ),
        (
            "wrong-source",
            {"source_sha": "f" * 40},
            "reviewed preparation inputs mismatch",
        ),
        ("wrong-version", {"version": "1.0.5"}, "reviewed preparation inputs mismatch"),
        (
            "unregistered-transport",
            {"preparation_run_id": 999999999999},
            "transport is not in the reviewed recovery registry",
        ),
    ]:
        altered = SimpleNamespace(**(vars(args) | changes))
        expect_refusal(report, label, lambda: button.verify_bundle(altered), marker)
    policy = ROOT / button.RECOVERY_REGISTRY
    original_policy = policy.read_bytes()
    try:
        rows = json.loads(original_policy)
        row = next(
            row
            for row in rows["bundles"]
            if row["manifest_sha256"] == args.manifest_sha256
        )
        row["backups"][0]["archive"]["digest"] = "sha256:" + "0" * 64
        policy.write_text(json.dumps(rows))
        expect_refusal(
            report,
            "wrong-registered-artifact",
            lambda: button.verify_bundle(args),
            "artifact metadata differs",
        )
        rows = json.loads(original_policy)
        row = next(
            row
            for row in rows["bundles"]
            if row["manifest_sha256"] == args.manifest_sha256
        )
        row["backups"] = row["backups"][:1]
        policy.write_text(json.dumps(rows))
        expect_refusal(
            report,
            "one-copy-cannot-authorize-publication",
            lambda: button.verify_bundle(args),
            "two independent healthy backups",
        )
    finally:
        policy.write_bytes(original_policy)
    member = next(
        name
        for name in manifest["files"]
        if name.startswith("pypi/") and name.endswith(".whl")
    )
    path = args.bundle / member
    with path.open("rb+") as stream:
        original = stream.read(1)
        stream.seek(0)
        stream.write(bytes([original[0] ^ 1]))
    try:
        expect_refusal(
            report,
            "changed-member-same-size",
            lambda: button.verify_bundle(args),
            "bundle digest mismatch",
        )
    finally:
        with path.open("rb+") as stream:
            stream.write(original)
    path = args.bundle / button.MANIFEST
    original = path.read_bytes()
    path.write_bytes(original + b"\n")
    try:
        expect_refusal(
            report,
            "changed-original-manifest",
            lambda: button.verify_bundle(args),
            "reviewed manifest digest mismatch",
        )
    finally:
        path.write_bytes(original)
    button.verify_bundle(args)


def validate_transport(report, label, transport, manifest, digest, *, negatives=False):
    with tempfile.TemporaryDirectory(prefix="runtime-recovery-qualified-") as temporary:
        destination = Path(temporary) / "bundle"
        metadata = button.download(
            {"id": transport}, f"runtime-release-bundle-{transport}-1", destination
        )
        args = SimpleNamespace(
            root=ROOT,
            bundle=destination,
            manifest_sha256=digest,
            preparation_run_id=transport,
            source_sha=manifest["source_sha"],
            version=manifest["version"],
        )
        verified = button.verify_bundle(args)
        support.require(verified == manifest, "recovered original manifest changed")
        release, tag = button.release_state(manifest["version"])
        if release is None:
            support.require(
                tag is None or tag == manifest["source_sha"],
                "existing tag targets another source",
            )
        else:
            button.reconcile_release(manifest, digest, release, tag)
        button.reconcile_pypi(
            manifest, button.pypi_files(manifest["version"]), owned=True
        )
        if negatives:
            negative_controls(report, args, manifest)
        report.setdefault("transport_validations", []).append(
            {
                "label": label,
                "transport_run_id": transport,
                "preparation_run_id": manifest["preparation_run_id"],
                "manifest_sha256": digest,
                "source_sha": manifest["source_sha"],
                "verified_members": len(manifest["files"]),
                "source_artifact": metadata,
                "result": "PASS",
                "publication_performed": False,
            }
        )
        support.snapshot(report)


def verify_disposable_loss(proof, manifest, digest, request):
    authorize_disposable(proof, manifest, digest, request)
    verify_creation(proof)
    run = support.api(f"repos/{support.REPO}/actions/runs/{DISPOSABLE_PREPARATION}")
    support.require(
        run["run_attempt"] == 2 and run["conclusion"] == "failure",
        "expected disposable rerun2 outcome absent; inspect uncertain state",
    )
    support.assert_log_marker(
        DISPOSABLE_PREPARATION, "prepare", "never rerun preparation"
    )
    support.require(
        support.api(
            f"repos/{support.REPO}/actions/artifacts/{proof['bundles'][0]['artifact_id']}",
            missing=True,
        )
        is None,
        "disposable original is still available",
    )
    original = support.api(
        f"repos/{support.REPO}/actions/runs/{DISPOSABLE_PREPARATION}/attempts/1"
    )
    support.require(
        original["conclusion"] == "success", "original preparation success lost"
    )
    button.verify_recovery(ROOT, digest, manifest, DISPOSABLE_PREPARATION)


def main():
    support.REPORT = REPORT
    request = json.loads(
        (ROOT / "scripts/runtime-release-recovery-request.json").read_text()
    )
    operation = request["operation"]
    support.require(
        operation in {"qualify-recovery", "verify-after-loss"},
        "unsupported qualification operation",
    )
    qa_controller()
    report = {
        "status": "RUNNING",
        "purpose": request["purpose"],
        "dispatches": [],
        "runs": [],
        "bundles": [],
        "publication_performed": False,
        "protected_owner_preparation": PROTECTED_OWNER,
        "qualification_controller_run_id": int(os.environ["GITHUB_RUN_ID"]),
        "qualification_controller_sha": os.environ["GITHUB_SHA"],
        "operation": operation,
    }
    support.snapshot(report)
    before = owner_snapshot()
    report["owner_before"] = before
    try:
        support.publication_absent(request["version"])
        report["repair_source_sha"] = request["repair_source_sha"]
        report["tested_code_blobs"] = verify_tested_code(request)
        owner_path = ROOT / "scripts/owner-release-bundle.json"
        owner = json.loads(owner_path.read_text())
        owner_digest = button.sha256(owner_path)
        support.require(
            owner["preparation_run_id"] == PROTECTED_OWNER
            and owner_digest
            == "1a77f6c8e09869d6bd45df1b14e6a9ce3f908bcf09351b76cee26a209504878a",
            "owner manifest changed",
        )
        owner_record = button.recovery_record(ROOT, owner_digest, owner)
        for transport in [
            PROTECTED_OWNER,
            *[row["run_id"] for row in owner_record["backups"]],
        ]:
            validate_transport(
                report, "owner-original-or-backup", transport, owner, owner_digest
            )
        proof = json.loads(
            (ROOT / "scripts/disposable-preparation-proof.json").read_text()
        )
        manifest_path = ROOT / "scripts/disposable-release-bundle.json"
        manifest = json.loads(manifest_path.read_text())
        digest = button.sha256(manifest_path)
        if operation == "qualify-recovery":
            destroy_disposable(report, request, proof, manifest, digest)
        else:
            verify_disposable_loss(proof, manifest, digest, request)
        record = button.recovery_record(ROOT, digest, manifest)
        with tempfile.TemporaryDirectory(prefix="missing-original-") as temporary:
            expect_refusal(
                report,
                "lost-original-artifact-refused",
                lambda: button.download(
                    {"id": DISPOSABLE_PREPARATION},
                    f"runtime-release-bundle-{DISPOSABLE_PREPARATION}-1",
                    Path(temporary) / "bundle",
                ),
                "missing, duplicated, or expired artifact",
            )
        for index, backup in enumerate(record["backups"]):
            validate_transport(
                report,
                "disposable-recovered-after-original-loss",
                backup["run_id"],
                manifest,
                digest,
                negatives=index == 0,
            )
        report["recovery_after_original_loss"] = "PASS"
        report[
            "default_button_activation"
        ] = "UNRUN until the reviewed repair is merged; no production controller guard was bypassed"
        support.publication_absent(request["version"])
        after = owner_snapshot()
        support.require(after == before, "protected owner changed during qualification")
        report.update(status="PASS", owner_after=after, protected_owner_unchanged=True)
    except Exception as error:
        report.update(
            status="FAILED", error_type=type(error).__name__, error=str(error)
        )
        raise
    finally:
        support.snapshot(report)


if __name__ == "__main__":
    main()
