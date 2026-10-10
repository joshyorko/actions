"""Contracts for source-bound RCC metadata inspection of one v2 fixture."""

from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from actions.server.deployments import source_manifest
from actions.server.deployments.ids import CapabilityId, PackageId


PACKAGE_ID = PackageId.model_validate("12345678-1234-5678-1234-567812345678")
SPEC_DIGEST = "sha256:" + "a" * 64
ARTIFACT_DIGEST = "sha256:" + "b" * 64
PROVIDER = "inspection-fixture-provider"
PACKAGE_YAML = (
    b"version: 0.1\nspec-version: v2\ndependencies:\n"
    b"  conda-forge:\n    - python=3.12.15\n"
    b"  pypi:\n    - actions-core=1.0.2\n"
)
ACTION_SOURCE = (
    b"from actions import action\n\n"
    b"@action\n"
    b"def query(value: str) -> str:\n"
    b"    return value\n"
)
SOURCE_CONTENTS = {"action.py": ACTION_SOURCE, "package.yaml": PACKAGE_YAML}


def _fixture(tmp_path: Path):
    source = tmp_path / "fixture-source"
    source.mkdir(mode=0o700)
    for name, content in SOURCE_CONTENTS.items():
        (source / name).write_bytes(content)
        (source / name).chmod(0o644)

    output = tmp_path / "inspection-output"
    output.mkdir(mode=0o700)
    operations = tmp_path / "operations"
    operations.mkdir(mode=0o700)

    fake_site = tmp_path / "fake-managed-site"
    (fake_site / "sitecustomize.py").parent.mkdir(parents=True, exist_ok=True)
    (fake_site / "sitecustomize.py").write_text(
        f"import sys; sys.prefix = {str(fake_site)!r}\n", encoding="utf-8"
    )
    fake_actions = fake_site / "actions"
    fake_actions.mkdir(parents=True)
    (fake_actions / "__init__.py").write_text("from . import cli\n", encoding="utf-8")
    action_file = (
        "from pathlib import Path\n"
        "import json, os\n"
        "def main(args):\n"
        "    assert args[0] == 'metadata'\n"
        "    package = Path(args[1]).resolve()\n"
        "    source = package / 'action.py'\n"
        "    if os.environ.get('FIXTURE_MUTATE_SOURCE') == '1':\n"
        "        source.write_bytes(source.read_bytes() + b'# changed\\n')\n"
        "    if os.environ.get('FIXTURE_ADD_SOURCE') == '1':\n"
        "        (package / 'extra.py').write_text('extra = True\\n')\n"
        "    filename = str(source if os.environ.get('FIXTURE_OUTSIDE_PATH') != '1' else Path('/etc/passwd'))\n"
        "    name = os.environ.get('FIXTURE_ACTION_NAME', 'query')\n"
        "    print(json.dumps({'actions': [{'name': name, 'file': filename, 'docs': 'Returns the value.', 'input_schema': {'type': 'object'}, 'output_schema': {'type': 'string'}}]}))\n"
    )
    (fake_actions / "cli.py").write_text(action_file, encoding="utf-8")
    dist_info = fake_site / "actions_core-1.0.2.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: actions-core\nVersion: 1.0.2\n\n",
        encoding="utf-8",
    )
    (dist_info / "RECORD").write_text("actions/__init__.py,,\n", encoding="utf-8")

    fake_rcc = tmp_path / "rcc-fixture"
    fake_rcc.write_text(
        "#!" + sys.executable + "\n"
        "import json, os, signal, subprocess, sys, time\n"
        f"FAKE_SITE = {str(fake_site)!r}\n"
        f"SPEC = {SPEC_DIGEST!r}\n"
        f"ARTIFACT = {ARTIFACT_DIGEST!r}\n"
        "args = sys.argv[1:]\n"
        "if args == ['--version']:\n"
        "    if os.environ.get('FIXTURE_RCC_MODE') == 'prep-timeout':\n"
        "        signal.signal(signal.SIGTERM, lambda *_: None)\n"
        "        subprocess.run([sys.executable, '-c', 'import time; time.sleep(10)'])\n"
        "    print('v18.19.3')\n"
        "elif args[:2] == ['env', 'publish']:\n"
        "    print(json.dumps({'specificationDigest': SPEC, 'artifactDigest': ARTIFACT}))\n"
        "elif args[:2] == ['env', 'acquire']:\n"
        "    print(json.dumps({'artifactDigest': ARTIFACT, 'verification': {'valid': True}}))\n"
        "elif args[:2] == ['env', 'exec']:\n"
        "    mode = os.environ.get('FIXTURE_RCC_MODE', '')\n"
        "    if mode in ('timeout', 'retain-pipe'): signal.signal(signal.SIGTERM, lambda *_: None)\n"
        "    if mode == 'output':\n"
        "        os.write(1, b'x' * (2 * 1024 * 1024))\n"
        "        raise SystemExit(0)\n"
        "    if mode == 'retain-pipe':\n"
        "        subprocess.run([sys.executable, '-c', 'import time; time.sleep(10)'])\n"
        "    separator = args.index('--')\n"
        "    command = args[separator + 1:]\n"
        "    receipt_path = args[args.index('--receipt-file') + 1]\n"
        "    child_env = dict(os.environ)\n"
        "    child_env['PYTHONPATH'] = FAKE_SITE\n"
        "    if mode == 'timeout':\n"
        "        command = [sys.executable, '-c', 'import time; time.sleep(10)']\n"
        "    child = subprocess.run([sys.executable, *command[1:]], cwd=os.getcwd(), env=child_env, check=False)\n"
        "    with open(receipt_path, 'w', encoding='utf-8') as receipt:\n"
        "        json.dump({'artifactDigest': ARTIFACT, 'verification': {'valid': True}, 'leaseId': 'fixture-lease'}, receipt)\n"
        "    raise SystemExit(child.returncode)\n"
        "else:\n"
        "    raise SystemExit('unexpected RCC invocation: ' + repr(args))\n",
        encoding="utf-8",
    )
    fake_rcc.chmod(fake_rcc.stat().st_mode | stat.S_IXUSR)
    return source, output, operations, fake_rcc


def _inspect(source, output, operations, rcc, *, timeout_seconds=15):
    from actions.server.deployments.package_compiler import DeclaredAction
    from actions.server.deployments.rcc_inspection import inspect_controlled_fixture

    entries = tuple(
        source_manifest.SuppliedSourceEntry(path, "file", content, 0o644)
        for path, content in SOURCE_CONTENTS.items()
    )
    return inspect_controlled_fixture(
        source_root=source,
        operation_parent=operations,
        output_directory=output,
        rcc_location=rcc,
        package_id=PACKAGE_ID,
        declared_paths=("action.py", "package.yaml"),
        protected_paths=("package.yaml",),
        source_entries=entries,
        declared_actions=(
            DeclaredAction(CapabilityId.model_validate("query"), "action.py", "query"),
        ),
        provider=PROVIDER,
        timeout_seconds=timeout_seconds,
    )


def test_inspects_exact_staged_fixture_through_bounded_rcc_and_compiles_proposal(
    tmp_path, monkeypatch
):
    source, output, operations, rcc = _fixture(tmp_path)
    monkeypatch.setenv("FIXTURE_MUTATE_SOURCE", "0")
    monkeypatch.setenv("FIXTURE_OUTSIDE_PATH", "0")

    declaration = _inspect(source, output, operations, rcc)

    assert declaration.compilation.inspection_status == "not_run"
    assert declaration.observation.status == "PASS"
    assert declaration.observation.rcc_version == "v18.19.3"
    assert declaration.observation.specification_digest == SPEC_DIGEST
    assert declaration.observation.artifact_digest == ARTIFACT_DIGEST
    assert declaration.observation.provider_reference == PROVIDER
    assert declaration.observation.core_version == "1.0.2"
    assert (
        "fake-managed-site/actions/__init__.py"
        in declaration.observation.core_module_origin
    )
    assert "fake-managed-site" in declaration.observation.core_distribution_root
    assert declaration.observation.core_distribution_record_sha256
    assert declaration.observation.core_sys_prefix
    assert declaration.observation.exit_code == 0
    assert declaration.observation.cleanup.descendant_reap_complete
    assert declaration.observation.source_inventory_sha256
    assert declaration.observation.metadata_sha256
    assert declaration.observation.receipt_sha256
    assert declaration.observation.operation_cleanup_complete
    assert sorted(path.name for path in source.iterdir()) == [
        "action.py",
        "package.yaml",
    ]
    assert sorted(path.name for path in output.iterdir())
    assert list(operations.iterdir()) == []


@pytest.mark.parametrize(
    ("environment", "value", "message"),
    [
        ("FIXTURE_MUTATE_SOURCE", "1", "staged source changed during RCC inspection"),
        ("FIXTURE_OUTSIDE_PATH", "1", "escapes staged fixture"),
        ("FIXTURE_ACTION_NAME", "renamed", "do not map exactly to declaration"),
        ("FIXTURE_ADD_SOURCE", "1", "tree differs from complete declaration"),
    ],
)
def test_rejects_source_drift_and_metadata_paths_outside_fixture(
    tmp_path, monkeypatch, environment, value, message
):
    source, output, operations, rcc = _fixture(tmp_path)
    monkeypatch.setenv(environment, value)
    with pytest.raises(ValueError, match=message):
        _inspect(source, output, operations, rcc)
    assert list(operations.iterdir()) == []


def test_timeout_reaps_rcc_wrapper_and_descendant(tmp_path, monkeypatch):
    source, output, operations, rcc = _fixture(tmp_path)
    monkeypatch.setenv("FIXTURE_RCC_MODE", "timeout")
    with pytest.raises(TimeoutError, match="cleanup_complete=True"):
        _inspect(source, output, operations, rcc, timeout_seconds=1)
    assert list(operations.iterdir()) == []


def test_caps_rcc_process_output(tmp_path, monkeypatch):
    source, output, operations, rcc = _fixture(tmp_path)
    monkeypatch.setenv("FIXTURE_RCC_MODE", "output")
    with pytest.raises(ValueError, match="output exceeds its bound"):
        _inspect(source, output, operations, rcc)
    assert list(operations.iterdir()) == []


def test_timeout_kills_child_that_retains_process_pipes(tmp_path, monkeypatch):
    source, output, operations, rcc = _fixture(tmp_path)
    monkeypatch.setenv("FIXTURE_RCC_MODE", "retain-pipe")
    with pytest.raises(TimeoutError, match="cleanup_complete=True"):
        _inspect(source, output, operations, rcc, timeout_seconds=1)
    assert list(operations.iterdir()) == []


def test_preparation_timeout_cleans_process_tree(tmp_path, monkeypatch):
    source, output, operations, rcc = _fixture(tmp_path)
    monkeypatch.setenv("FIXTURE_RCC_MODE", "prep-timeout")
    with pytest.raises(TimeoutError, match="RCC preparation command timed out"):
        _inspect(source, output, operations, rcc, timeout_seconds=1)
    assert list(operations.iterdir()) == []
