"""Validation for Actions-owned frontend build artifacts."""

import argparse
import gzip
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import tree_shaker

FRONTEND_PAYLOAD_MAX_BYTES = 1024 * 1024
FRONTEND_PAYLOAD_GZIP_MAX_BYTES = 300 * 1024


@dataclass
class ValidationCheck:
    """Result of a single validation check."""
    
    name: str
    passed: bool
    message: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class BuildArtifact:
    """Represents a build artifact with metadata."""
    
    platform: str
    file_path: Path
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    git_commit: Optional[str] = None
    
    def compute_hash(self) -> str:
        """Compute SHA256 hash of artifact."""
        sha256_hash = hashlib.sha256()
        
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        self.sha256 = sha256_hash.hexdigest()
        return self.sha256
    
    def compute_size(self) -> int:
        """Compute size of artifact in bytes."""
        self.size_bytes = self.file_path.stat().st_size
        return self.size_bytes
    
    def to_metadata_json(self) -> str:
        """Generate metadata JSON for artifact."""
        metadata = {
            "platform": self.platform,
            "sha256": self.sha256 or self.compute_hash(),
            "size_bytes": self.size_bytes or self.compute_size(),
            "git_commit": self.git_commit,
        }
        return json.dumps(metadata, indent=2)


def validate_imports(artifact_path: Path) -> ValidationCheck:
    """Validate that an artifact has no removed product imports."""
    symlinks = _find_symlinks(artifact_path)
    if symlinks:
        return ValidationCheck("symlinks", False, f"Symlink entries are forbidden: {', '.join(map(str, symlinks))}")
    if artifact_path.is_dir():
        violations = tree_shaker.TreeShaker(artifact_path).scan_directory(artifact_path)
    else:
        violations = tree_shaker.scan_imports(str(artifact_path))
    
    if violations:
        messages = [
            f"{v.prohibited_module} at line {v.line_number}" for v in violations
        ]
        return ValidationCheck(
            name="imports",
            passed=False,
            message=f"Removed product imports detected: {', '.join(messages)}",
            severity="error",
        )
    
    return ValidationCheck(
        name="imports",
        passed=True,
        message="No removed product imports detected",
        severity="info",
    )


def _find_symlinks(artifact_path: Path) -> list[Path]:
    """Return the root or any descendant symlink without following it."""
    if artifact_path.is_symlink():
        return [artifact_path]
    if not artifact_path.is_dir():
        return []
    return [path for path in artifact_path.rglob("*") if path.is_symlink()]


def validate_size(artifact_path: Path, baseline_path: Optional[Path]) -> ValidationCheck:
    """Validate artifact size against baseline (warn if >120%)."""
    files = [artifact_path] if artifact_path.is_file() else list(artifact_path.rglob("*"))
    size_mb = sum(file.stat().st_size for file in files if file.is_file()) / (1024 * 1024)
    
    if not baseline_path or not baseline_path.exists():
        return ValidationCheck(
            name="size",
            passed=True,
            message=f"Artifact size: {size_mb:.2f}MB (no baseline to compare)",
            severity="warning",
        )
    
    with open(baseline_path, "r") as f:
        baseline = json.load(f)
    
    baseline_size = baseline.get("bundle_size_mb", 0)
    if baseline_size == 0:
        return ValidationCheck(
            name="size",
            passed=True,
            message=f"Artifact size: {size_mb:.2f}MB (baseline not set)",
            severity="warning",
        )
    
    threshold = baseline_size * 1.2
    if size_mb > threshold:
        return ValidationCheck(
            name="size",
            passed=False,
            message=f"Artifact size {size_mb:.2f}MB exceeds 120% of baseline ({baseline_size:.2f}MB)",
            severity="warning",
        )
    
    return ValidationCheck(
        name="size",
        passed=True,
        message=f"Artifact size {size_mb:.2f}MB within budget (baseline: {baseline_size:.2f}MB)",
        severity="info",
    )


def validate_build_metadata(
    artifact_path: Path,
    expected_artifact: Optional[str] = None,
    expected_content_type: Optional[str] = None,
) -> list[ValidationCheck]:
    """Validate release metadata when produced by the frontend build pipeline."""
    symlinks = _find_symlinks(artifact_path)
    if symlinks:
        return [ValidationCheck("symlinks", False, f"Symlink entries are forbidden: {', '.join(map(str, symlinks))}")]
    if not artifact_path.is_dir():
        return []
    manifest_path = artifact_path / "artifact-manifest.json"
    if not manifest_path.exists():
        return [ValidationCheck("metadata", True, "No build manifest (fixture or legacy artifact)", "warning")]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest["files"]
        names = [item["path"] for item in files]
        expected_names = sorted(
            path.relative_to(artifact_path).as_posix()
            for path in artifact_path.rglob("*")
            if path.is_file() and path.name not in {"artifact-manifest.json", "sbom.json"}
        )
        expected_directories = sorted(
            {
                parent.as_posix()
                for name in names
                for parent in Path(name).parents
                if parent.as_posix() != "."
            }
        )
        actual_directories = sorted(
            path.relative_to(artifact_path).as_posix()
            for path in artifact_path.rglob("*")
            if path.is_dir()
        )
        safe_names = all(
            isinstance(name, str)
            and name == name.replace("\\", "/")
            and not name.startswith("/")
            and ".." not in Path(name).parts
            for name in names
        )
        checks = [ValidationCheck("metadata", manifest.get("schemaVersion") == 1 and bool(files), "Build manifest is present and non-empty")]
        checks.append(ValidationCheck("source-maps", not manifest.get("sourceMaps") and not any(name.endswith(".map") for name in names), "Source maps are disabled"))
        checks.append(ValidationCheck("sbom", (artifact_path / "sbom.json").is_file(), "CycloneDX SBOM is present"))
        content_type = manifest.get("contentType")
        checks.append(ValidationCheck("artifact", expected_artifact is not None and manifest.get("artifact") == expected_artifact, f"Declared artifact: {manifest.get('artifact')}"))
        checks.append(ValidationCheck("content-type", expected_content_type is not None and content_type == expected_content_type, f"Declared content type: {content_type}"))
        checks.append(ValidationCheck("inventory", safe_names and names == sorted(names) and names == expected_names and actual_directories == expected_directories, "Manifest inventory is complete and sorted"))
        actual_bytes = []
        actual_hashes = []
        for item in files:
            path = artifact_path / item["path"]
            data = path.read_bytes()
            actual_bytes.append(len(data) == item["bytes"])
            actual_hashes.append(hashlib.sha256(data).hexdigest() == item["sha256"])
        checks.append(ValidationCheck("sizes", all(actual_bytes), "Manifest byte sizes match artifact files"))
        checks.append(ValidationCheck("hashes", all(actual_hashes), "Manifest hashes match artifact files"))
        payload = [
            (artifact_path / item["path"]).read_bytes()
            for item in files
        ]
        payload_bytes = sum(len(data) for data in payload)
        payload_gzip_bytes = sum(len(gzip.compress(data, mtime=0)) for data in payload)
        checks.append(ValidationCheck("payload-budget", payload_bytes <= FRONTEND_PAYLOAD_MAX_BYTES and payload_gzip_bytes <= FRONTEND_PAYLOAD_GZIP_MAX_BYTES, f"Executable payload: {payload_bytes} bytes raw, {payload_gzip_bytes} bytes gzip"))
        return checks
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return [ValidationCheck("metadata", False, f"Invalid build manifest: {exc}")]


def validate_artifact(
    artifact_path: Path,
    baseline_path: Optional[Path] = None,
    json_output: bool = False,
    expected_artifact: Optional[str] = None,
    expected_content_type: Optional[str] = None,
) -> tuple[bool, list[ValidationCheck]]:
    """Validate build artifact.
    
    Args:
        artifact_path: Path to artifact to validate
        baseline_path: Optional path to baseline.json
        json_output: Output results as JSON
        
    Returns:
        Tuple of (all_passed, checks)
    """
    checks = []

    symlinks = _find_symlinks(artifact_path)
    if symlinks:
        return False, [ValidationCheck("symlinks", False, f"Symlink entries are forbidden: {', '.join(map(str, symlinks))}")]
    
    # Run validation checks
    checks.append(validate_imports(artifact_path))
    checks.append(validate_size(artifact_path, baseline_path))
    checks.extend(validate_build_metadata(artifact_path, expected_artifact, expected_content_type))
    
    # Determine overall result
    all_passed = all(
        check.passed or check.severity == "warning" for check in checks
    )
    
    return all_passed, checks


def main():
    """CLI entry point for artifact validation."""
    parser = argparse.ArgumentParser(description="Validate build artifacts")
    parser.add_argument("--artifact", required=True, help="Path to artifact")
    parser.add_argument("--baseline", help="Path to baseline.json")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    artifact_path = Path(args.artifact)
    if not artifact_path.exists():
        print(f"Error: Artifact not found: {artifact_path}", file=sys.stderr)
        sys.exit(2)
    
    baseline_path = Path(args.baseline) if args.baseline else None
    
    all_passed, checks = validate_artifact(
        artifact_path, baseline_path, args.json
    )
    
    if args.json:
        result = {
            "passed": all_passed,
            "checks": [
                {
                    "name": check.name,
                    "passed": check.passed,
                    "message": check.message,
                    "severity": check.severity,
                }
                for check in checks
            ],
        }
        print(json.dumps(result, indent=2))
    else:
        for check in checks:
            status = "[OK]" if check.passed else "[FAIL]"
            print(f"{status} {check.name}: {check.message}")
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
