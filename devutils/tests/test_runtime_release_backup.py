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
    import hashlib
    import io
    import zipfile

    original_stream = io.BytesIO()
    with zipfile.ZipFile(original_stream, "w") as z:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(bundle).as_posix())
    original_zip = original_stream.getvalue()
    record["original_archive_sha256"] = hashlib.sha256(original_zip).hexdigest()
    downloads = {}
    for backup in record["backups"]:
        receipt = {
            key: record[key]
            for key in (
                "preparation_run_id",
                "source_sha",
                "version",
                "manifest_sha256",
                "original_archive_sha256",
            )
        }
        receipt.update(
            schema_version=1,
            repository=button.REPOSITORY,
            controller_sha=backup["head_sha"],
        )
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            z.writestr("original-bundle.zip", original_zip)
            z.writestr("backup-receipt.json", json.dumps(receipt))
        content = stream.getvalue()
        item = artifacts[backup["run_id"]][1]
        item.update(
            digest="sha256:" + hashlib.sha256(content).hexdigest(),
            size_in_bytes=len(content),
        )
        backup["archive"] = {
            key: item[key] for key in ("id", "digest", "size_in_bytes")
        }
        downloads[item["id"]] = content

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

    def subprocess_run(command, **kwargs):
        if command[:2] == ["gh", "api"]:
            identity = int(command[-1].split("/artifacts/")[1].split("/")[0])
            kwargs["stdout"].write(downloads[identity])
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(button.subprocess, "run", subprocess_run)
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
        downloads=downloads,
        original_zip=original_zip,
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


def archive_module(monkeypatch):
    path = SCRIPTS / "runtime_release_backup.py"
    assert path.is_file(), "nonpublishing archive implementation is missing"
    spec = importlib.util.spec_from_file_location("backup_archive", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "button", button)
    return module


@pytest.fixture
def archive_case(recovery, monkeypatch, tmp_path):
    import hashlib
    import io
    import zipfile

    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as z:
        for path in sorted(recovery.args.bundle.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(recovery.args.bundle).as_posix())
    original = raw.getvalue()
    original_item = artifact(123, "bundle", 1901)
    original_item.update(
        digest="sha256:" + hashlib.sha256(original).hexdigest(),
        size_in_bytes=len(original),
    )
    recovery.artifacts[123] = [original_item]
    downloads = {1901: original}
    # Bootstrapping copies is read-only; publication still requires a populated policy.
    recovery.registry.write_text(
        json.dumps(
            {"schema_version": 1, "repository": button.REPOSITORY, "bundles": []}
        )
    )

    def run(command, **kwargs):
        if command[:2] == ["gh", "api"]:
            assert "/artifacts/" in command[-1] and command[-1].endswith("/zip")
            identity = int(command[-1].split("/artifacts/")[1].split("/")[0])
            kwargs["stdout"].write(downloads[identity])
        else:
            assert "twine" in command, "unexpected archive subprocess"
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(button.subprocess, "run", run)
    monkeypatch.setattr(
        button, "publish", lambda *args: pytest.fail("archive entered publication")
    )
    args = SimpleNamespace(**vars(recovery.args))
    args.preparation_run_id = 123
    args.output = tmp_path / "backup-output"
    return SimpleNamespace(
        recovery=recovery, args=args, original=original, downloads=downloads
    )


def test_archive_preserves_original_zip_manifest_and_every_member(
    archive_case, monkeypatch
):
    archive = archive_module(monkeypatch)
    monkeypatch.setattr(archive, "backup_controller", lambda root: "d" * 40)
    receipt = archive.archive(archive_case.args)
    out = archive_case.args.output
    assert (out / "archive/original-bundle.zip").read_bytes() == archive_case.original
    original_bundle = archive_case.recovery.args.bundle
    for path in original_bundle.rglob("*"):
        if path.is_file():
            assert (
                out / "bundle" / path.relative_to(original_bundle)
            ).read_bytes() == path.read_bytes()
    assert set(
        p.relative_to(out / "bundle").as_posix()
        for p in (out / "bundle").rglob("*")
        if p.is_file()
    ) == set(archive_case.recovery.manifest["files"]) | {button.MANIFEST}
    assert receipt["preparation_run_id"] == 123
    assert receipt["manifest_sha256"] == archive_case.args.manifest_sha256
    assert receipt["publication_performed"] is False


def test_archive_verifies_zip_digest_before_extraction(archive_case, monkeypatch):
    archive = archive_module(monkeypatch)
    monkeypatch.setattr(archive, "backup_controller", lambda root: "d" * 40)
    archive_case.recovery.artifacts[123][0]["digest"] = "sha256:" + "0" * 64
    with pytest.raises(button.ReleaseError, match="archive digest mismatch"):
        archive.archive(archive_case.args)
    assert not (archive_case.args.output / "bundle").exists()


def test_archive_refuses_existing_output(archive_case, monkeypatch):
    archive = archive_module(monkeypatch)
    monkeypatch.setattr(archive, "backup_controller", lambda root: "d" * 40)
    archive_case.args.output.mkdir()
    keep = archive_case.args.output / "keep"
    keep.write_text("owned content")
    with pytest.raises(button.ReleaseError, match="output already exists"):
        archive.archive(archive_case.args)
    assert keep.read_text() == "owned content"


def test_one_surviving_registered_raw_archive_can_reseed_copies(
    archive_case, monkeypatch
):
    import hashlib
    import io
    import zipfile

    archive = archive_module(monkeypatch)
    monkeypatch.setattr(archive, "backup_controller", lambda root: "d" * 40)
    r = archive_case.recovery
    original_digest = hashlib.sha256(archive_case.original).hexdigest()
    receipt = {
        "schema_version": 1,
        "repository": button.REPOSITORY,
        "preparation_run_id": 123,
        "manifest_sha256": r.args.manifest_sha256,
        "source_sha": r.args.source_sha,
        "version": "1.0.4",
        "original_archive_sha256": original_digest,
    }
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as z:
        z.writestr("original-bundle.zip", archive_case.original)
        z.writestr("backup-receipt.json", json.dumps(receipt))
    sidecar = raw.getvalue()
    item = r.artifacts[201][1]
    item.update(
        digest="sha256:" + hashlib.sha256(sidecar).hexdigest(),
        size_in_bytes=len(sidecar),
    )
    r.record["original_archive_sha256"] = original_digest
    r.record["backups"][0]["archive"] = {
        k: item[k] for k in ("id", "digest", "size_in_bytes")
    }
    r.save_record()
    r.artifacts[123].clear()  # The original artifact is gone.
    r.artifacts[202].clear()  # Only one independent backup survives.
    r.artifacts[201].pop(0)  # Its raw archive alone suffices to reseed, not publish.
    archive_case.downloads[item["id"]] = sidecar
    archive_case.args.preparation_run_id = 201
    result = archive.archive(archive_case.args)
    assert result["preparation_run_id"] == 123
    assert result["source_run_id"] == 201
    assert (
        archive_case.args.output / "archive/original-bundle.zip"
    ).read_bytes() == archive_case.original
    assert (archive_case.args.output / "bundle" / button.MANIFEST).read_bytes() == (
        r.args.bundle / button.MANIFEST
    ).read_bytes()
    with pytest.raises(button.ReleaseError, match="two independent healthy backups"):
        button.verify(r.args)


@pytest.mark.parametrize(
    "mutation", ["wrong_branch", "rerun", "wrong_workflow", "stale_checkout"]
)
def test_archive_controller_refuses_unsafe_execution(monkeypatch, tmp_path, mutation):
    archive = archive_module(monkeypatch)
    env = {
        "GITHUB_REPOSITORY": button.REPOSITORY,
        "GITHUB_REF": "refs/heads/backup/runtime-release-bundles",
        "GITHUB_WORKFLOW_REF": f"{button.REPOSITORY}/{button.BACKUP_WORKFLOW}@refs/heads/backup/runtime-release-bundles",
        "GITHUB_WORKFLOW_SHA": "d" * 40,
        "GITHUB_RUN_ATTEMPT": "1",
    }
    if mutation == "wrong_branch":
        env["GITHUB_REF"] = "refs/heads/community"
    if mutation == "rerun":
        env["GITHUB_RUN_ATTEMPT"] = "2"
    if mutation == "wrong_workflow":
        env["GITHUB_WORKFLOW_REF"] = "other"
    if mutation == "stale_checkout":
        env["GITHUB_WORKFLOW_SHA"] = "e" * 40
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(button, "git", lambda *args: "d" * 40)
    with pytest.raises(button.ReleaseError):
        archive.backup_controller(tmp_path)


def test_archive_checks_actual_downloaded_zip_size_before_extraction(
    archive_case, monkeypatch
):
    archive = archive_module(monkeypatch)
    monkeypatch.setattr(archive, "backup_controller", lambda root: "d" * 40)
    archive_case.recovery.artifacts[123][0]["size_in_bytes"] += 1
    with pytest.raises(button.ReleaseError, match="archive size mismatch"):
        archive.archive(archive_case.args)
    assert not (archive_case.args.output / "bundle").exists()


def test_reviewed_backup_workflow_cannot_load_a_publication_credential():
    import yaml

    template = SCRIPTS / "runtime_release_backup_workflow.yml"
    assert template.is_file(), "reviewable backup workflow template missing"
    workflow = yaml.safe_load(template.read_text())
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    job = workflow["jobs"]["backup"]
    assert "permissions" not in job and "environment" not in job
    assert "secrets." not in template.read_text()
    uploads = [
        step
        for step in job["steps"]
        if "actions/upload-artifact@" in step.get("uses", "")
    ]
    assert len(uploads) == 2
    assert {step["with"]["name"] for step in uploads} == {
        "runtime-release-bundle-${{ github.run_id }}-1",
        "runtime-release-archive-${{ github.run_id }}-1",
    }
    assert all(step["with"]["retention-days"] == 90 for step in uploads)
    assert not workflow["concurrency"]["cancel-in-progress"]


def test_available_metadata_does_not_count_as_a_readable_backup(recovery, monkeypatch):
    def unavailable(command, **kwargs):
        return SimpleNamespace(returncode=1 if command[:2] == ["gh", "api"] else 0)

    monkeypatch.setattr(button.subprocess, "run", unavailable)
    with pytest.raises(button.ReleaseError, match="artifact download failed"):
        button.verify(recovery.args)


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("receipt-source", "raw receipt differs"),
        ("original-zip", "original ZIP digest mismatch"),
        ("member", "bundle digest mismatch"),
        ("manifest", "original manifest digest mismatch"),
    ],
)
def test_backup_readability_rejects_wrong_receipts_and_nested_bytes(
    recovery, mutation, expected
):
    import hashlib
    import io
    import zipfile

    original = recovery.original_zip
    if mutation == "original-zip":
        content = bytearray(original)
        content[60] ^= 1
        original = bytes(content)
    if mutation in {"member", "manifest"}:
        stream = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(
            stream, "w"
        ) as target:
            for entry in source.infolist():
                content = source.read(entry.filename)
                if mutation == "member" and entry.filename == "pypi/a.whl":
                    content = b"other"
                if mutation == "manifest" and entry.filename == button.MANIFEST:
                    content += b"\n"
                target.writestr(entry, content)
        original = stream.getvalue()
        recovery.record["original_archive_sha256"] = hashlib.sha256(
            original
        ).hexdigest()
    changed = (
        recovery.record["backups"]
        if mutation in {"member", "manifest"}
        else recovery.record["backups"][1:]
    )
    for backup in changed:
        identity = backup["archive"]["id"]
        with zipfile.ZipFile(io.BytesIO(recovery.downloads[identity])) as source:
            receipt = json.loads(source.read("backup-receipt.json"))
        receipt["original_archive_sha256"] = recovery.record["original_archive_sha256"]
        if mutation == "receipt-source":
            receipt["source_sha"] = "f" * 40
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as target:
            target.writestr("original-bundle.zip", original)
            target.writestr("backup-receipt.json", json.dumps(receipt))
        content = stream.getvalue()
        recovery.downloads[identity] = content
        metadata = recovery.artifacts[backup["run_id"]][1]
        metadata.update(
            digest="sha256:" + hashlib.sha256(content).hexdigest(),
            size_in_bytes=len(content),
        )
        backup["archive"] = {
            key: metadata[key] for key in ("id", "digest", "size_in_bytes")
        }
    recovery.save_record()
    with pytest.raises(button.ReleaseError, match=expected):
        button.verify(recovery.args)
