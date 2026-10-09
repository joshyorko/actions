"""Build deterministic Action Server template archives."""

from __future__ import annotations

import argparse
import fnmatch
import glob
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import yaml

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIP_FILE_MODE = 0o100644 << 16


def _matches_exclude_pattern(relative_path: str, pattern: str) -> bool:
    """Match a package.yaml exclude using PackageExcludeHandler path semantics."""
    pattern = pattern.rstrip("/\\")
    patterns = pattern.replace("\\", "/").split("/")
    paths = relative_path.replace("\\", "/").split("/")

    def matches(pattern_parts: list[str], path_parts: list[str]) -> bool:
        if not pattern_parts and not path_parts:
            return True
        if not pattern_parts or not path_parts:
            return False
        part = pattern_parts[0]
        if not glob.has_magic(part):
            if part != path_parts[0]:
                return False
        elif part == "**":
            if len(pattern_parts) == 1:
                return True
            return any(
                matches(pattern_parts[1:], path_parts[index:])
                for index in range(len(path_parts))
            )
        elif not fnmatch.fnmatch(path_parts[0], part):
            return False
        return matches(pattern_parts[1:], path_parts[1:])

    return matches(patterns, paths)


def _package_exclude_patterns(directory: Path) -> list[str]:
    package_file = directory / "package.yaml"
    if not package_file.is_file():
        return []
    package = yaml.safe_load(package_file.read_text(encoding="utf-8")) or {}
    excludes = (package.get("packaging") or {}).get("exclude") or []
    if not isinstance(excludes, list) or not all(
        isinstance(pattern, str) for pattern in excludes
    ):
        raise ValueError(f"Invalid packaging.exclude list in {package_file}")

    normalized = []
    for pattern in excludes:
        if pattern.startswith("./"):
            pattern = pattern[2:]
        elif pattern.startswith("/"):
            pattern = pattern[1:]
        elif not pattern.startswith("**"):
            pattern = f"**/{pattern}"
        normalized.append(pattern)
    return normalized


def _zip_directory(directory: Path) -> bytes:
    result = bytearray()
    exclude_patterns = _package_exclude_patterns(directory)
    with tempfile.NamedTemporaryFile() as temporary:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            sources = (
                path
                for path in directory.rglob("*")
                if path.is_file()
                and not any(
                    _matches_exclude_pattern(
                        path.relative_to(directory).as_posix(), pattern
                    )
                    for pattern in exclude_patterns
                )
            )
            for source in sorted(sources):
                relative = source.relative_to(directory).as_posix()
                info = zipfile.ZipInfo(relative, ZIP_TIMESTAMP)
                info.create_system = 3
                info.external_attr = ZIP_FILE_MODE
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, source.read_bytes())
        temporary.seek(0)
        result.extend(temporary.read())
    return bytes(result)


def _zip_templates(templates: dict[str, bytes]) -> bytes:
    with tempfile.NamedTemporaryFile() as temporary:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name in sorted(templates):
                info = zipfile.ZipInfo(f"{name}.zip", ZIP_TIMESTAMP)
                info.create_system = 3
                info.external_attr = ZIP_FILE_MODE
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, templates[name])
        temporary.seek(0)
        return temporary.read()


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.part")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def build_bundle(config_path: Path, template_root: Path, output_dir: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    template_archives: dict[str, bytes] = {}
    descriptions: dict[str, str] = {}
    for entry in config["templates"]:
        template_id = entry["id"]
        source = template_root / template_id
        if not source.is_dir():
            raise FileNotFoundError(f"Template directory does not exist: {source}")
        template_archives[template_id] = _zip_directory(source)
        descriptions[template_id] = f"{entry['name']} - {entry['desc']}"

    bundle = _zip_templates(template_archives)
    metadata = {
        "schema": 1,
        "hash": hashlib.sha256(bundle).hexdigest(),
        "templates": {name: descriptions[name] for name in sorted(descriptions)},
    }
    metadata_bytes = (
        json.dumps(metadata, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    ).encode("utf-8")
    _write_atomic(output_dir / "action-templates.zip", bundle)
    _write_atomic(output_dir / "action-templates.yaml", metadata_bytes)

    individual_dir = output_dir / "zips"
    if individual_dir.exists():
        shutil.rmtree(individual_dir)
    individual_dir.mkdir(parents=True)
    for template_id, archive in sorted(template_archives.items()):
        _write_atomic(individual_dir / f"{template_id}.zip", archive)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--template-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_bundle(args.config, args.template_root, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
