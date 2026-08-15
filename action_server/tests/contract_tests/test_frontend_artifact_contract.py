import json
from pathlib import Path


FRONTEND = Path(__file__).parents[2] / "frontend"


def test_frontend_manifest_declares_modern_dual_artifact_contract():
    manifest = json.loads((FRONTEND / "package.json").read_text())

    assert manifest["engines"]["node"] == ">=20.19.0"
    assert "build:artifacts" in manifest["scripts"]
    assert "validate:artifacts" in manifest["scripts"]
    assert "@vitejs/plugin-react" in manifest["devDependencies"]
    assert "vite-plugin-singlefile" not in manifest["devDependencies"]


def test_vite_config_keeps_runtime_embeddable_and_canvas_mcp_view_distinct():
    config = (FRONTEND / "vite.config.js").read_text()

    assert "runtime-admin" in config
    assert "canvas-mcp-app" in config
    assert "sourcemap: false" in config
    assert "text/html;profile=mcp-app" in config


def test_artifact_validator_checks_manifests_and_directory_budgets():
    validator = (FRONTEND.parent / "build-binary" / "artifact_validator.py").read_text()

    assert "artifact-manifest.json" in validator
    assert "sbom.json" in validator
    assert "rglob" in validator
    assert "text/html;profile=mcp-app" in validator


def test_hosted_bundle_budget_uses_the_manifest_payload_for_both_artifacts():
    workflow = (FRONTEND.parents[1] / ".github/workflows/frontend-build.yml").read_text()

    assert "npm run validate:artifacts" in workflow
    assert "du -sb dist" not in workflow
    assert "Get-ChildItem -Path dist -Recurse -File" not in workflow


def test_frontend_release_metadata_and_canvas_identity_are_cross_platform():
    package = json.loads((FRONTEND / "package.json").read_text())
    scripts = package["scripts"]

    assert scripts["sbom"].count("--output-reproducible") == 2
    assert "'text/html;profile=mcp-app'" not in scripts["build:canvas"]
    assert '"text/html;profile=mcp-app"' in scripts["build:canvas"]


def test_hosted_determinism_check_covers_every_matrix_os():
    workflow = (FRONTEND.parents[1] / ".github/workflows/frontend-build.yml").read_text()

    assert "if: runner.os != 'Windows'" not in workflow
