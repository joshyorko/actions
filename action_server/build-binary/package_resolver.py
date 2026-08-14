"""Canonical offline-safe frontend dependency contract."""

from pathlib import Path

from package_manifest import PackageManifest


def validate_frontend_contract(frontend_dir: Path) -> None:
    result = PackageManifest.load(frontend_dir).validate()
    if not result.passed:
        raise ValueError(result.message)
