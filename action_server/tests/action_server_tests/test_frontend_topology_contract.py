import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
FRONTEND = ROOT / "frontend"


def test_frontend_uses_one_canonical_manifest_and_lock():
    manifest = json.loads((FRONTEND / "package.json").read_text())

    assert (FRONTEND / "package-lock.json").exists()
    assert not (FRONTEND / "package.json.community").exists()
    assert not (FRONTEND / "package.json.enterprise").exists()
    assert not (FRONTEND / "feature-boundaries.json").exists()
    assert not (FRONTEND / "src/enterprise").exists()
    assert not any(
        name.startswith("@sema") for name in manifest.get("dependencies", {})
    )


def test_build_helpers_use_canonical_frontend_entry():
    tasks = (ROOT / "tasks.py").read_text()
    manifest = (ROOT / "build-binary" / "package_manifest.py").read_text()
    resolver = (ROOT / "build-binary" / "package_resolver.py").read_text()

    assert "package.json.community" not in tasks
    assert "package.json.enterprise" not in tasks
    assert "--tier" not in tasks
    assert "package.json.{tier_name}" not in manifest
    assert "private" not in resolver.lower()


def test_runtime_and_canvas_artifact_contracts_are_explicit():
    vite = (FRONTEND / "vite.config.js").read_text()
    package = json.loads((FRONTEND / "package.json").read_text())

    assert "build:canvas" in package["scripts"]
    assert "dist-canvas" in vite
    assert "dist" in vite
    assert (FRONTEND / "apps/runtime/index.html").exists()
    assert (FRONTEND / "apps/canvas-view/index.html").exists()


def test_integrity_contract_is_actions_owned_and_offline():
    integrity = (
        ROOT / "tests" / "action_server_tests" / "test_frontend_integrity.py"
    ).read_text()

    assert "package.json" in integrity
    assert "package-lock.json" in integrity
    assert "LICENSES" in integrity
    assert "private" not in integrity.lower()
    assert "npm.pkg.github.com" not in integrity
