import hashlib
import io
import logging
import os
import tempfile
import zipfile
from pathlib import Path

import yaml
from pydantic import ValidationError
from pydantic.main import BaseModel

from ._settings import get_default_settings_dir

ACTION_TEMPLATES_METADATA_FILENAME = "action-templates.yaml"

log = logging.getLogger(__name__)


class ActionTemplate(BaseModel):
    name: str
    description: str


class ActionTemplatesMetadata(BaseModel):
    hash: str
    templates: list[ActionTemplate]


def _ensure_latest_templates() -> None:
    """Seed an invalid or missing cache from verified embedded assets."""
    action_templates_dir_path = _get_action_templates_dir_path()
    if action_templates_dir_path.is_symlink():
        action_templates_dir_path.unlink()
    action_templates_dir_path.mkdir(parents=True, exist_ok=True)
    embedded_metadata, embedded_package = _embedded_assets()
    local_metadata = _get_local_templates_metadata()
    if not _cache_is_valid(
        action_templates_dir_path,
        local_metadata,
        embedded_metadata,
        embedded_package,
    ) and not _install_bundle(
        action_templates_dir_path, embedded_metadata, embedded_package
    ):
        raise RuntimeError("Embedded Action Server templates failed validation")


def _install_bundle(
    action_templates_dir: Path, metadata: ActionTemplatesMetadata, bundle: bytes
) -> bool:
    if hashlib.sha256(bundle).hexdigest() != metadata.hash:
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            members = archive.infolist()
            member_names = [member.filename for member in members]
            if len(member_names) != len(set(member_names)):
                return False
            expected = {f"{template.name}.zip" for template in metadata.templates}
            if set(member_names) != expected:
                return False
            if any(not _safe_zip_member(member) for member in members):
                return False
            extracted: dict[str, bytes] = {
                Path(member.filename).stem: archive.read(member) for member in members
            }
        for name, content in extracted.items():
            with zipfile.ZipFile(io.BytesIO(content)) as template_archive:
                template_members = template_archive.infolist()
                template_names = [member.filename for member in template_members]
                if len(template_names) != len(set(template_names)):
                    return False
                if any(not _safe_zip_member(member) for member in template_members):
                    return False
            _write_atomic(action_templates_dir / f"{name}.zip", content)
        _write_atomic(_get_action_templates_metadata_path(), _metadata_bytes(metadata))
        return True
    except (OSError, ValueError, zipfile.BadZipFile, KeyError):
        return False


def _embedded_assets() -> tuple[ActionTemplatesMetadata, bytes]:
    directory = Path(__file__).parent / "templates"
    metadata_path = directory / ACTION_TEMPLATES_METADATA_FILENAME
    package_path = directory / "action-templates.zip"
    metadata = _parse_templates_metadata(metadata_path.read_text(encoding="utf-8"))
    if metadata is None or not package_path.is_file():
        raise RuntimeError("Embedded Action Server templates are unavailable")
    return metadata, package_path.read_bytes()


def _metadata_bytes(metadata: ActionTemplatesMetadata) -> bytes:
    return (
        yaml.safe_dump(
            {
                "schema": 1,
                "hash": metadata.hash,
                "templates": {
                    item.name: item.description
                    for item in sorted(metadata.templates, key=lambda item: item.name)
                },
            },
            sort_keys=False,
        )
    ).encode("utf-8")


def _cache_is_valid(
    directory: Path,
    metadata: ActionTemplatesMetadata | None,
    embedded_metadata: ActionTemplatesMetadata,
    embedded_bundle: bytes,
) -> bool:
    if not metadata or metadata.hash != embedded_metadata.hash:
        return False
    if hashlib.sha256(embedded_bundle).hexdigest() != embedded_metadata.hash:
        return False
    if {item.name for item in metadata.templates} != {
        item.name for item in embedded_metadata.templates
    }:
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(embedded_bundle)) as embedded_archive:
            expected = {
                Path(member.filename).stem: embedded_archive.read(member)
                for member in embedded_archive.infolist()
            }
    except (OSError, zipfile.BadZipFile, KeyError):
        return False
    for name, expected_content in expected.items():
        archive_path = directory / f"{name}.zip"
        if not archive_path.is_file():
            return False
        try:
            if archive_path.read_bytes() != expected_content:
                return False
            with zipfile.ZipFile(archive_path) as archive:
                if any(not _safe_zip_member(member) for member in archive.infolist()):
                    return False
        except (OSError, zipfile.BadZipFile):
            return False
    return True


def _safe_zip_member(member: zipfile.ZipInfo) -> bool:
    name = member.filename
    path = Path(name)
    mode = member.external_attr >> 16
    is_symlink = mode & 0o170000 == 0o120000
    return bool(
        name
        and not is_symlink
        and not path.is_absolute()
        and ".." not in path.parts
        and name == path.as_posix()
    )


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def _get_local_templates_metadata() -> ActionTemplatesMetadata | None:
    action_templates_metadata_path = _get_action_templates_metadata_path()

    if not os.path.isfile(action_templates_metadata_path):
        return None

    try:
        contents = action_templates_metadata_path.read_text(encoding="utf-8")
    except OSError as e:
        log.warning(f"Error reading local template metadata: {e}")
        return None
    return _parse_templates_metadata(contents)


def _parse_templates_metadata(yaml_content: str) -> ActionTemplatesMetadata | None:
    try:
        metadata = yaml.safe_load(yaml_content)
        if not isinstance(metadata, dict):
            return None

        template_values = metadata.get("templates", {})
        if not isinstance(template_values, dict):
            return None

        templates: list[ActionTemplate] = []

        for name, description in template_values.items():
            templates.append(ActionTemplate(name=name, description=description))

        return ActionTemplatesMetadata(
            hash=metadata.get("hash", ""),
            templates=templates,
        )
    except (ValidationError, TypeError, ValueError, yaml.YAMLError) as e:
        log.warning(f"Error reading metadata: {e}")
        return None


def _unpack_template(template_name: str, directory: str = ".") -> None:
    template_path = _get_action_templates_dir_path() / f"{template_name}.zip"

    if not os.path.isfile(template_path):
        raise RuntimeError(f"Template {template_name} does not exist")

    os.makedirs(directory, exist_ok=True)

    with zipfile.ZipFile(template_path, "r") as zip_ref:
        members = zip_ref.infolist()
        if any(not _safe_zip_member(member) for member in members):
            raise ValueError(f"Template {template_name} contains an unsafe path")
        zip_ref.extractall(directory)


def _get_action_templates_dir_path() -> Path:
    return Path(get_default_settings_dir() / "action-templates")


def _get_action_templates_metadata_path() -> Path:
    return Path(_get_action_templates_dir_path() / ACTION_TEMPLATES_METADATA_FILENAME)


def _print_templates_list(templates: list[ActionTemplate]) -> None:
    from actions.server.vendored_deps.termcolors import colored

    for index, template in enumerate(templates, start=1):
        log.info(colored(f" > {index}. {template.description}", "cyan"))
