"""Build deterministic Action Server template archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIP_FILE_MODE = 0o100644 << 16


def _zip_directory(directory: Path) -> bytes:
    result = bytearray()
    with tempfile.NamedTemporaryFile() as temporary:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for source in sorted(path for path in directory.rglob("*") if path.is_file()):
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
        "url": config.get("templateBundleUrl", ""),
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
