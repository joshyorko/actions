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
