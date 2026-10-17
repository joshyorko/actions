"""Retain exact reviewed Runtime bytes in independent workflow artifacts.

This command reads GitHub/PyPI and stages files only. It never creates a release,
tag, package or remote mutation. The branch-only workflow uploads its output.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import runtime_release_button as button


def backup_controller(root):
    button.require(
        os.environ.get("GITHUB_REPOSITORY") == button.REPOSITORY
        and os.environ.get("GITHUB_REF") == f"refs/heads/{button.BACKUP_BRANCH}"
        and os.environ.get("GITHUB_WORKFLOW_REF")
        == f"{button.REPOSITORY}/{button.BACKUP_WORKFLOW}@refs/heads/{button.BACKUP_BRANCH}",
        "archive requires the dedicated nonpublishing backup controller",
    )
    button.require(
        os.environ.get("GITHUB_RUN_ATTEMPT") == "1",
        "never rerun a backup; reseed a separate run from surviving bytes",
    )
    button.git(
        root,
        "fetch",
        "--no-tags",
        "origin",
        f"refs/heads/{button.BACKUP_BRANCH}:refs/remotes/origin/{button.BACKUP_BRANCH}",
    )
    head = button.git(root, "rev-parse", "HEAD")
    button.require(
        head
        == os.environ.get("GITHUB_WORKFLOW_SHA")
        == button.git(root, "rev-parse", f"origin/{button.BACKUP_BRANCH}"),
        "backup controller checkout is not current",
    )
    return head


def archive(args):
    root = args.root.resolve()
    control = backup_controller(root)
    button.require(not args.output.exists(), "archive output already exists")
    args.output.mkdir(parents=True)
    run = button.api(
        f"repos/{button.REPOSITORY}/actions/runs/{args.preparation_run_id}/attempts/1"
    )
    bundle = args.output / "bundle"
    if (
        run.get("path") == button.PREPARE_WORKFLOW
        and run.get("head_branch") == "community"
    ):
        metadata = button.download(
            run,
            f"runtime-release-bundle-{args.preparation_run_id}-1",
            bundle,
            retain_archive=True,
        )
        original_zip = bundle.with_suffix(".zip")
        source_kind = "original-preparation"
    else:
        button.require(
            run.get("path") == button.BACKUP_WORKFLOW
            and run.get("head_branch") == button.BACKUP_BRANCH,
            "archive source is not a canonical preparation or registered backup",
        )
        retained = args.output / "retained"
        metadata = button.download(
            run, f"runtime-release-archive-{args.preparation_run_id}-1", retained
        )
        button.require(
            {p.name for p in retained.iterdir()}
            == {"original-bundle.zip", "backup-receipt.json"}
            and all(
                p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1
                for p in retained.iterdir()
            ),
            "raw recovery archive inventory mismatch",
        )
        receipt_path = retained / "backup-receipt.json"
        button.require(
            receipt_path.stat().st_size <= 1024**2, "backup receipt bound exceeded"
        )
        prior = json.loads(receipt_path.read_text(encoding="utf-8"))
        button.require(
            prior.get("schema_version") == 1
            and prior.get("repository") == button.REPOSITORY
            and prior.get("manifest_sha256") == args.manifest_sha256
            and prior.get("source_sha") == args.source_sha
            and prior.get("version") == args.version,
            "raw recovery receipt identity mismatch",
        )
        record = button.recovery_record(root, args.manifest_sha256, prior)
        matches = [
            item
            for item in record["backups"]
            if item["run_id"] == args.preparation_run_id
        ]
        button.require(
            len(matches) == 1, "archive source is not in the reviewed recovery registry"
        )
        checked = button.verify_backup(record, matches[0], archive_only=True)["archive"]
        button.require(
            checked["id"] == metadata["id"] and checked["digest"] == metadata["digest"],
            "downloaded raw archive differs from registry",
        )
        original_zip = retained / "original-bundle.zip"
        button.require(
            button.sha256(original_zip)
            == prior.get("original_archive_sha256")
            == record["original_archive_sha256"],
            "original recovery ZIP digest mismatch",
        )
        button.extract_zip(original_zip, bundle)
        source_kind = "registered-raw-archive"
    staged = SimpleNamespace(**vars(args))
    staged.bundle = bundle
    manifest = button.verify_bundle(staged, require_backups=False)
    digest = button.sha256(original_zip)
    existing = button.recovery_record(
        root, args.manifest_sha256, manifest, required=False
    )
    button.require(
        existing is None or existing["original_archive_sha256"] == digest,
        "original ZIP differs from reviewed recovery registry",
    )
    archive_dir = args.output / "archive"
    archive_dir.mkdir()
    original_zip.replace(archive_dir / "original-bundle.zip")
    if (args.output / "retained").exists():
        shutil.rmtree(args.output / "retained")
    receipt = {
        "schema_version": 1,
        "repository": button.REPOSITORY,
        "preparation_run_id": manifest["preparation_run_id"],
        "preparation_run_attempt": manifest["preparation_run_attempt"],
        "manifest_sha256": args.manifest_sha256,
        "source_sha": manifest["source_sha"],
        "qualification_sha": manifest["qualification_sha"],
        "version": manifest["version"],
        "tree": manifest["tree"],
        "source_run_id": args.preparation_run_id,
        "source_kind": source_kind,
        "source_artifact": metadata,
        "original_archive_sha256": digest,
        "controller_sha": control,
        "publication_performed": False,
        "verified_members": len(manifest["files"]),
    }
    button.save(archive_dir / "backup-receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--preparation-run-id", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    archive(parser.parse_args())


if __name__ == "__main__":
    main()
