"""Validation for the Actions-owned frontend manifest and lock."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str]
    warnings: list[str]

    @property
    def violations(self) -> list[str] | None:
        return self.errors or None

    @property
    def message(self) -> str:
        return "Validation passed" if self.passed else "; ".join(self.errors)


class PackageManifest:
    """Load and validate the single frontend package contract."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.data: dict = {}

    @property
    def dependencies(self) -> dict:
        return self.data.get("dependencies", {})

    @property
    def dev_dependencies(self) -> dict:
        return self.data.get("devDependencies", {})

    @property
    def locked(self) -> bool:
        return (self.file_path.parent / "package-lock.json").is_file()

    @classmethod
    def load(cls, frontend_dir: Path) -> "PackageManifest":
        file_path = frontend_dir / "package.json"
        if not file_path.is_file():
            raise FileNotFoundError(f"Manifest not found: {file_path}")
        manifest = cls(file_path)
        manifest.data = json.loads(file_path.read_text(encoding="utf-8"))
        return manifest

    def validate(self) -> ValidationResult:
        errors: list[str] = []
        if not self.locked:
            errors.append("package-lock.json is required beside package.json")
        packages = {**self.dependencies, **self.dev_dependencies}
        prohibited_names = {
            name
            for name in packages
            if name.startswith("@sema4ai/")
            or name in {"actions-runtime-components", "actions-runtime-icons"}
        }
        prohibited_urls = {
            name
            for name, version in packages.items()
            if isinstance(version, str)
            and (version.startswith("file:") or "npm.pkg.github.com" in version)
        }
        for name in sorted(prohibited_names | prohibited_urls):
            errors.append(f"Actions frontend manifest contains prohibited package {name!r}")
        for name, version in packages.items():
            if version in {"*", "latest"}:
                errors.append(f"Package {name} uses unsupported version {version!r}")
        return ValidationResult(not errors, errors, [])
