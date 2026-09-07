"""Offline integrity contract for the Actions-owned frontend source bundle."""

import json
from pathlib import Path

FRONTEND = Path(__file__).parents[2] / "frontend"


def test_canonical_manifest_lock_and_license_are_present():
    manifest = json.loads((FRONTEND / "package.json").read_text())
    lock = json.loads((FRONTEND / "package-lock.json").read_text())

    assert manifest["name"] == "actions-runtime-frontend"
    assert lock["packages"][""]["name"] == manifest["name"]
    assert "Actions-owned" in (FRONTEND / "LICENSES/README.md").read_text()
    assert not any(name.startswith("@sema") for name in manifest["dependencies"])


def test_canonical_contract_has_no_external_runtime_asset_dependency():
    vite = (FRONTEND / "vite.config.js").read_text()
    runtime = (FRONTEND / "apps/runtime/src/main.tsx").read_text()

    assert "external" not in vite
    assert "http://" not in runtime
    assert "https://" not in runtime
