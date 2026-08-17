import datetime
import hashlib
import io
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import TypedDict

import yaml
from pydantic.main import BaseModel

from ._settings import get_default_settings_dir

TEMPLATES_METADATA_URL = "https://downloads.robocorp.com/action-templates/action-templates.yaml"
TEMPLATES_PACKAGE_URL = "https://downloads.robocorp.com/action-templates/action-templates.zip"

ACTION_TEMPLATES_METADATA_FILENAME = "action-templates.yaml"

log = logging.getLogger(__name__)


class ActionTemplatesYaml(TypedDict):
    hash: str
    url: str
    date: datetime.datetime
    templates: dict[str, str]


class ActionTemplate(BaseModel):
    name: str
    description: str


class ActionTemplatesMetadata(BaseModel):
    hash: str
    url: str
    date: datetime.datetime | None
    templates: list[ActionTemplate]


def _ensure_latest_templates() -> None:
    """Ensure a verified template cache, preferring embedded assets offline."""
    action_templates_dir_path = _get_action_templates_dir_path()
    action_templates_dir_path.mkdir(parents=True, exist_ok=True)
    embedded_metadata, embedded_package = _embedded_assets()
    local_metadata = _get_local_templates_metadata()
    if not _cache_is_valid(action_templates_dir_path, local_metadata):
        _install_bundle(action_templates_dir_path, embedded_metadata, embedded_package)

    import actions_http

    try:
        response = actions_http.get(TEMPLATES_METADATA_URL)
        response.raise_for_status()
        new_metadata_content = response.text
        new_metadata = _parse_templates_metadata(new_metadata_content)
        if new_metadata and _download_and_install_bundle(
            action_templates_dir_path, new_metadata
        ):
            _write_atomic(_get_action_templates_metadata_path(), new_metadata_content.encode())
    except Exception as error:  # noqa: BLE001 - refresh must never hide embedded fallback
        log.info("Using embedded Action Server templates: %s", error)


def _download_and_install_bundle(
    action_templates_dir: Path, metadata: ActionTemplatesMetadata
) -> bool:
    import actions_http

    response = actions_http.get(metadata.url or TEMPLATES_PACKAGE_URL)
    response.raise_for_status()
    return _install_bundle(action_templates_dir, metadata, response.data)


def _install_bundle(
    action_templates_dir: Path, metadata: ActionTemplatesMetadata, bundle: bytes
) -> bool:
    if hashlib.sha256(bundle).hexdigest() != metadata.hash:
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            members = archive.infolist()
            expected = {f"{template.name}.zip" for template in metadata.templates}
            if {member.filename for member in members} != expected:
                return False
            if any(not _safe_zip_member(member.filename) for member in members):
                return False
            extracted: dict[str, bytes] = {
                Path(member.filename).stem: archive.read(member)
                for member in members
            }
        for name, content in extracted.items():
            with zipfile.ZipFile(io.BytesIO(content)) as template_archive:
                if any(not _safe_zip_member(member.filename) for member in template_archive.infolist()):
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
    return (yaml.safe_dump({
        "schema": 1,
        "hash": metadata.hash,
        "url": metadata.url,
        "templates": {item.name: item.description for item in sorted(metadata.templates, key=lambda item: item.name)},
    }, sort_keys=False)).encode("utf-8")


def _cache_is_valid(directory: Path, metadata: ActionTemplatesMetadata | None) -> bool:
    if not metadata:
        return False
    for item in metadata.templates:
        archive_path = directory / f"{item.name}.zip"
        if not archive_path.is_file():
            return False
        try:
            with zipfile.ZipFile(archive_path) as archive:
                if any(not _safe_zip_member(member.filename) for member in archive.infolist()):
                    return False
        except (OSError, zipfile.BadZipFile):
            return False
    return True


def _safe_zip_member(name: str) -> bool:
    path = Path(name)
    return bool(name and not path.is_absolute() and ".." not in path.parts and name == path.as_posix())


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

    return _parse_templates_metadata(action_templates_metadata_path.read_text())


def _parse_templates_metadata(yaml_content: str) -> ActionTemplatesMetadata | None:
    try:
        metadata: ActionTemplatesYaml = yaml.safe_load(yaml_content)

        templates: list[ActionTemplate] = []

        for name, description in metadata.get("templates", {}).items():
            templates.append(ActionTemplate(name=name, description=description))

        return ActionTemplatesMetadata(
            hash=metadata.get("hash", ""),
            url=metadata.get("url", ""),
            date=metadata.get("date", None),
            templates=templates,
        )
    except yaml.YAMLError as e:
        log.warning(f"Error reading metadata: {e}")
        return None


def _unpack_template(template_name: str, directory: str = ".") -> None:
    template_path = _get_action_templates_dir_path() / f"{template_name}.zip"

    if not os.path.isfile(template_path):
        raise RuntimeError(f"Template {template_name} does not exist")

    os.makedirs(directory, exist_ok=True)

    with zipfile.ZipFile(template_path, "r") as zip_ref:
        members = zip_ref.infolist()
        if any(not _safe_zip_member(member.filename) for member in members):
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
