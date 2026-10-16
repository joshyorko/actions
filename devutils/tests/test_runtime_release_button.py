import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SCRIPTS = ROOT / "action_server/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "runtime_release_button", SCRIPTS / "runtime_release_button.py"
)
button = importlib.util.module_from_spec(spec)
# A missing implementation is the initial red regression.
spec.loader.exec_module(button)


def manifest():
    return {
        "version": "1.0.4",
        "source_sha": "a" * 40,
        "preparation_run_id": 123,
        "files": {
            "pypi/a.whl": {"sha256": "b" * 64, "size": 12},
            "pypi/b.tar.gz": {"sha256": "c" * 64, "size": 13},
            "native/actions-runtime-1.0.4-linux64": {"sha256": "d" * 64, "size": 14},
        },
    }


def pypi_file(name, digest, size):
    return {"filename": name, "digests": {"sha256": digest}, "size": size}


def release(m, digest, *, assets=None, draft=True):
    return {
        "id": 45,
        "tag_name": "actions-runtime-1.0.4",
        "target_commitish": "a" * 40,
        "body": button.release_body(m, digest),
        "draft": draft,
        "prerelease": False,
        "assets": assets or [],
    }


def test_new_publication_plan():
    m = manifest()
    assert button.reconcile_pypi(m, [], owned=False) == ["a.whl", "b.tar.gz"]
    assert button.reconcile_release(m, "e" * 64, None, None) == [
        "actions-runtime-1.0.4-linux64"
    ]


@pytest.mark.parametrize("existing", [0, 1, 2])
def test_retry_only_uploads_missing_exact_files(existing):
    m = manifest()
    files = [pypi_file("a.whl", "b" * 64, 12), pypi_file("b.tar.gz", "c" * 64, 13)]
    assert (
        button.reconcile_pypi(m, files[:existing], owned=True)
        == ["a.whl", "b.tar.gz"][existing:]
    )


@pytest.mark.parametrize(
    "mutation", ["digest", "size", "unexpected", "duplicate", "unowned"]
)
def test_pypi_collision_fails_closed(mutation):
    files = [pypi_file("a.whl", "b" * 64, 12)]
    if mutation == "digest":
        files[0]["digests"]["sha256"] = "0" * 64
    if mutation == "size":
        files[0]["size"] = 90
    if mutation == "unexpected":
        files.append(pypi_file("other.whl", "b" * 64, 12))
    if mutation == "duplicate":
        files *= 2
    with pytest.raises(button.ReleaseError):
        button.reconcile_pypi(manifest(), files, owned=mutation != "unowned")


def test_partial_draft_resume_and_complete_noop():
    m, digest = manifest(), "e" * 64
    r = release(m, digest)
    assert button.reconcile_release(m, digest, r, None) == [
        "actions-runtime-1.0.4-linux64"
    ]
    r["assets"] = [
        {
            "name": "actions-runtime-1.0.4-linux64",
            "digest": "sha256:" + "d" * 64,
            "size": 14,
            "state": "uploaded",
        }
    ]
    assert button.reconcile_release(m, digest, r, "a" * 40) == []
    r["draft"] = False
    assert button.reconcile_release(m, digest, r, "a" * 40) == []


@pytest.mark.parametrize(
    "mutation",
    [
        "source",
        "body",
        "tag",
        "published_partial",
        "asset_digest",
        "asset_size",
        "unexpected",
        "duplicate",
        "no_release_tag",
    ],
)
def test_release_collision_cannot_replace_or_retarget(mutation):
    m, digest = manifest(), "e" * 64
    r = release(m, digest)
    tag = None
    if mutation == "source":
        r["target_commitish"] = "f" * 40
    if mutation == "body":
        r["body"] += "changed"
    if mutation == "tag":
        tag = "f" * 40
    if mutation == "published_partial":
        r["draft"] = False
    if mutation.startswith("asset_"):
        r["assets"] = [
            {
                "name": "actions-runtime-1.0.4-linux64",
                "digest": "sha256:" + "d" * 64,
                "size": 14,
                "state": "uploaded",
            }
        ]
        r["assets"][0]["digest" if mutation == "asset_digest" else "size"] = "wrong"
    if mutation == "unexpected":
        r["assets"] = [{"name": "extra"}]
    if mutation == "duplicate":
        r["assets"] = [{"name": "extra"}] * 2
    if mutation == "no_release_tag":
        r, tag = None, "a" * 40
    with pytest.raises(button.ReleaseError):
        button.reconcile_release(m, digest, r, tag)


def test_successful_pr_run_requires_canonical_workflow_jobs_and_same_repo():
    run = {
        "id": 1,
        "head_sha": "a" * 40,
        "path": ".github/workflows/actions_runtime_tests.yml",
        "status": "completed",
        "conclusion": "success",
        "event": "pull_request",
        "repository": {"full_name": "joshyorko/actions"},
        "head_repository": {"full_name": "joshyorko/actions"},
    }
    jobs = [{"conclusion": "success"}] * 3
    button.validate_run(run, jobs, sha="a" * 40, path=run["path"], count=3)
    for key, value in [
        ("head_sha", "b" * 40),
        ("path", "other"),
        ("conclusion", "failure"),
        ("event", "pull_request_target"),
        ("head_repository", {"full_name": "fork/actions"}),
    ]:
        bad = dict(run, **{key: value})
        with pytest.raises(button.ReleaseError):
            button.validate_run(bad, jobs, sha="a" * 40, path=run["path"], count=3)
    with pytest.raises(button.ReleaseError):
        button.validate_run(run, jobs[:2], sha="a" * 40, path=run["path"], count=3)
    with pytest.raises(button.ReleaseError):
        button.validate_run(
            run,
            [{"conclusion": "skipped"}] * 3,
            sha="a" * 40,
            path=run["path"],
            count=3,
        )


def test_bundle_rejects_mutation_symlink_and_unlisted_file(tmp_path):
    (tmp_path / "one").write_bytes(b"original")
    m = {"files": {"one": {"sha256": button.sha256(tmp_path / "one"), "size": 8}}}
    button.verify_files(tmp_path, m)
    (tmp_path / "two").write_bytes(b"extra")
    with pytest.raises(button.ReleaseError):
        button.verify_files(tmp_path, m)
    (tmp_path / "two").unlink()
    (tmp_path / "one").write_bytes(b"modified")
    with pytest.raises(button.ReleaseError):
        button.verify_files(tmp_path, m)
    (tmp_path / "one").unlink()
    (tmp_path / "outside").write_bytes(b"original")
    (tmp_path / "one").symlink_to(tmp_path / "outside")
    with pytest.raises(button.ReleaseError):
        button.verify_files(tmp_path, m)


def test_zip_traversal_duplicate_symlink_and_bomb_are_rejected(tmp_path):
    import stat
    import zipfile

    for name, mode in [
        ("../escape", 0),
        ("/absolute", 0),
        ("a\\b", 0),
        ("link", stat.S_IFLNK << 16),
    ]:
        archive = tmp_path / "bad.zip"
        with zipfile.ZipFile(archive, "w") as z:
            entry = zipfile.ZipInfo(name)
            entry.external_attr = mode
            z.writestr(entry, b"data")
        with pytest.raises(button.ReleaseError):
            button.extract_zip(archive, tmp_path / "output")


def test_release_version_never_inferred_or_adapted():
    for value in ["v1.0.4", "1.0.4rc1", "1.0", "1.0.4/../../x", "01.0.4"]:
        with pytest.raises(button.ReleaseError):
            button.validate_version(value)
    button.validate_version("1.0.4")


def test_validate_never_writes_or_requires_publication_credentials(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("GITHUB_ACTOR", "joshyorko")
    monkeypatch.setenv("GITHUB_TRIGGERING_ACTOR", "joshyorko")
    from types import SimpleNamespace

    m = manifest()
    monkeypatch.setattr(button, "verify", lambda args: m)
    monkeypatch.setattr(button, "release_state", lambda version: (None, None))
    monkeypatch.setattr(button, "pypi_files", lambda version: [])
    monkeypatch.setattr(
        button,
        "api",
        lambda *args, **kwargs: pytest.fail("validation attempted a remote write"),
    )
    monkeypatch.delenv("RUNTIME_TOKEN", raising=False)
    args = SimpleNamespace(
        command="validate",
        source_sha=m["source_sha"],
        version=m["version"],
        manifest_sha256="e" * 64,
    )
    button.publish(args)
    args.command = "publish"
    with pytest.raises(
        button.ReleaseError, match="required before any publication write"
    ):
        button.publish(args)


def test_interruption_after_each_external_write_resumes_without_duplicates(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("GITHUB_ACTOR", "joshyorko")
    monkeypatch.setenv("GITHUB_TRIGGERING_ACTOR", "joshyorko")
    from types import SimpleNamespace

    m, digest = manifest(), "e" * 64
    monkeypatch.setattr(button, "verify", lambda args: m)
    monkeypatch.setenv("RUNTIME_TOKEN", "synthetic-test-token")
    args = SimpleNamespace(
        command="publish",
        source_sha=m["source_sha"],
        version=m["version"],
        manifest_sha256=digest,
        bundle=tmp_path,
    )
    # Simulate a lost response after each committed draft/asset/PyPI/tag/publication write.
    for interrupt_at in range(1, 8):
        state = {
            "release": None,
            "tag": None,
            "pypi": [],
            "writes": [],
            "interrupted": False,
        }

        def write(kind):
            state["writes"].append(kind)
            if len(state["writes"]) == interrupt_at and not state["interrupted"]:
                state["interrupted"] = True
                raise RuntimeError("synthetic connection lost after committed write")

        def api(endpoint, *, method="GET", data=None, **kwargs):
            if method == "GET":
                return copy.deepcopy(state["release"])
            if endpoint.endswith("/releases"):
                assert state["release"] is None
                state["release"] = release(m, digest)
                write("draft")
            elif endpoint.endswith("/git/refs"):
                assert state["tag"] is None
                state["tag"] = m["source_sha"]
                write("tag")
            elif method == "PATCH":
                assert state["release"]["draft"]
                state["release"]["draft"] = False
                write("public")
            else:
                pytest.fail(endpoint)
            return copy.deepcopy(state["release"])

        def run(command, **kwargs):
            if "twine" in command:
                name = Path(command[-1]).name
                assert name not in [item["filename"] for item in state["pypi"]]
                entry = m["files"]["pypi/" + name]
                state["pypi"].append(pypi_file(name, entry["sha256"], entry["size"]))
                write(name)
            else:
                assert not state["release"]["assets"]
                state["release"]["assets"] = [
                    {
                        "name": "actions-runtime-1.0.4-linux64",
                        "digest": "sha256:" + "d" * 64,
                        "size": 14,
                        "state": "uploaded",
                    }
                ]
                write("native")

        monkeypatch.setattr(button, "api", api)
        monkeypatch.setattr(button.subprocess, "run", run)
        monkeypatch.setattr(
            button,
            "release_state",
            lambda version: (copy.deepcopy(state["release"]), state["tag"]),
        )
        monkeypatch.setattr(
            button, "pypi_files", lambda version: copy.deepcopy(state["pypi"])
        )
        try:
            button.publish(args)
        except RuntimeError:
            pass
        button.publish(args)
        writes = list(state["writes"])
        button.publish(args)
        assert state["writes"] == writes
        assert writes == ["draft", "native", "a.whl", "b.tar.gz", "tag", "public"]
        assert state["release"]["draft"] is False


def test_manual_workflows_have_read_only_validation_and_explicit_publication():
    import yaml

    prepare = yaml.safe_load(
        (ROOT / ".github/workflows/runtime-release-prepare.yml").read_text()
    )
    publish = yaml.safe_load(
        (ROOT / ".github/workflows/runtime-release-publish.yml").read_text()
    )
    assert prepare["permissions"] == {"contents": "read", "actions": "read"}
    assert publish["permissions"] == prepare["permissions"]
    assert "permissions" not in publish["jobs"]["validate"]
    writer = publish["jobs"]["publish"]
    assert (
        writer["if"]
        == "inputs.operation == 'publish' && github.actor == 'joshyorko' && github.triggering_actor == 'joshyorko'"
    )
    assert writer["needs"] == "validate"
    assert writer["environment"] == "pypi"
    assert writer["permissions"] == {"contents": "write", "actions": "read"}
    assert (
        publish[True]["workflow_dispatch"]["inputs"]["operation"]["default"]
        == "validate"
    )
    for workflow in (prepare, publish):
        assert workflow["concurrency"]["cancel-in-progress"] is False
        assert (
            workflow["concurrency"]["group"]
            == "runtime-release-${{ inputs.expected_version }}"
        )


def test_read_only_validation_cannot_adopt_a_hidden_draft(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTOR", "joshyorko")
    monkeypatch.setenv("GITHUB_TRIGGERING_ACTOR", "joshyorko")
    from types import SimpleNamespace

    m = manifest()
    monkeypatch.setattr(button, "verify", lambda args: m)
    monkeypatch.setattr(
        button, "release_state", lambda version: (None, m["source_sha"])
    )
    monkeypatch.setattr(
        button, "pypi_files", lambda version: [pypi_file("a.whl", "b" * 64, 12)]
    )
    monkeypatch.setattr(
        button,
        "api",
        lambda *args, **kwargs: pytest.fail("write before ownership verification"),
    )
    args = SimpleNamespace(
        command="validate",
        source_sha=m["source_sha"],
        version=m["version"],
        manifest_sha256="e" * 64,
    )
    button.publish(args)
    args.command = "publish"
    with pytest.raises(button.ReleaseError, match="without an owned"):
        button.publish(args)


def test_source_binding_accepts_normal_merge_but_rejects_changed_workflow_tree(
    tmp_path,
):
    import subprocess

    repo, remote = tmp_path / "repo", tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=community", str(repo)], check=True
    )

    def git(*args):
        return button.git(repo, *args)

    git("config", "user.email", "synthetic@example.invalid")
    git("config", "user.name", "Synthetic release test")
    git("remote", "add", "origin", str(remote))
    for name, contents in {
        "action_server/pyproject.toml": '[tool.poetry]\nname="actions-runtime"\nversion="1.0.4"\n',
        "action_server/src/actions/server/__init__.py": '__version__ = "1.0.4"\n',
        "action_server/scripts/verify_published_runtime_floor.py": 'EXPECTED_RUNTIME = "1.0.4"\n',
        "action_server/docs/ACTIONS_RUNTIME_CHANGELOG.md": "## actions-runtime-1.0.4\n\nSynthetic notes.\n",
        ".github/workflows/button.yml": "name: synthetic\n",
    }.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    git("add", ".")
    git("commit", "--quiet", "-m", "base")
    git("checkout", "--quiet", "-b", "qualified")
    (repo / "qualified.txt").write_text("qualified\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "qualified source")
    qualified = git("rev-parse", "HEAD")
    git("checkout", "--quiet", "community")
    git("merge", "--quiet", "--no-ff", "qualified", "-m", "normal merge")
    source = git("rev-parse", "HEAD")
    git("push", "--quiet", "origin", "community")
    assert source != qualified
    assert button.check_source(repo, source, qualified, "1.0.4") == git(
        "rev-parse", "HEAD^{tree}"
    )
    with pytest.raises(button.ReleaseError, match="version mismatch"):
        button.check_source(repo, source, qualified, "1.0.5")
    (repo / ".github/workflows/button.yml").write_text("name: changed\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "controller workflow changed")
    git("push", "--quiet", "origin", "community")
    with pytest.raises(button.ReleaseError, match="workflow files differ"):
        button.check_source(repo, source, qualified, "1.0.4")


def test_download_verifies_github_archive_digest_before_extraction(
    monkeypatch, tmp_path
):
    import zipfile

    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("receipt.json", b"{}")
    metadata = {
        "id": 9,
        "name": "proof",
        "digest": "sha256:" + button.sha256(archive),
        "size_in_bytes": archive.stat().st_size,
        "expired": False,
        "created_at": "synthetic",
        "expires_at": "synthetic",
    }
    monkeypatch.setattr(button, "pages", lambda *args: [metadata])

    def download(command, *, stdout, stderr):
        from types import SimpleNamespace

        stdout.write(archive.read_bytes())
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(button.subprocess, "run", download)
    button.download({"id": 12}, "proof", tmp_path / "valid")
    assert (tmp_path / "valid/receipt.json").read_bytes() == b"{}"
    metadata["digest"] = "sha256:" + "0" * 64
    with pytest.raises(button.ReleaseError, match="archive digest mismatch"):
        button.download({"id": 12}, "proof", tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize("original_conclusion", ["success", "failure"])
def test_publication_keeps_original_success_after_an_accidental_preparation_rerun(
    monkeypatch, tmp_path, original_conclusion
):
    import hashlib
    import json
    from types import SimpleNamespace

    bundle = tmp_path / "bundle"
    native = bundle / "native"
    native.mkdir(parents=True)
    (bundle / "pypi").mkdir()
    for suffix in ("linux64", "macos-arm64", "windows64.exe", "sha256.txt"):
        (native / f"actions-runtime-1.0.4-{suffix}").write_bytes(b"synthetic")
    m = dict(
        manifest(),
        schema_version=1,
        repository=button.REPOSITORY,
        qualification_sha="a" * 40,
        tree="b" * 40,
        controller_sha="c" * 40,
        preparation_run_attempt=1,
    )
    path = bundle / button.MANIFEST
    path.write_text(json.dumps(m))
    args = SimpleNamespace(
        root=tmp_path,
        bundle=bundle,
        manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        preparation_run_id=123,
        source_sha="a" * 40,
        version="1.0.4",
    )
    monkeypatch.setattr(button, "controller", lambda *args: None)
    monkeypatch.setattr(button, "check_source", lambda *args: m["tree"])
    monkeypatch.setattr(button, "verify_files", lambda *args: None)
    monkeypatch.setattr(button, "verify_artifacts", lambda *args: None)
    monkeypatch.setattr(button.subprocess, "run", lambda *args, **kwargs: None)
    requested = []

    def api(endpoint):
        requested.append(endpoint)
        return {
            "path": button.PREPARE_WORKFLOW,
            "event": "workflow_dispatch",
            "head_branch": "community",
            "head_sha": m["controller_sha"],
            "run_attempt": 1 if endpoint.endswith("/attempts/1") else 2,
            "conclusion": original_conclusion
            if endpoint.endswith("/attempts/1")
            else "failure",
        }

    monkeypatch.setattr(button, "api", api)
    if original_conclusion == "success":
        assert button.verify(args) == m
    else:
        with pytest.raises(
            button.ReleaseError, match="preparation run identity/state mismatch"
        ):
            button.verify(args)
    assert requested == [f"repos/{button.REPOSITORY}/actions/runs/123/attempts/1"]


@pytest.mark.parametrize(
    "actor,triggering_actor",
    [
        ("another-writer", "joshyorko"),
        ("joshyorko", "another-writer"),
        ("another-writer", "another-writer"),
    ],
)
def test_only_josh_can_enter_publication_or_rerun_writer(
    monkeypatch, actor, triggering_actor
):
    from types import SimpleNamespace

    monkeypatch.setenv("GITHUB_ACTOR", actor)
    monkeypatch.setenv("GITHUB_TRIGGERING_ACTOR", triggering_actor)
    monkeypatch.setattr(
        button,
        "verify",
        lambda *args: pytest.fail("nonowner entered publication validation"),
    )
    with pytest.raises(button.ReleaseError, match="Only joshyorko"):
        button.publish(SimpleNamespace(command="publish"))
