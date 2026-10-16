"""Recovery keeps original release identity and requires independent exact copies."""

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parents[2]
SCRIPTS = ROOT / "action_server/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "recovery_button", SCRIPTS / "runtime_release_button.py"
)
button = importlib.util.module_from_spec(spec)
spec.loader.exec_module(button)


def artifact(run, role, identity):
    return {
        "id": identity,
        "name": f"runtime-release-{role}-{run}-1",
        "digest": "sha256:" + str(identity % 10) * 64,
        "size_in_bytes": 100 + identity,
        "expired": False,
        "created_at": "2026-10-16T00:00:00Z",
        "expires_at": "2027-01-14T00:00:00Z",
        "workflow_run": {"id": run},
    }


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    members = {"pypi/a.whl": b"wheel", "pypi/b.tar.gz": b"sdist"}
    members.update(
        {
            f"native/actions-runtime-1.0.4-{suffix}": suffix.encode()
            for suffix in ("linux64", "macos-arm64", "windows64.exe", "sha256.txt")
        }
    )
    for name, data in members.items():
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    manifest = {
        "schema_version": 1,
        "repository": button.REPOSITORY,
        "version": "1.0.4",
        "source_sha": "a" * 40,
        "qualification_sha": "a" * 40,
        "controller_sha": "c" * 40,
        "tree": "b" * 40,
        "preparation_run_id": 123,
        "preparation_run_attempt": 1,
        "files": {
            name: {"sha256": button.sha256(bundle / name), "size": len(data)}
            for name, data in members.items()
        },
    }
    (bundle / button.MANIFEST).write_text(json.dumps(manifest))
    digest = button.sha256(bundle / button.MANIFEST)
    record = {
        "manifest_sha256": digest,
        "source_sha": manifest["source_sha"],
        "version": "1.0.4",
        "preparation_run_id": 123,
        "original_archive_sha256": "f" * 64,
        "backups": [],
    }
    runs, artifacts = {}, {}
    for run_id, head in [(201, "d" * 40), (202, "e" * 40)]:
        runs[run_id] = {
            "id": run_id,
            "run_attempt": 1,
            "head_sha": head,
            "head_branch": "backup/runtime-release-bundles",
            "path": ".github/workflows/runtime-release-backup.yml",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": button.REPOSITORY},
            "head_repository": {"full_name": button.REPOSITORY},
        }
        artifacts[run_id] = [
            artifact(run_id, "bundle", run_id * 10 + 1),
            artifact(run_id, "archive", run_id * 10 + 2),
        ]
        record["backups"].append(
            {
                "run_id": run_id,
                "head_sha": head,
                "bundle": {
                    k: artifacts[run_id][0][k]
                    for k in ("id", "digest", "size_in_bytes")
                },
                "archive": {
                    k: artifacts[run_id][1][k]
                    for k in ("id", "digest", "size_in_bytes")
                },
            }
        )
    registry_path = tmp_path / "action_server/release-bundle-backups.json"
    registry_path.parent.mkdir()

    def save_record():
        registry_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repository": button.REPOSITORY,
                    "bundles": [record],
                }
            )
        )

    save_record()
    requests = []

    def api(endpoint, **kwargs):
        assert kwargs.get("method", "GET") == "GET", "recovery attempted a remote write"
        requests.append(endpoint)
        run_id = int(endpoint.split("/runs/")[1].split("/")[0])
        if run_id == 123:
            return {
                "id": 123,
                "run_attempt": 1,
                "head_sha": manifest["controller_sha"],
                "head_branch": "community",
                "path": button.PREPARE_WORKFLOW,
                "event": "workflow_dispatch",
                "status": "completed",
                "conclusion": "success",
                "repository": {"full_name": button.REPOSITORY},
                "head_repository": {"full_name": button.REPOSITORY},
            }
        return copy.deepcopy(runs.get(run_id))

    def pages(endpoint, key):
        assert key == "artifacts"
        run_id = int(endpoint.split("/runs/")[1].split("/")[0])
        return copy.deepcopy(artifacts[run_id])

    monkeypatch.setattr(button, "api", api)
    monkeypatch.setattr(button, "pages", pages)
    monkeypatch.setattr(button, "controller", lambda *args: None)
    monkeypatch.setattr(button, "check_source", lambda *args: manifest["tree"])
    monkeypatch.setattr(button, "verify_artifacts", lambda *args: None)
    monkeypatch.setattr(button.subprocess, "run", lambda *args, **kwargs: None)
    args = SimpleNamespace(
        root=tmp_path,
        bundle=bundle,
        manifest_sha256=digest,
        preparation_run_id=201,
        source_sha=manifest["source_sha"],
        version="1.0.4",
    )
    return SimpleNamespace(
        args=args,
        manifest=manifest,
        record=record,
        save_record=save_record,
        runs=runs,
        artifacts=artifacts,
        requests=requests,
        registry=registry_path,
    )


def test_backup_transport_keeps_original_preparation_and_release_owner(recovery):
    result = button.verify(recovery.args)
    assert result == recovery.manifest
    assert result["preparation_run_id"] == 123
    assert "Preparation run: 123" in button.release_body(
        result, recovery.args.manifest_sha256
    )
    assert any(
        endpoint.endswith("/runs/123/attempts/1") for endpoint in recovery.requests
    )
    assert not any(endpoint.endswith("/runs/123") for endpoint in recovery.requests)


def test_original_transport_also_requires_two_registered_backups(recovery):
    recovery.args.preparation_run_id = 123
    recovery.artifacts[202].clear()
    with pytest.raises(button.ReleaseError, match="two independent healthy backups"):
        button.verify(recovery.args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_sha", "9" * 40),
        ("version", "1.0.5"),
        ("preparation_run_id", 456),
        ("manifest_sha256", "0" * 64),
    ],
)
def test_registry_cannot_admit_another_release(recovery, field, value):
    recovery.record[field] = value
    recovery.save_record()
    with pytest.raises(button.ReleaseError, match="recovery registry"):
        button.verify(recovery.args)


def test_missing_registry_does_not_fall_back_to_unprotected_publication(recovery):
    recovery.registry.unlink()
    with pytest.raises(button.ReleaseError, match="recovery registry"):
        button.verify(recovery.args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("path", ".github/workflows/other.yml"),
        ("head_branch", "community"),
        ("head_sha", "0" * 40),
        ("head_repository", {"full_name": "fork/actions"}),
        ("conclusion", "failure"),
        ("run_attempt", 2),
        ("event", "pull_request_target"),
    ],
)
def test_backup_run_identity_is_not_interchangeable(recovery, field, value):
    recovery.runs[201][field] = value
    with pytest.raises(button.ReleaseError, match="backup run identity"):
        button.verify(recovery.args)


@pytest.mark.parametrize("mutation", ["digest", "size", "id", "duplicate", "expired"])
def test_backup_artifact_metadata_is_exact_and_current(recovery, mutation):
    item = recovery.artifacts[202][1]
    if mutation == "digest":
        item["digest"] = "sha256:" + "0" * 64
    if mutation == "size":
        item["size_in_bytes"] += 1
    if mutation == "id":
        item["id"] += 1
    if mutation == "duplicate":
        recovery.artifacts[202].append(dict(item))
    if mutation == "expired":
        item["expired"] = True
    with pytest.raises(button.ReleaseError):
        button.verify(recovery.args)


def test_distinct_artifacts_in_one_run_do_not_count_as_independent_backups(recovery):
    recovery.record["backups"][1] = copy.deepcopy(recovery.record["backups"][0])
    recovery.save_record()
    with pytest.raises(button.ReleaseError, match="distinct backup runs"):
        button.verify(recovery.args)


def test_valid_recovery_cannot_bypass_original_member_integrity(recovery):
    (recovery.args.bundle / "pypi/a.whl").write_bytes(b"other")
    with pytest.raises(button.ReleaseError, match="bundle digest mismatch"):
        button.verify(recovery.args)
