"""Task-owned common SQL fixtures for Foundry integration only."""

import os
from uuid import uuid4

import pytest


@pytest.fixture(params=["sqlite", "postgresql"])
def database_location(request, tmp_path):
    if request.param == "sqlite":
        yield tmp_path / "runtime.db"
        return
    base = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
    if not base:
        if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
            pytest.fail("owned PostgreSQL deployment fixture required")
        pytest.skip("owned PostgreSQL deployment fixture not configured")
    import psycopg
    from action_server_tests.test_database_shared import _postgresql_schema_url

    schema = "foundry_deployment_" + uuid4().hex
    owner = psycopg.connect(base, autocommit=True)
    try:
        owner.execute(f'CREATE SCHEMA "{schema}"')
        yield _postgresql_schema_url(base, schema)
    finally:
        try:
            owner.execute(f'DROP SCHEMA "{schema}" CASCADE')
        finally:
            owner.close()


@pytest.fixture
def foundry_package_store(tmp_path):
    import sys

    from actions.server.run_outputs.filesystem import FilesystemOutputProvider

    if sys.platform != "linux":
        pytest.skip("private filesystem Package storage is Linux-only")
    root = tmp_path / "package-objects"
    root.mkdir()
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with FilesystemOutputProvider(fd) as provider:
            yield provider
    finally:
        os.close(fd)


@pytest.fixture(autouse=True)
def retain_and_release_owned_compiler_views(request):
    """Bound an explicitly admitted task fixture without touching RCC artifacts.

    This is opt-in for the dedicated serial compiler gate. The exact prepared
    home must carry the task-owned marker; no developer/default home is pruned.
    """
    enabled = os.environ.get("ACTIONS_PACKAGE_COMPILER_OWNED_VIEW_CLEANUP") == "1"
    selected = request.node.path.name in {
        "test_foundry_package_registry_rcc.py",
        "test_reviewed_generated_rcc.py",
        "test_activated_generated_rcc.py",
    }
    yield
    if not enabled or not selected:
        return
    import hashlib
    import json
    import re
    import shutil
    import subprocess
    from pathlib import Path

    import psutil

    from actions.server.deployments.package_revision_compiler import (
        load_prepared_rcc_environment,
    )

    prepared = load_prepared_rcc_environment(
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
    )
    home = prepared.robocorp_home.resolve(strict=True)
    marker = home / ".actions-owned-compiler-fixture"
    if (
        marker.is_symlink()
        or marker.read_text() != "actions.task-owned-compiler-fixture/v1\n"
    ):
        pytest.fail("exact task-owned compiler-home cleanup admission required")
    views = home / "holotree"
    active = []
    for process in psutil.process_iter(["pid", "exe", "cwd"]):
        data = process.info
        if any(
            str(data.get(key) or "").startswith(str(views) + "/")
            for key in ("exe", "cwd")
        ):
            active.append(data["pid"])
    if active:
        pytest.fail(
            "owned compiler views still have active processes; cleanup not attempted"
        )
    identities = sorted(
        p.stem
        for p in views.glob("*.meta")
        if re.fullmatch(r"[0-9a-f]{7}_[0-9a-f]{7}_[0-9a-f]{8}", p.stem)
    )
    evidence = (
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_CLEANUP_EVIDENCE"])
        / hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:16]
    )
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = {
        "nodeid": request.node.nodeid,
        "home": str(home),
        "spaces": identities,
        "active_processes": active,
        "before_free_bytes": shutil.disk_usage(home).free,
        "retained": "immutable artifacts/catalog/source/build receipts/package caches",
    }
    for identity in identities:
        for suffix in (".meta", ".meta.info"):
            source = views / (identity + suffix)
            if source.is_file():
                shutil.copy2(source, evidence / source.name)
    environment = dict(os.environ, ROBOCORP_HOME=str(home), ACTIONS_HOME=str(home))
    command = [
        os.environ["ACTIONS_PACKAGE_COMPILER_RCC"],
        "holotree",
        "delete",
        *identities,
    ]
    if identities:
        with (evidence / "dryrun.log").open("wb") as log:
            dryrun = subprocess.run(
                [*command, "--dryrun"],
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
        receipt["dryrun_returncode"] = dryrun.returncode
        if dryrun.returncode == 0:
            with (evidence / "delete.log").open("wb") as log:
                result = subprocess.run(
                    command,
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=60,
                )
            receipt["returncode"] = result.returncode
    receipt["after_free_bytes"] = shutil.disk_usage(home).free
    receipt["remaining_selected_spaces"] = [
        identity for identity in identities if (views / identity).exists()
    ]
    (evidence / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if identities and (
        receipt.get("returncode") != 0 or receipt["remaining_selected_spaces"]
    ):
        pytest.fail(
            "owned RCC view cleanup failed; evidence retained, no fallback deletion"
        )
