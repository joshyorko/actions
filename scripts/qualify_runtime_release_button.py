"""Exercise preparation and read-only validation; never dispatch publication.

This helper belongs only to the qualification branch, not the release candidate.
Its job token has contents:read/actions:write and no package credential.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = "joshyorko/actions"
PREPARE = "runtime-release-prepare.yml"
VALIDATE = "runtime-release-publish.yml"
REPORT = Path("qualification-report.json")


class QualificationError(ValueError):
    pass


def require(value, message):
    if not value:
        raise QualificationError(message)


def dispatch_input(kind, source, qualification, version, preparation=None, digest=None):
    require(re.fullmatch(r"[0-9a-f]{40}", source), "full source SHA required")
    require(
        re.fullmatch(r"[0-9a-f]{40}", qualification), "full qualification SHA required"
    )
    require(version == "1.0.4", "this qualification is scoped to1.0.4")
    if kind == "prepare":
        return PREPARE, {
            "source_sha": source,
            "qualification_sha": qualification,
            "expected_version": version,
        }
    require(
        kind == "validate", "only preparation/read-only validation may be dispatched"
    )
    require(isinstance(preparation, int) and preparation > 0, "preparation ID required")
    require(re.fullmatch(r"[0-9a-f]{64}", digest or ""), "manifest digest required")
    return VALIDATE, {
        "operation": "validate",
        "preparation_run_id": str(preparation),
        "source_sha": source,
        "expected_version": version,
        "manifest_sha256": digest,
    }


def api(path, *, method="GET", data=None, missing=False):
    require(path.startswith(f"repos/{REPO}/"), "repository scope mismatch")
    if method != "GET":
        require(
            method == "POST" and path in ALLOWED_WRITES,
            "write endpoint was not explicitly admitted",
        )
        if path.endswith(f"/{VALIDATE}/dispatches"):
            require(
                data.get("ref") == "community"
                and data.get("inputs", {}).get("operation") == "validate",
                "publication dispatch is forbidden",
            )
    command = ["gh", "api", "--method", method, path]
    if data is not None:
        command += ["--input", "-"]
    result = subprocess.run(
        command,
        input=json.dumps(data) if data is not None else None,
        text=True,
        capture_output=True,
    )
    if missing and result.returncode and "HTTP 404" in result.stderr:
        return None
    require(
        result.returncode == 0,
        f"API {method} failed at {path}; do not blindly retry a write",
    )
    return json.loads(result.stdout) if result.stdout.strip() else None


ALLOWED_WRITES = {
    f"repos/{REPO}/actions/workflows/{name}/dispatches" for name in (PREPARE, VALIDATE)
}


def snapshot(report):
    temporary = REPORT.with_suffix(".part")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(REPORT)


def latest_runs(workflow):
    return api(
        f"repos/{REPO}/actions/workflows/{workflow}/runs?event=workflow_dispatch&branch=community&per_page=100"
    )["workflow_runs"]


def select_run(runs, *, after, source, title):
    matches = [
        run
        for run in runs
        if run["id"] > after
        and run["head_sha"] == source
        and run["display_title"] == title
        and run["event"] == "workflow_dispatch"
        and run["head_branch"] == "community"
    ]
    require(
        len(matches) <= 1,
        "ambiguous dispatch outcome; inspect actual runs before any retry",
    )
    return matches[0] if matches else None


def dispatch(
    report,
    label,
    kind,
    source,
    qualification,
    version,
    *,
    preparation=None,
    digest=None,
):
    require(
        api(f"repos/{REPO}/git/ref/heads/community")["object"]["sha"] == source,
        "community moved; recheck source before dispatch",
    )
    workflow, inputs = dispatch_input(
        kind, source, qualification, version, preparation, digest
    )
    previous = max((run["id"] for run in latest_runs(workflow)), default=0)
    entry = {
        "label": label,
        "workflow": workflow,
        "inputs": inputs,
        "outcome": "not dispatched",
    }
    report["dispatches"].append(entry)
    snapshot(report)
    # Exactly one POST. A missing/lost response is reconciled by run lookup;
    # this helper never submits that dispatch again.
    entry["outcome"] = "dispatch response uncertain"
    snapshot(report)
    api(
        f"repos/{REPO}/actions/workflows/{workflow}/dispatches",
        method="POST",
        data={"ref": "community", "inputs": inputs},
    )
    entry["outcome"] = "dispatch accepted; locating run"
    snapshot(report)
    title = (
        f"{'Prepare' if kind == 'prepare' else 'validate'} Runtime {version} @ {source}"
    )
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        run = select_run(
            latest_runs(workflow), after=previous, source=source, title=title
        )
        if run:
            entry.update(
                run_id=run["id"], html_url=run["html_url"], outcome="run located"
            )
            snapshot(report)
            return run["id"]
        time.sleep(5)
    raise QualificationError(
        "accepted dispatch has no unique run yet; inspect uncertain outcome before retrying"
    )


def wait_run(run_id, *, attempt=1):
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        run = api(f"repos/{REPO}/actions/runs/{run_id}")
        if run["run_attempt"] == attempt and run["status"] == "completed":
            return run
        time.sleep(8)
    raise QualificationError(f"run{run_id} attempt{attempt} remains pending")


def result(report, label, run):
    record = {
        key: run[key]
        for key in (
            "id",
            "run_attempt",
            "head_sha",
            "head_branch",
            "event",
            "path",
            "status",
            "conclusion",
            "html_url",
        )
    }
    record["label"] = label
    report["runs"].append(record)
    snapshot(report)


def bundle(report, label, run_id, source, qualification, version):
    listing = api(f"repos/{REPO}/actions/runs/{run_id}/artifacts?per_page=100")[
        "artifacts"
    ]
    matches = [
        item for item in listing if item["name"] == f"runtime-release-bundle-{run_id}-1"
    ]
    require(
        len(matches) == 1 and not matches[0]["expired"],
        "original preparation artifact absent/ambiguous/expired",
    )
    artifact = matches[0]
    path = Path(os.environ["RUNNER_TEMP"]) / f"bundle-{run_id}.zip"
    with path.open("wb") as output:
        download = subprocess.run(
            ["gh", "api", f"repos/{REPO}/actions/artifacts/{artifact['id']}/zip"],
            stdout=output,
            stderr=subprocess.PIPE,
        )
    require(download.returncode == 0, "preparation bundle download failed")
    require(
        artifact["digest"]
        == "sha256:" + hashlib.file_digest(path.open("rb"), "sha256").hexdigest(),
        "GitHub ZIP digest mismatch",
    )
    with zipfile.ZipFile(path) as archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        require(
            len(entries) <= 2000
            and sum(entry.file_size for entry in entries) <= 2 * 1024**3,
            "bundle bounds exceeded",
        )
        require(
            len(entries) == len({entry.filename for entry in entries}),
            "duplicate bundle member",
        )
        require(
            archive.getinfo("release-bundle.json").file_size <= 1024**2,
            "manifest bound exceeded",
        )
        raw = archive.read("release-bundle.json")
        manifest = json.loads(raw)
        require(
            manifest["source_sha"] == source
            and manifest["qualification_sha"] == qualification
            and manifest["version"] == version
            and manifest["preparation_run_id"] == run_id
            and manifest["preparation_run_attempt"] == 1,
            "preparation identity mismatch",
        )
        require(
            {entry.filename for entry in entries}
            == set(manifest["files"]) | {"release-bundle.json"},
            "bundle inventory mismatch",
        )
        for name, expected in manifest["files"].items():
            with archive.open(name) as member:
                digest = hashlib.file_digest(member, "sha256").hexdigest()
            require(
                digest == expected["sha256"]
                and archive.getinfo(name).file_size == expected["size"],
                "bundle member integrity mismatch",
            )
    path.unlink()
    manifest_path = Path(f"{label}-release-bundle.json")
    manifest_path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    record = {
        "label": label,
        "run_id": run_id,
        "artifact_id": artifact["id"],
        "artifact_digest": artifact["digest"],
        "manifest_sha256": digest,
        "manifest_file": str(manifest_path),
        "source_sha": source,
        "qualification_sha": qualification,
        "version": version,
    }
    report["bundles"].append(record)
    snapshot(report)
    return digest, artifact["digest"]


def validate(
    report,
    label,
    source,
    qualification,
    version,
    preparation,
    digest,
    *,
    expected="success",
):
    run_id = dispatch(
        report,
        label,
        "validate",
        source,
        qualification,
        version,
        preparation=preparation,
        digest=digest,
    )
    run = wait_run(run_id)
    result(report, label, run)
    require(run["conclusion"] == expected, f"validation {label} had unexpected outcome")
    jobs = api(f"repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100")["jobs"]
    writer = [job for job in jobs if job["name"] == "publish"]
    require(
        len(writer) == 1 and writer[0]["conclusion"] == "skipped",
        "publication job must remain skipped",
    )
    if expected == "failure":
        checker = next(job for job in jobs if job["name"] == "validate")
        logs = subprocess.run(
            ["gh", "api", f"repos/{REPO}/actions/jobs/{checker['id']}/logs"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        require(
            "reviewed manifest digest mismatch" in logs,
            "negative validation failed for an unexpected reason",
        )
    return run_id


def assert_log_marker(run_id, job_name, marker):
    jobs = api(f"repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100")["jobs"]
    job = next(job for job in jobs if job["name"] == job_name)
    logs = subprocess.run(
        ["gh", "api", f"repos/{REPO}/actions/jobs/{job['id']}/logs"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    require(marker in logs, "negative control failed for an unexpected reason")


def publication_absent(version):
    require(
        api(f"repos/{REPO}/git/ref/tags/actions-runtime-{version}", missing=True)
        is None,
        "release tag unexpectedly exists",
    )
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/actions-runtime/{version}/json", timeout=30
        ):
            raise QualificationError("PyPI version unexpectedly exists")
    except urllib.error.HTTPError as error:
        require(error.code == 404, "unexpected PyPI query failure")


def main():
    source = os.environ["EXPECTED_SOURCE_SHA"]
    qualification = "9e8cfd7caa602031db4eba75f545b1211f882561"
    version = "1.0.4"
    report = {
        "status": "RUNNING",
        "source_sha": source,
        "qualification_sha": qualification,
        "version": version,
        "dispatches": [],
        "runs": [],
        "bundles": [],
        "publication_performed": False,
    }
    snapshot(report)
    try:
        publication_absent(version)
        production = dispatch(
            report,
            "owner-handoff-preparation",
            "prepare",
            source,
            qualification,
            version,
        )
        run = wait_run(production)
        result(report, "owner-handoff-preparation", run)
        require(run["conclusion"] == "success", "owner preparation failed")
        production_digest, _ = bundle(
            report, "owner-handoff", production, source, qualification, version
        )
        rehearsal = dispatch(
            report,
            "retry-rehearsal-preparation",
            "prepare",
            source,
            qualification,
            version,
        )
        run = wait_run(rehearsal)
        result(report, "retry-rehearsal-preparation", run)
        require(run["conclusion"] == "success", "rehearsal preparation failed")
        rehearsal_digest, artifact_digest = bundle(
            report, "retry-rehearsal", rehearsal, source, qualification, version
        )
        endpoint = f"repos/{REPO}/actions/runs/{rehearsal}/rerun"
        ALLOWED_WRITES.add(endpoint)
        report["rehearsal_rerun"] = {
            "run_id": rehearsal,
            "requested_attempt": 2,
            "outcome": "request uncertain",
        }
        snapshot(report)
        api(endpoint, method="POST")
        report["rehearsal_rerun"]["outcome"] = "accepted"
        snapshot(report)
        rerun = wait_run(rehearsal, attempt=2)
        result(report, "preparation-rerun-refused-as-expected", rerun)
        require(
            rerun["conclusion"] == "failure",
            "preparation must refuse rebuilding on a rerun",
        )
        assert_log_marker(rehearsal, "prepare", "never rerun preparation")
        _, retained_digest = bundle(
            report,
            "retry-rehearsal-after-refusal",
            rehearsal,
            source,
            qualification,
            version,
        )
        require(
            retained_digest == artifact_digest,
            "original artifact changed after refused rerun",
        )
        validate(
            report,
            "original-attempt-survives-refused-rerun",
            source,
            qualification,
            version,
            rehearsal,
            rehearsal_digest,
        )
        validate(
            report,
            "owner-validation-first",
            source,
            qualification,
            version,
            production,
            production_digest,
        )
        validate(
            report,
            "owner-validation-repeat",
            source,
            qualification,
            version,
            production,
            production_digest,
        )
        wrong = ("0" if production_digest[0] != "0" else "1") + production_digest[1:]
        validate(
            report,
            "wrong-reviewed-digest-refused",
            source,
            qualification,
            version,
            production,
            wrong,
            expected="failure",
        )
        publication_absent(version)
        report.update(
            status="PASS",
            publication_state_unchanged=True,
            owner_handoff={
                "preparation_run_id": production,
                "source_sha": source,
                "expected_version": version,
                "manifest_sha256": production_digest,
            },
        )
    except Exception as error:
        report.update(
            status="FAILED", error_type=type(error).__name__, error=str(error)
        )
        raise
    finally:
        snapshot(report)


if __name__ == "__main__":
    main()
