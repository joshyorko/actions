from __future__ import annotations

import importlib.util
import json
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent


def _sibling(name: str):
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


manifest_writer = _sibling("write_native_artifact_manifest")
archive_writer = _sibling("archive_native_artifact_provenance")
binding = _sibling("native_runtime_artifact_binding")

VERIFIER_PATH = SCRIPT_DIR / "verify_dakota_rcc_acceptance.py"


def _verifier():
    spec = importlib.util.spec_from_file_location(
        "rcc_acceptance_verifier", VERIFIER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path: Path):
    package = tmp_path / "bundle" / "action_server"
    frozen = package / "dist/action-server"
    frozen.mkdir(parents=True)
    frozen_executable = frozen / "action-server"
    frozen_executable.write_bytes(b"frozen executable")
    frozen_executable.chmod(0o755)
    wrapper = package / "dist/final/action-server"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_bytes(b"go wrapper")
    assets = tmp_path / "assets.zip"
    with zipfile.ZipFile(assets, "w") as archive:
        archive.writestr("action-server", b"frozen executable")
    source = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    inventory = manifest_writer.packaged_tree_inventory(frozen)
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    tree_digest = manifest_writer.packaged_tree_sha256(frozen)
    files_digest = manifest_writer.packaged_files_sha256(frozen)
    manifest = {
        "schema_version": 1,
        "source_sha": source,
        "workflow_run_id": "123456",
        "workflow_run_attempt": "2",
        "platform": platform.system(),
        "architecture": platform.machine(),
        "artifacts": {
            "frozen": {
                "path": "dist/action-server/action-server",
                "sha256": manifest_writer.sha256(frozen_executable),
                "assets_zip_path": "go-wrapper/assets/assets.zip",
                "embedded_files_sha256": files_digest,
                "frozen_package_tree_sha256": tree_digest,
                "assets_zip_sha256": manifest_writer.sha256(assets),
                "frozen_package_tree_inventory_path": archive_writer.INVENTORY_ARCHIVE_PATH,
            },
            "go-wrapper": {
                "path": "dist/final/action-server",
                "sha256": manifest_writer.sha256(wrapper),
                "assets_zip_path": "go-wrapper/assets/assets.zip",
                "embedded_files_sha256": files_digest,
                "frozen_package_tree_sha256": tree_digest,
                "assets_zip_sha256": manifest_writer.sha256(assets),
                "frozen_package_tree_inventory_path": archive_writer.INVENTORY_ARCHIVE_PATH,
            },
        },
        "artifact_downloads": {
            "frozen": {
                "container_archive_path": "native-artifact-provenance.tar",
                "archive_path": "dist/action-server/action-server",
                "tree_archive_path": archive_writer.TREE_ARCHIVE_PATH,
                "inventory_archive_path": archive_writer.INVENTORY_ARCHIVE_PATH,
            },
            "manifest": {
                "container_archive_path": "native-artifact-provenance.tar",
                "archive_path": archive_writer.MANIFEST_ARCHIVE_PATH,
                "inventory_archive_path": archive_writer.INVENTORY_ARCHIVE_PATH,
            },
        },
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    provenance = tmp_path / "provenance.tar"
    archive_writer.create_archive(frozen, manifest_path, inventory_path, provenance)
    return package, manifest_path, inventory_path, provenance, assets, manifest


def test_native_mode_requires_complete_bound_package_and_exact_selector(tmp_path):
    package, manifest, inventory, provenance, assets, _ = _fixture(tmp_path)

    result = binding.validate_native_artifact(
        "frozen", package, manifest, inventory, provenance
    )

    assert result.receipt["selected_kind"] == "frozen"
    assert result.receipt["selected_path"] == "dist/action-server/action-server"
    assert result.receipt["package_tree_sha256"]
    assert str(result.selector_path) == str(
        (package / "dist/action-server/action-server").resolve()
    )


def test_native_binding_rejects_companion_tree_outside_selected_bundle(tmp_path):
    package, manifest, inventory, provenance, _, _ = _fixture(tmp_path)
    frozen = package / "dist/action-server"
    external = tmp_path / "external/action-server"
    external.parent.mkdir(parents=True)
    frozen.rename(external)
    frozen.symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="escapes selected bundle"):
        binding.validate_native_artifact(
            "frozen", package, manifest, inventory, provenance
        )


def test_provenance_metadata_tar_members_are_bounded_by_external_inputs(tmp_path):
    package, manifest, inventory, provenance, _, _ = _fixture(tmp_path)
    metadata_sizes = {
        archive_writer.MANIFEST_ARCHIVE_PATH: manifest.stat().st_size,
        archive_writer.INVENTORY_ARCHIVE_PATH: inventory.stat().st_size,
    }

    binding._check_tar_member_limit(provenance, metadata_sizes=metadata_sizes)

    metadata_sizes[archive_writer.MANIFEST_ARCHIVE_PATH] += 1
    with pytest.raises(ValueError, match="metadata member size"):
        binding._check_tar_member_limit(provenance, metadata_sizes=metadata_sizes)


def test_go_wrapper_requires_exact_embedded_zip_and_binds_extraction(tmp_path):
    package, manifest, inventory, provenance, assets, _ = _fixture(tmp_path)

    result = binding.validate_native_artifact(
        "go-wrapper", package, manifest, inventory, provenance, assets_zip_path=assets
    )

    assert result.receipt["selected_kind"] == "go-wrapper"
    assert result.receipt["assets_zip_sha256"] == manifest_writer.sha256(assets)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("platform", "WrongOS"),
        ("workflow_run_id", ""),
        ("workflow_run_attempt", "0"),
    ],
)
def test_native_binding_rejects_wrong_build_identity(tmp_path, field, value):
    package, manifest_path, inventory, provenance, _, manifest = _fixture(tmp_path)
    manifest[field] = value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError):
        binding.validate_native_artifact(
            "frozen", package, manifest_path, inventory, provenance
        )


def test_go_wrapper_rejects_assets_archive_hash_mismatch(tmp_path):
    package, manifest, inventory, provenance, assets, _ = _fixture(tmp_path)
    assets.write_bytes(b"different archive")

    with pytest.raises(ValueError, match="assets archive"):
        binding.validate_native_artifact(
            "go-wrapper",
            package,
            manifest,
            inventory,
            provenance,
            assets_zip_path=assets,
        )


def test_go_extraction_requires_exact_inventory(tmp_path):
    package, manifest, inventory, provenance, assets, _ = _fixture(tmp_path)
    binding.validate_native_artifact(
        "go-wrapper", package, manifest, inventory, provenance, assets_zip_path=assets
    )
    internal = tmp_path / "home/.actions/bin/action-server/internal/1.0.0"
    internal.mkdir(parents=True)
    (internal / "action-server").write_bytes(b"frozen executable")
    manifest_value = json.loads(manifest.read_text(encoding="utf-8"))
    (internal / "app_hash").write_text(
        manifest_value["artifacts"]["frozen"]["assets_zip_sha256"]
    )

    with pytest.raises(ValueError, match="extracted package"):
        binding.validate_go_extraction(
            tmp_path / "home",
            inventory,
            embedded_files_sha256="not-the-tree",
            assets_zip_sha256=manifest_value["artifacts"]["frozen"][
                "assets_zip_sha256"
            ],
        )


def test_go_extraction_accepts_matching_measured_inventory(tmp_path):
    package, manifest, inventory, provenance, assets, _ = _fixture(tmp_path)
    binding_result = binding.validate_native_artifact(
        "go-wrapper", package, manifest, inventory, provenance, assets_zip_path=assets
    )
    internal = tmp_path / "home/.actions/bin/action-server/internal/1.0.0"
    internal.mkdir(parents=True)
    source = package / "dist/action-server/action-server"
    executable = internal / "action-server"
    executable.write_bytes(source.read_bytes())
    executable.chmod(source.stat().st_mode & 0o777)
    (internal / "app_hash").write_text(
        str(binding_result.receipt["assets_zip_sha256"]), encoding="utf-8"
    )

    result = binding.validate_go_extraction(
        tmp_path / "home",
        inventory,
        embedded_files_sha256=str(binding_result.receipt["embedded_files_sha256"]),
        assets_zip_sha256=str(binding_result.receipt["assets_zip_sha256"]),
    )

    assert result["extracted_tree_sha256"]


def test_verifier_defaults_to_source_and_filters_ambient_selector(tmp_path):
    verifier = _verifier()
    args = verifier._parser().parse_args(["--receipt", str(tmp_path / "receipt.json")])
    assert args.action_server_mode == "source"

    inherited = {
        "PATH": "/usr/bin",
        "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE": "/ambient/native",
    }
    source_env = verifier.child_environment(inherited, task_root=tmp_path / "source")
    assert "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE" not in source_env

    native = tmp_path / "verified-executable"
    native.write_text("native", encoding="utf-8")
    native_env = verifier.child_environment(
        inherited,
        task_root=tmp_path / "native",
        validated_native_artifact=binding.ValidatedNativeArtifact(
            selector_path=native,
            inventory_path=native,
            receipt={},
        ),
    )
    assert native_env["SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE"] == str(
        native
    )


def test_verifier_requires_all_explicit_native_binding_inputs(tmp_path):
    verifier = _verifier()
    args = verifier._parser().parse_args(
        ["--action-server-mode", "frozen", "--receipt", str(tmp_path / "receipt.json")]
    )

    with pytest.raises(
        ValueError, match="requires package, manifest, inventory, and provenance"
    ):
        verifier._native_binding_from_args(args)


def test_supervisor_forwards_only_explicit_native_artifact_inputs(tmp_path):
    verifier = _verifier()
    package, manifest, inventory, provenance, _, _ = _fixture(tmp_path)
    receipt = tmp_path / "receipt.json"
    args = verifier._parser().parse_args(
        [
            "--action-server-mode",
            "frozen",
            "--native-package-root",
            str(package),
            "--native-build-manifest",
            str(manifest),
            "--native-tree-inventory",
            str(inventory),
            "--native-provenance",
            str(provenance),
            "--receipt",
            str(receipt),
        ]
    )
    verifier._validate_native_argument_shape(args)

    command = verifier._worker_command(args)

    assert command[command.index("--action-server-mode") + 1] == "frozen"
    assert command[command.index("--native-package-root") + 1] == str(package)
    assert command[command.index("--native-build-manifest") + 1] == str(manifest)
    assert command[command.index("--native-tree-inventory") + 1] == str(inventory)
    assert command[command.index("--native-provenance") + 1] == str(provenance)
    assert "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE" not in command


def test_source_supervisor_command_does_not_forward_native_artifacts(tmp_path):
    verifier = _verifier()
    args = verifier._parser().parse_args(["--receipt", str(tmp_path / "receipt.json")])

    command = verifier._worker_command(args)

    assert command[command.index("--action-server-mode") + 1] == "source"
    assert not any(argument.startswith("--native-") for argument in command)


def test_verifier_and_helpers_import_by_path_without_scripts_sys_path(tmp_path):
    code = (
        "import importlib.util,sys; "
        f"script={str(VERIFIER_PATH)!r}; "
        f"scripts={str(SCRIPT_DIR)!r}; "
        "assert scripts not in sys.path; "
        "spec=importlib.util.spec_from_file_location('isolated_verifier',script); "
        "module=importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(module); "
        "assert scripts not in sys.path; "
        "assert module._native_binding.__file__ == scripts + '/native_runtime_artifact_binding.py'; "
        "assert sys.modules['archive_native_artifact_provenance'].__file__ == scripts + '/archive_native_artifact_provenance.py'; "
        "print('isolated sibling import PASS')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "isolated sibling import PASS"


def test_verifier_has_explicit_go_wrapper_mode(tmp_path):
    verifier = _verifier()
    args = verifier._parser().parse_args(
        [
            "--action-server-mode",
            "go-wrapper",
            "--receipt",
            str(tmp_path / "receipt.json"),
        ]
    )

    assert args.action_server_mode == "go-wrapper"


def test_candidate_wheel_identity_records_worker_distribution_origins(tmp_path):
    verifier = _verifier()
    prefix = tmp_path / "worker"
    site_packages = prefix / "lib/python3.12/site-packages"
    site_packages.mkdir(parents=True)
    expected = {
        "result": "dakota-rcc-local-acceptance",
        "actions_core": "1.0.3",
        "actions_http_helper": "1.0.3",
        "server_integration": "ManagedParameters",
    }
    result = {
        **expected,
        "worker_prefix": str(prefix),
        "actions_core_distribution_root": str(site_packages),
        "actions_http_helper_distribution_root": str(site_packages),
    }

    identity = verifier.candidate_worker_distribution_identity(result, expected)

    assert identity["worker_prefix"] == str(prefix)
    assert identity["distributions"]["actions-core"]["version"] == "1.0.3"


def test_candidate_wheel_identity_rejects_origin_outside_worker_prefix(tmp_path):
    verifier = _verifier()
    prefix = tmp_path / "worker"
    prefix.mkdir()
    outside = tmp_path / "external-site-packages"
    outside.mkdir()
    expected = {
        "result": "dakota-rcc-local-acceptance",
        "actions_core": "1.0.3",
        "actions_http_helper": "1.0.3",
        "server_integration": "ManagedParameters",
    }
    result = {
        **expected,
        "worker_prefix": str(prefix),
        "actions_core_distribution_root": str(outside),
        "actions_http_helper_distribution_root": str(outside),
    }

    with pytest.raises(AssertionError, match="outside its prefix"):
        verifier.candidate_worker_distribution_identity(result, expected)
