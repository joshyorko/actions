"""Prepare immutable Runtime bundles and reconcile owner-requested publication.

No write to GitHub or PyPI occurs without the explicit ``publish`` subcommand.
The producer run SHA and checkout SHA remain distinct from the release SHA;
complete Git tree equality binds a normal merge to its reviewed PR artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from publish_verified_runtime import verify_artifacts

REPOSITORY = "joshyorko/actions"
MANIFEST = "release-bundle.json"
PREPARE_WORKFLOW = ".github/workflows/runtime-release-prepare.yml"
REQUIRED = {
    "actions_runtime_tests.yml": 3,
    "actions_runtime_pypi_release.yml": 5,
    "frontend-build-unauthenticated.yml": 3,
    "developer_toolkit.yml": 6,
    "actions_core_tests.yml": 4,
    "http_helper_tests.yml": 3,
    "coverage-gate.yml": 1,
    "ai-audit.yml": 1,
}
PLATFORMS = {
    "ubuntu-22.04": ("Linux", "linux64", "action-server"),
    "macos-15": ("Darwin", "macos-arm64", "action-server"),
    "windows-2022": ("Windows", "windows64.exe", "action-server.exe"),
}


class ReleaseError(ValueError):
    """A release invariant failed; retain existing state for a reviewed retry."""


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def validate_version(version):
    require(
        re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version),
        "expected stable X.Y.Z version",
    )


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def api(endpoint, *, method="GET", data=None, missing=False):
    command = ["gh", "api", "--method", method, endpoint]
    if data is not None:
        command += ["--input", "-"]
    result = subprocess.run(
        command,
        input=json.dumps(data) if data is not None else None,
        capture_output=True,
        text=True,
    )
    if missing and result.returncode and "HTTP 404" in result.stderr:
        return None
    require(result.returncode == 0, f"GitHub API {method} failed: {endpoint}")
    return json.loads(result.stdout)


def pages(endpoint, key):
    result = []
    for page in range(1, 101):
        separator = "&" if "?" in endpoint else "?"
        payload = api(f"{endpoint}{separator}per_page=100&page={page}")
        items = payload[key] if key else payload
        result.extend(items)
        if len(items) < 100:
            return result
    raise ReleaseError("GitHub pagination exceeded bound")


def validate_run(run, jobs, *, sha, path, count):
    require(run.get("head_sha") == sha, "qualification source SHA mismatch")
    require(run.get("path") == path, "qualification workflow path mismatch")
    require(
        run.get("repository", {}).get("full_name") == REPOSITORY,
        "qualification repository mismatch",
    )
    require(
        run.get("head_repository", {}).get("full_name") == REPOSITORY,
        "fork qualification is not admitted",
    )
    require(
        run.get("event") in {"pull_request", "push"}, "unexpected qualification event"
    )
    require(
        run.get("status") == "completed" and run.get("conclusion") == "success",
        "latest exact-head qualification is not successful",
    )
    require(
        len(jobs) == count and all(job.get("conclusion") == "success" for job in jobs),
        "required qualification jobs missing, skipped, or failed",
    )


def check_source(root, source, qualification, version):
    import tomllib

    validate_version(version)
    for value in (source, qualification):
        require(
            re.fullmatch(r"[0-9a-f]{40}", value), "source must be a full lowercase SHA"
        )
        git(root, "fetch", "--no-tags", "origin", value)
        git(root, "merge-base", "--is-ancestor", value, "origin/community")
    tree = git(root, "rev-parse", f"{source}^{{tree}}")
    require(
        tree == git(root, "rev-parse", f"{qualification}^{{tree}}"),
        "release and qualification complete trees differ",
    )
    project = tomllib.loads(git(root, "show", f"{source}:action_server/pyproject.toml"))
    require(
        project["tool"]["poetry"]["name"] == "actions-runtime",
        "wrong distribution identity",
    )
    require(project["tool"]["poetry"]["version"] == version, "package version mismatch")
    init = git(root, "show", f"{source}:action_server/src/actions/server/__init__.py")
    require(
        re.search(rf'^__version__ = "{re.escape(version)}"$', init, re.M),
        "Runtime version mismatch",
    )
    floor = git(
        root,
        "show",
        f"{source}:action_server/scripts/verify_published_runtime_floor.py",
    )
    require(
        re.search(rf'^EXPECTED_RUNTIME = "{re.escape(version)}"$', floor, re.M),
        "installed-wheel verifier version mismatch",
    )
    changelog = git(
        root, "show", f"{source}:action_server/docs/ACTIONS_RUNTIME_CHANGELOG.md"
    )
    require(
        f"## actions-runtime-{version}" in changelog.splitlines(),
        "exact Runtime changelog heading missing",
    )
    return tree


def controller(root, workflow):
    require(
        os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "wrong controller repository"
    )
    require(
        os.environ.get("GITHUB_REF") == "refs/heads/community",
        "dispatch the controller from community",
    )
    require(
        os.environ.get("GITHUB_WORKFLOW_REF")
        == f"{REPOSITORY}/{workflow}@refs/heads/community",
        "unexpected controller workflow",
    )
    git(
        root,
        "fetch",
        "--no-tags",
        "origin",
        "refs/heads/community:refs/remotes/origin/community",
    )
    head = git(root, "rev-parse", "HEAD")
    require(
        head
        == os.environ.get("GITHUB_WORKFLOW_SHA")
        == git(root, "rev-parse", "origin/community"),
        "controller is not current merged community",
    )
    return head


def safe_name(name):
    require(
        isinstance(name, str) and name and "\\" not in name and ":" not in name,
        "unsafe bundle path",
    )
    require(
        not name.startswith("/")
        and all(part not in {"", ".", ".."} for part in name.split("/")),
        "unsafe bundle path",
    )
    require(
        len(name) <= 240 and len(name.split("/")) <= 8, "bundle path bound exceeded"
    )


def extract_zip(archive, destination):
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        require(
            len(entries) <= 2000
            and sum(item.file_size for item in entries) <= 2 * 1024**3,
            "artifact archive bounds exceeded",
        )
        seen = set()
        for item in entries:
            name = item.filename.rstrip("/")
            safe_name(name)
            require(name not in seen, "duplicate archive path")
            seen.add(name)
            mode = item.external_attr >> 16
            require(
                not stat.S_ISLNK(mode)
                and (stat.S_IFMT(mode) in {0, stat.S_IFREG, stat.S_IFDIR}),
                "nonregular archive member",
            )
        require(not destination.exists(), "artifact destination already exists")
        destination.mkdir(parents=True)
        source.extractall(destination)


def download(run, artifact_name, destination):
    artifacts = pages(
        f"repos/{REPOSITORY}/actions/runs/{run['id']}/artifacts", "artifacts"
    )
    matches = [item for item in artifacts if item["name"] == artifact_name]
    require(
        len(matches) == 1 and not matches[0]["expired"],
        f"missing, duplicated, or expired artifact: {artifact_name}",
    )
    artifact = matches[0]
    require(
        0 < artifact["size_in_bytes"] <= 2 * 1024**3, "artifact size bound exceeded"
    )
    archive = destination.with_suffix(".zip")
    with archive.open("wb") as stream:
        result = subprocess.run(
            ["gh", "api", f"repos/{REPOSITORY}/actions/artifacts/{artifact['id']}/zip"],
            stdout=stream,
            stderr=subprocess.PIPE,
        )
    require(result.returncode == 0, "artifact download failed")
    extract_zip(archive, destination)
    archive.unlink()
    return {
        key: artifact[key]
        for key in ("id", "name", "digest", "size_in_bytes", "created_at", "expires_at")
    }


def verify_files(directory, manifest):
    actual = set()
    for path in directory.rglob("*"):
        require(not path.is_symlink(), "symlink in bundle")
        if path.is_dir():
            continue
        require(
            path.is_file() and path.stat().st_nlink == 1,
            "nonregular or hardlinked bundle member",
        )
        name = path.relative_to(directory).as_posix()
        if name == MANIFEST:
            continue
        safe_name(name)
        actual.add(name)
    require(actual == set(manifest["files"]), "bundle inventory differs from manifest")
    for name, entry in manifest["files"].items():
        safe_name(name)
        path = directory / name
        require(
            path.stat().st_size == entry["size"] and sha256(path) == entry["sha256"],
            f"bundle digest mismatch: {name}",
        )


def release_body(manifest, digest):
    return (
        f"Actions Runtime {manifest['version']}\n\n"
        f"{manifest.get('release_notes', '')}\n\n"
        f"Immutable source: {manifest['source_sha']}\n"
        f"Preparation run: {manifest['preparation_run_id']}\n"
        f"Reviewed release-bundle.json SHA-256: {digest}\n\n"
        "This release publishes the reviewed preparation bundle directly. "
        "Reruns may add only missing assets with the same manifest; existing bytes are never replaced."
    )


def reconcile_pypi(manifest, existing, *, owned):
    expected = {
        Path(name).name: entry
        for name, entry in manifest["files"].items()
        if name.startswith("pypi/") and not name.endswith(".sha256")
    }
    seen = set()
    require(
        not existing or owned,
        "PyPI version already exists without this preparation's owned release",
    )
    for item in existing:
        name = item["filename"]
        require(
            name in expected and name not in seen,
            "unexpected or duplicate PyPI distribution",
        )
        seen.add(name)
        require(
            item.get("digests", {}).get("sha256") == expected[name]["sha256"]
            and item.get("size") == expected[name]["size"],
            "existing PyPI bytes differ; never replace or skip blindly",
        )
    return sorted(set(expected) - seen)


def reconcile_release(manifest, digest, release, tag_sha):
    expected = {
        Path(name).name: entry
        for name, entry in manifest["files"].items()
        if name.startswith("native/")
    }
    require(
        tag_sha is None or tag_sha == manifest["source_sha"],
        "existing tag targets another source",
    )
    if release is None:
        require(tag_sha is None, "tag exists without an owned resumable release")
        return sorted(expected)
    require(
        release.get("tag_name") == f"actions-runtime-{manifest['version']}"
        and release.get("target_commitish") == manifest["source_sha"],
        "release identity mismatch",
    )
    require(
        release.get("body") == release_body(manifest, digest)
        and release.get("prerelease") is False,
        "release is not owned by this preparation",
    )
    seen = set()
    for asset in release.get("assets", []):
        name = asset["name"]
        require(
            name in expected and name not in seen,
            "unexpected or duplicate native asset",
        )
        seen.add(name)
        require(
            asset.get("state") == "uploaded"
            and asset.get("digest") == "sha256:" + expected[name]["sha256"]
            and asset.get("size") == expected[name]["size"],
            "existing native asset differs; never overwrite",
        )
    missing = sorted(set(expected) - seen)
    require(
        release.get("draft") is True
        or (not missing and tag_sha == manifest["source_sha"]),
        "published release is incomplete or lacks its immutable tag",
    )
    return missing


def pypi_files(version):
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/actions-runtime/{version}/json", timeout=30
        ) as response:
            return json.load(response)["urls"]
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return []
        raise


def release_state(version):
    tag = f"actions-runtime-{version}"
    releases = pages(f"repos/{REPOSITORY}/releases", None)
    matches = [item for item in releases if item["tag_name"] == tag]
    require(len(matches) <= 1, "duplicate release tag records")
    ref = api(f"repos/{REPOSITORY}/git/ref/tags/{tag}", missing=True)
    target = ref["object"] if ref else None
    for _ in range(5):
        if target is None or target["type"] == "commit":
            return matches[0] if matches else None, target["sha"] if target else None
        require(target["type"] == "tag", "tag does not resolve to commit")
        target = api(f"repos/{REPOSITORY}/git/tags/{target['sha']}")["object"]
    raise ReleaseError("tag nesting exceeded bound")


def prepare(args):
    root = args.root.resolve()
    control = controller(root, PREPARE_WORKFLOW)
    require(
        os.environ.get("GITHUB_RUN_ATTEMPT") == "1",
        "never rerun preparation; start a new preparation or resume publication from its original bundle",
    )
    tree = check_source(root, args.source_sha, args.qualification_sha, args.version)
    require(not args.output.exists(), "preparation output already exists")
    release, tag = release_state(args.version)
    require(
        release is None and tag is None and not pypi_files(args.version),
        "version already has publication state; reuse its original preparation",
    )
    runs = {}
    for filename, count in REQUIRED.items():
        candidates = pages(
            f"repos/{REPOSITORY}/actions/workflows/{filename}/runs?head_sha={args.qualification_sha}",
            "workflow_runs",
        )
        require(candidates, f"no exact-head run: {filename}")
        run = max(candidates, key=lambda item: (item["id"], item["run_attempt"]))
        jobs = pages(
            f"repos/{REPOSITORY}/actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs",
            "jobs",
        )
        validate_run(
            run,
            jobs,
            sha=args.qualification_sha,
            path=f".github/workflows/{filename}",
            count=count,
        )
        runs[filename] = run
    args.output.mkdir(parents=True)
    evidence = args.output / "evidence"
    evidence.mkdir()
    for filename, run in runs.items():
        save(
            evidence / (filename + ".json"),
            {
                key: run[key]
                for key in (
                    "id",
                    "run_attempt",
                    "head_sha",
                    "head_branch",
                    "event",
                    "path",
                    "workflow_id",
                    "conclusion",
                    "html_url",
                    "created_at",
                    "updated_at",
                )
            },
        )
    downloads = args.output.parent / (args.output.name + "-downloads")
    require(not downloads.exists(), "download directory already exists")
    downloads.mkdir()
    pypi_run = runs["actions_runtime_pypi_release.yml"]
    dist = args.output / "pypi"
    artifacts = [download(pypi_run, "actions-runtime-dist", dist)]
    names = verify_artifacts(dist)
    require(
        all(
            name.startswith(f"actions_runtime-{args.version}-")
            or name == f"actions_runtime-{args.version}.tar.gz"
            for name in names
        ),
        "distribution version mismatch",
    )
    measured = {}
    for lane in ("sdist", "Linux", "macOS", "Windows"):
        target = downloads / lane
        artifacts.append(download(pypi_run, f"runtime-build-source-{lane}", target))
        proof = json.loads((target / "runtime-build-source.json").read_text())
        require(
            proof["run_id"] == str(pypi_run["id"])
            and proof["run_attempt"] == str(pypi_run["run_attempt"]),
            "package receipt producer mismatch",
        )
        require(
            proof["qualification_sha"] == args.qualification_sha
            and proof["tree"] == tree
            and proof["version"] == args.version,
            "package receipt source mismatch",
        )
        git(root, "fetch", "--no-tags", "origin", proof["source_sha"])
        require(
            git(root, "rev-parse", proof["source_sha"] + "^{tree}") == tree,
            "package producer checkout tree mismatch",
        )
        for name, digest in proof["files"].items():
            require(
                name not in measured
                and name in names
                and sha256(dist / name) == digest,
                "package producer digest mismatch",
            )
            measured[name] = digest
        shutil.copy2(
            target / "runtime-build-source.json", evidence / f"package-{lane}.json"
        )
    require(
        set(measured) == set(names),
        "producer receipts do not cover all seven distributions",
    )
    native = args.output / "native"
    native.mkdir()
    native_run = runs["frontend-build-unauthenticated.yml"]
    for runner, (platform, suffix, binary) in PLATFORMS.items():
        acceptance = downloads / f"acceptance-{runner}"
        # Native manifests retain the actual PR merge checkout identity.
        listing = pages(
            f"repos/{REPOSITORY}/actions/runs/{native_run['id']}/artifacts", "artifacts"
        )
        candidates = [
            item["name"]
            for item in listing
            if item["name"].startswith(f"native-acceptance-{runner}-")
        ]
        require(len(candidates) == 1, "native acceptance receipt is ambiguous")
        artifacts.append(download(native_run, candidates[0], acceptance))
        manifest = json.loads(
            (acceptance / "native-artifact-manifest.json").read_text()
        )
        require(
            manifest["workflow_run_id"] == str(native_run["id"])
            and manifest["workflow_run_attempt"] == str(native_run["run_attempt"]),
            "native producer mismatch",
        )
        git(root, "fetch", "--no-tags", "origin", manifest["source_sha"])
        require(
            git(root, "rev-parse", manifest["source_sha"] + "^{tree}") == tree
            and manifest["platform"] == platform
            and manifest["architecture"].lower()
            in ({"arm64", "aarch64"} if platform == "Darwin" else {"amd64", "x86_64"}),
            "native checkout tree/platform/architecture mismatch",
        )
        for receipt_name in ("native-acceptance.json", "native-history.json"):
            receipt = json.loads((acceptance / receipt_name).read_text())
            require(
                receipt["source_sha"] == manifest["source_sha"]
                and receipt["status"] == "PASS",
                "native acceptance/history failed",
            )
            require(
                len(receipt["cases"]) == 2
                and {case["kind"] for case in receipt["cases"]}
                == {"frozen", "go-wrapper"}
                and all(
                    case["status"] == "PASS"
                    and case["sha256"] == manifest["artifacts"][case["kind"]]["sha256"]
                    for case in receipt["cases"]
                ),
                "both frozen and Go-wrapper acceptance cases must match measured binaries",
            )
            if receipt_name == "native-acceptance.json":
                require(
                    receipt["expected_version"] == args.version,
                    "native version mismatch",
                )
            shutil.copy2(
                acceptance / receipt_name, evidence / f"{runner}-{receipt_name}"
            )
        shutil.copy2(
            acceptance / "native-artifact-manifest.json",
            evidence / f"{runner}-manifest.json",
        )
        executable = downloads / f"binary-{runner}"
        artifacts.append(
            download(native_run, f"action-server-unauthenticated-{runner}", executable)
        )
        require(
            [path.name for path in executable.iterdir()] == [binary],
            "native download inventory mismatch",
        )
        require(
            sha256(executable / binary)
            == manifest["artifacts"]["go-wrapper"]["sha256"],
            "native executable digest mismatch",
        )
        shutil.copy2(
            executable / binary, native / f"actions-runtime-{args.version}-{suffix}"
        )
    checksum = native / f"actions-runtime-{args.version}-sha256.txt"
    checksum.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in sorted(native.iterdir())),
        encoding="utf-8",
    )
    save(evidence / "github-artifacts.json", artifacts)
    result = {
        "schema_version": 1,
        "repository": REPOSITORY,
        "version": args.version,
        "source_sha": args.source_sha,
        "qualification_sha": args.qualification_sha,
        "tree": tree,
        "controller_sha": control,
        "preparation_run_id": int(os.environ["GITHUB_RUN_ID"]),
        "preparation_run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
        "release_notes": git(
            root,
            "show",
            f"{args.source_sha}:action_server/docs/ACTIONS_RUNTIME_CHANGELOG.md",
        )
        .split(f"## actions-runtime-{args.version}\n", 1)[1]
        .split("\n## ", 1)[0]
        .strip(),
        "native_signing": "unsigned; all signing credentials required absent by preparation workflow",
        "files": {
            path.relative_to(args.output).as_posix(): {
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
            for path in sorted(args.output.rglob("*"))
            if path.is_file()
        },
    }
    save(args.output / MANIFEST, result)
    verify_files(args.output, result)
    print(
        f"Prepared {args.version} from {args.source_sha}; {MANIFEST} SHA-256: {sha256(args.output / MANIFEST)}"
    )


def verify(args):
    root = args.root.resolve()
    controller(root, ".github/workflows/runtime-release-publish.yml")
    require(
        re.fullmatch(r"[0-9a-f]{64}", args.manifest_sha256),
        "reviewed manifest SHA-256 required",
    )
    require(
        sha256(args.bundle / MANIFEST) == args.manifest_sha256,
        "reviewed manifest digest mismatch",
    )
    manifest = json.loads((args.bundle / MANIFEST).read_text())
    require(
        manifest["schema_version"] == 1 and manifest["repository"] == REPOSITORY,
        "bundle schema/repository mismatch",
    )
    require(
        manifest["preparation_run_id"] == args.preparation_run_id
        and manifest["source_sha"] == args.source_sha
        and manifest["version"] == args.version,
        "reviewed preparation inputs mismatch",
    )
    require(
        check_source(
            root,
            manifest["source_sha"],
            manifest["qualification_sha"],
            manifest["version"],
        )
        == manifest["tree"],
        "bundle tree mismatch",
    )
    run = api(f"repos/{REPOSITORY}/actions/runs/{args.preparation_run_id}")
    require(
        run["path"] == PREPARE_WORKFLOW
        and run["event"] == "workflow_dispatch"
        and run["head_branch"] == "community"
        and run["head_sha"] == manifest["controller_sha"]
        and run["run_attempt"] == manifest["preparation_run_attempt"]
        and run["conclusion"] == "success",
        "preparation run identity/state mismatch; never rerun an original preparation",
    )
    verify_files(args.bundle, manifest)
    verify_artifacts(args.bundle / "pypi")
    native_names = {
        f"actions-runtime-{args.version}-{suffix}"
        for _, suffix, _ in PLATFORMS.values()
    } | {f"actions-runtime-{args.version}-sha256.txt"}
    require(
        {p.name for p in (args.bundle / "native").iterdir()} == native_names,
        "native release inventory mismatch",
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "twine",
            "check",
            "--strict",
            *[
                str(path)
                for path in sorted((args.bundle / "pypi").iterdir())
                if path.suffix in {".whl", ".gz"}
            ],
        ],
        check=True,
    )
    return manifest


def publish(args):
    manifest = verify(args)
    release, tag = release_state(args.version)
    native_missing = reconcile_release(manifest, args.manifest_sha256, release, tag)
    package_missing = reconcile_pypi(
        manifest, pypi_files(args.version), owned=release is not None
    )
    print(
        json.dumps(
            {
                "mode": args.command,
                "source_sha": args.source_sha,
                "missing_native": native_missing,
                "missing_pypi": package_missing,
            },
            sort_keys=True,
        )
    )
    if args.command == "validate":
        return
    require(
        os.environ.get("RUNTIME_TOKEN"),
        "PYPI_TOKEN_ACTIONS_RUNTIME is required before any publication write",
    )
    # Reserve a private, source/manifest-bound draft before the first PyPI write.
    # An uncertain write is never retried here: a rerun first reconciles actual state.
    if release is None:
        release = api(
            f"repos/{REPOSITORY}/releases",
            method="POST",
            data={
                "tag_name": f"actions-runtime-{args.version}",
                "target_commitish": args.source_sha,
                "name": f"Actions Runtime {args.version}",
                "body": release_body(manifest, args.manifest_sha256),
                "draft": True,
                "prerelease": False,
            },
        )
        reconcile_release(manifest, args.manifest_sha256, release, None)
    for name in native_missing:
        endpoint = f"https://uploads.github.com/repos/{REPOSITORY}/releases/{release['id']}/assets?name={urllib.parse.quote(name)}"
        subprocess.run(
            [
                "gh",
                "api",
                "--method",
                "POST",
                endpoint,
                "-H",
                "Content-Type: application/octet-stream",
                "--input",
                str(args.bundle / "native" / name),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    release = api(f"repos/{REPOSITORY}/releases/{release['id']}")
    require(
        not reconcile_release(manifest, args.manifest_sha256, release, tag),
        "native draft assets are incomplete",
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("TWINE_")
        and key not in {"RUNTIME_TOKEN", "PYPI", "GH_TOKEN", "GITHUB_TOKEN"}
    }
    env.update(
        TWINE_USERNAME="__token__",
        TWINE_PASSWORD=os.environ["RUNTIME_TOKEN"],
        TWINE_NON_INTERACTIVE="1",
    )
    for name in package_missing:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "twine",
                "upload",
                "--repository-url",
                "https://upload.pypi.org/legacy/",
                str(args.bundle / "pypi" / name),
            ],
            check=True,
            env=env,
        )
    require(
        not reconcile_pypi(manifest, pypi_files(args.version), owned=True),
        "PyPI inventory is not complete; retain the draft and rerun this publication",
    )
    release, tag = release_state(args.version)
    require(
        release is not None
        and not reconcile_release(manifest, args.manifest_sha256, release, tag),
        "release changed during publication",
    )
    if tag is None:
        api(
            f"repos/{REPOSITORY}/git/refs",
            method="POST",
            data={
                "ref": f"refs/tags/actions-runtime-{args.version}",
                "sha": args.source_sha,
            },
        )
    if release["draft"]:
        api(
            f"repos/{REPOSITORY}/releases/{release['id']}",
            method="PATCH",
            data={"draft": False, "make_latest": "true"},
        )
    release, tag = release_state(args.version)
    require(
        release is not None
        and release["draft"] is False
        and not reconcile_release(manifest, args.manifest_sha256, release, tag),
        "publication final verification failed",
    )
    print(
        f"Published immutable actions-runtime-{args.version} from {args.source_sha}; exact bundle {args.manifest_sha256}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "validate", "publish"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--qualification-sha")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--preparation-run-id", type=int)
    args = parser.parse_args()
    if args.command == "prepare":
        require(
            args.qualification_sha and args.output,
            "prepare requires qualification SHA and output",
        )
        prepare(args)
    else:
        require(
            args.bundle and args.preparation_run_id and args.manifest_sha256,
            "validation/publication requires the reviewed preparation bundle inputs",
        )
        publish(args)


if __name__ == "__main__":
    main()
