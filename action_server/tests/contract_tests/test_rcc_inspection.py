"""Contracts for source-bound RCC metadata inspection of one v2 fixture."""

from __future__ import annotations

import stat
import sys
import hashlib
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


def test_private_inspection_environment_preserves_network_context(tmp_path, monkeypatch):
    from actions.server.deployments.rcc_inspection import _private_environment

    proxy_names = (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "http_proxy", "https_proxy", "all_proxy",
    )
    ca_names = (
        "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE", "PIP_CERT", "NODE_EXTRA_CA_CERTS",
    )
    for name in proxy_names + ca_names + ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    expected = {
        "HTTP_PROXY": "http://upper-http-proxy.invalid:8080",
        "HTTPS_PROXY": "http://upper-https-proxy.invalid:8080",
        "ALL_PROXY": "socks5://upper-all-proxy.invalid:1080",
        "http_proxy": "http://lower-http-proxy.invalid:8080",
        "https_proxy": "http://lower-https-proxy.invalid:8080",
        "all_proxy": "socks5://lower-all-proxy.invalid:1080",
        "SSL_CERT_FILE": "/configured/ca-bundle.pem",
        "SSL_CERT_DIR": "/configured/ca-directory",
        "REQUESTS_CA_BUNDLE": "/configured/requests-ca.pem",
        "CURL_CA_BUNDLE": "/configured/curl-ca.pem",
        "PIP_CERT": "/configured/pip-ca.pem",
        "NODE_EXTRA_CA_CERTS": "/configured/node-ca.pem",
        "NO_PROXY": "service.internal,127.0.0.1",
        "no_proxy": "other.internal,localhost",
    }
    for name, value in expected.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("UNRELATED_INSPECTION_SECRET", "must-not-be-forwarded")

    operation_root = tmp_path / "operation"
    operation_root.mkdir(mode=0o700)
    env = _private_environment(operation_root)

    assert {name: env[name] for name in proxy_names + ca_names} == {
        name: value for name, value in expected.items() if name in proxy_names + ca_names
    }
    assert env["NO_PROXY"] == env["no_proxy"] == (
        "service.internal,127.0.0.1,other.internal,localhost,::1"
    )
    assert "UNRELATED_INSPECTION_SECRET" not in env
    assert env["HOME"] == str(operation_root / "home")
    assert env["ROBOCORP_HOME"] == str(operation_root / "rcc-home")


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
        "import os, sys; sys.prefix = os.environ['FIXTURE_PREFIX']; "
        "sys.executable = os.environ['FIXTURE_PYTHON']\n",
        encoding="utf-8",
    )
    config_file = tmp_path / "fixture-config.json"
    config_file.write_text("{}", encoding="utf-8")
    fake_actions = fake_site / "actions"
    fake_actions.mkdir(parents=True)
    (fake_actions / "__init__.py").write_text("from . import cli\n", encoding="utf-8")
    action_file = (
        "from pathlib import Path\n"
        "import json, os\n"
        f"CONFIG = Path({str(config_file)!r})\n"
        "def main(args, exit=True):\n"
        "    assert args[0] == 'metadata'\n"
        "    if exit: raise SystemExit(0)\n"
        "    assert 'FIXTURE_SECRET_SENTINEL' not in os.environ\n"
        "    config = json.loads(CONFIG.read_text())\n"
        "    package = Path(args[1]).resolve()\n"
        "    source = package / 'action.py'\n"
        "    if config.get('mutate_source'):\n"
        "        source.write_bytes(source.read_bytes() + b'# changed\\n')\n"
        "    if config.get('add_source'):\n"
        "        (package / 'extra.py').write_text('extra = True\\n')\n"
        "    filename = str(source if not config.get('outside_path') else Path('/etc/passwd'))\n"
        "    name = config.get('action_name', 'query')\n"
        "    print(json.dumps({'actions': [{'name': name, 'file': filename, 'docs': 'Returns the value.', 'input_schema': {'type': 'object'}, 'output_schema': {'type': 'string'}}]}))\n"
        "    return 0\n"
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
        "import json, os, shutil, signal, subprocess, sys\n"
        f"FAKE_SITE = {str(fake_site)!r}\n"
        f"CONFIG = {str(config_file)!r}\n"
        f"SPEC = {SPEC_DIGEST!r}\n"
        f"ARTIFACT = {ARTIFACT_DIGEST!r}\n"
        "args = sys.argv[1:]\n"
        "config = json.loads(open(CONFIG, encoding='utf-8').read())\n"
        "mode = config.get('mode', '')\n"
        "if args == ['--version']:\n"
        "    if mode == 'prep-timeout':\n"
        "        signal.signal(signal.SIGTERM, lambda *_: None)\n"
        "        subprocess.run([sys.executable, '-c', 'import time; time.sleep(10)'])\n"
        "    print('v18.19.3')\n"
        "elif args[:2] == ['env', 'publish']:\n"
        "    print(json.dumps({'specificationDigest': SPEC, 'artifactDigest': ARTIFACT}))\n"
        "elif args[:2] == ['env', 'acquire']:\n"
        "    print(json.dumps({'artifactDigest': ARTIFACT, 'verification': {'valid': True}}))\n"
        "elif args[:2] == ['env', 'exec']:\n"
        "    if mode in ('timeout', 'retain-pipe'): signal.signal(signal.SIGTERM, lambda *_: None)\n"
        "    if mode == 'output':\n"
        "        os.write(1, b'x' * (2 * 1024 * 1024))\n"
        "        raise SystemExit(0)\n"
        "    if mode == 'retain-pipe':\n"
        "        subprocess.run([sys.executable, '-c', 'import time; time.sleep(10)'])\n"
        "    separator = args.index('--')\n"
        "    command = args[separator + 1:]\n"
        "    receipt_path = args[args.index('--receipt-file') + 1]\n"
        "    runtime = os.path.join(os.environ['ROBOCORP_HOME'], 'fixture-materialization')\n"
        "    site = os.path.join(runtime, 'lib', 'python3.12', 'site-packages')\n"
        "    fake_bin = os.path.join(runtime, 'bin')\n"
        "    os.makedirs(fake_bin, mode=0o700)\n"
        "    shutil.copytree(FAKE_SITE, site)\n"
        "    python_path = os.path.join(fake_bin, 'python')\n"
        "    with open(python_path, 'w', encoding='utf-8') as shim: shim.write('#!/bin/sh\\nexec ' + sys.executable + ' \"$@\"\\n')\n"
        "    os.chmod(python_path, 0o700)\n"
        "    child_env = dict(os.environ)\n"
        "    child_env['PATH'] = fake_bin + os.pathsep + child_env['PATH']\n"
        "    child_env['PYTHONPATH'] = site\n"
        "    child_env['FIXTURE_PREFIX'] = os.path.join(os.path.dirname(runtime), 'wrong-prefix') if config.get('wrong_prefix') else runtime\n"
        "    child_env['FIXTURE_PYTHON'] = python_path\n"
        "    if mode == 'timeout':\n"
        "        command = ['python', '-c', 'import time; time.sleep(10)']\n"
        "    assert command[0] == 'python', 'inspection must use managed interpreter command'\n"
        "    child = subprocess.run(command, cwd=runtime, env=child_env, check=False)\n"
        "    with open(receipt_path, 'w', encoding='utf-8') as receipt:\n"
        "        receipt_materialization = '/tmp' if config.get('receipt_outside') else runtime\n"
        "        materialization_id = '' if config.get('missing_materialization_id') else 'fixture-materialization-id'\n"
        "        json.dump({'artifactDigest': ARTIFACT, 'verification': {'valid': True}, 'leaseId': 'fixture-lease', 'materializationId': materialization_id, 'path': receipt_materialization, 'status': config.get('receipt_status', 'completed'), 'exitCode': config.get('receipt_exit_code', child.returncode)}, receipt)\n"
        "    raise SystemExit(child.returncode)\n"
        "else:\n"
        "    raise SystemExit('unexpected RCC invocation: ' + repr(args))\n",
        encoding="utf-8",
    )
    fake_rcc.chmod(fake_rcc.stat().st_mode | stat.S_IXUSR)
    return source, output, operations, fake_rcc


def _configure(rcc: Path, **values) -> None:
    config = rcc.parent / "fixture-config.json"
    config.write_text(__import__("json").dumps(values), encoding="utf-8")


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
    sibling = operations / "rcc-inspect-unrelated"
    sibling.mkdir(mode=0o700)
    monkeypatch.setenv("FIXTURE_SECRET_SENTINEL", "must-not-enter-rcc")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy-secret.invalid:8080")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/private/configured-ca.pem")
    _configure(rcc)

    declaration = _inspect(source, output, operations, rcc)

    assert declaration.compilation.inspection_status == "not_run"
    assert declaration.observation.status == "PASS"
    assert declaration.observation.rcc_version == "v18.19.3"
    assert declaration.observation.specification_digest == SPEC_DIGEST
    assert declaration.observation.artifact_digest == ARTIFACT_DIGEST
    assert declaration.observation.provider_reference == PROVIDER
    assert declaration.observation.core_version == "1.0.2"
    assert (
        "fixture-materialization/lib/python3.12/site-packages/actions/__init__.py"
        in declaration.observation.core_module_origin
    )
    assert "fixture-materialization/lib/python3.12/site-packages" in declaration.observation.core_distribution_root
    assert declaration.observation.core_distribution_record_sha256
    assert declaration.observation.core_sys_prefix
    assert declaration.observation.managed_python.endswith("fixture-materialization/bin/python")
    assert declaration.observation.managed_prefix.endswith("fixture-materialization")
    assert declaration.observation.materialization_path == declaration.observation.managed_prefix
    assert declaration.observation.materialization_id == "fixture-materialization-id"
    assert declaration.observation.materialization_cwd == declaration.observation.materialization_path
    assert declaration.observation.receipt_path.startswith(str(output))
    assert declaration.observation.exit_code == 0
    assert declaration.observation.cleanup.descendant_reap_complete
    assert declaration.observation.source_inventory_sha256
    expected_inventory = source_manifest.validate_proposed_inventory(
        tuple(
            source_manifest.SuppliedSourceEntry(path, "file", content, 0o644)
            for path, content in SOURCE_CONTENTS.items()
        ),
        protected_input_names=("package.yaml",),
    )
    assert declaration.observation.source_inventory_sha256 == hashlib.sha256(
        expected_inventory.canonical_json
    ).hexdigest()
    assert declaration.observation.metadata_sha256
    assert declaration.observation.receipt_sha256
    assert declaration.observation.operation_cleanup_complete
    assert "http://proxy-secret.invalid:8080" not in repr(declaration.observation)
    assert "/private/configured-ca.pem" not in repr(declaration.observation)
    assert sorted(path.name for path in source.iterdir()) == [
        "action.py",
        "package.yaml",
    ]
    assert sorted(path.name for path in output.iterdir())
    assert list(operations.iterdir()) == [sibling]


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
    _configure(rcc, **{
        "FIXTURE_MUTATE_SOURCE": {"mutate_source": True},
        "FIXTURE_OUTSIDE_PATH": {"outside_path": True},
        "FIXTURE_ACTION_NAME": {"action_name": "renamed"},
        "FIXTURE_ADD_SOURCE": {"add_source": True},
    }[environment])
    with pytest.raises(ValueError, match=message):
        _inspect(source, output, operations, rcc)
    assert list(operations.iterdir()) == []


def test_timeout_reaps_rcc_wrapper_and_descendant(tmp_path, monkeypatch):
    source, output, operations, rcc = _fixture(tmp_path)
    _configure(rcc, mode="timeout")
    with pytest.raises(TimeoutError, match="cleanup_complete=True"):
        _inspect(source, output, operations, rcc, timeout_seconds=1)
    assert list(operations.iterdir()) == []


def test_caps_rcc_process_output(tmp_path, monkeypatch):
    source, output, operations, rcc = _fixture(tmp_path)
    _configure(rcc, mode="output")
    with pytest.raises(ValueError, match="output exceeds its byte bound"):
        _inspect(source, output, operations, rcc)
    assert list(operations.iterdir()) == []


def test_timeout_kills_child_that_retains_process_pipes(tmp_path, monkeypatch):
    source, output, operations, rcc = _fixture(tmp_path)
    _configure(rcc, mode="retain-pipe")
    with pytest.raises(TimeoutError, match="cleanup_complete=True"):
        _inspect(source, output, operations, rcc, timeout_seconds=1)
    assert list(operations.iterdir()) == []


@pytest.mark.parametrize(
    "receipt_values",
    [
        {"receipt_status": "failed"},
        {"receipt_exit_code": True},
        {"receipt_exit_code": 1},
    ],
)
def test_rejects_receipt_that_does_not_confirm_success(tmp_path, receipt_values):
    source, output, operations, rcc = _fixture(tmp_path)
    _configure(rcc, **receipt_values)
    with pytest.raises(ValueError, match="does not confirm this completed invocation"):
        _inspect(source, output, operations, rcc)
    assert list(operations.iterdir()) == []


@pytest.mark.parametrize(
    ("receipt_values", "message"),
    [
        ({"receipt_outside": True}, "escapes the private RCC home"),
        ({"wrong_prefix": True}, "outside its interpreter prefix"),
        ({"missing_materialization_id": True}, "materialization identity is missing"),
    ],
)
def test_binds_managed_python_to_receipt_materialization(
    tmp_path, receipt_values, message
):
    source, output, operations, rcc = _fixture(tmp_path)
    _configure(rcc, **receipt_values)
    with pytest.raises(ValueError, match=message):
        _inspect(source, output, operations, rcc)
    assert list(operations.iterdir()) == []


def test_preparation_timeout_cleans_process_tree(tmp_path, monkeypatch):
    source, output, operations, rcc = _fixture(tmp_path)
    _configure(rcc, mode="prep-timeout")
    with pytest.raises(TimeoutError, match="execution deadline"):
        _inspect(source, output, operations, rcc, timeout_seconds=1)
    assert list(operations.iterdir()) == []


def test_bounded_output_reader_rejects_symlink(tmp_path):
    from actions.server.deployments.rcc_inspection import _read_owned_regular_file

    target = tmp_path / "target"
    target.write_bytes(b"{}")
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(OSError):
        _read_owned_regular_file(link, 16)
