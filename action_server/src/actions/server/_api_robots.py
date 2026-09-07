import asyncio
import ipaddress
import logging
import os
import shutil
import socket
import stat
import tempfile
import time
import unicodedata
import uuid
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import fastapi
import yaml
from fastapi import File, Form, UploadFile
from fastapi.routing import APIRouter
from pydantic import BaseModel

from actions.server._database import datetime_to_str
from actions.server._rcc import get_rcc_robots
from actions.server._runs_state_cache import get_global_runs_state
from actions.server._settings import get_settings

log = logging.getLogger(__name__)

# Directory where imported robots are stored
ROBOTS_DIR = Path.home() / ".robots"

_ROBOT_IO_CHUNK_SIZE = 64 * 1024
_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
_MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
_MAX_ARCHIVE_INPUT_BYTES = 100 * 1024 * 1024
_MAX_ARCHIVE_ENTRIES = 10_000
_MAX_ARCHIVE_MEMBER_BYTES = 50 * 1024 * 1024
_MAX_ARCHIVE_EXPANDED_BYTES = 500 * 1024 * 1024
_MAX_ARCHIVE_EXPANSION_RATIO = 100.0
_MAX_ARCHIVE_SECONDS = 60.0
_MAX_REDIRECTS = 5
_ALLOWED_ZIP_CONTENT_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",
}

robots_api_router = APIRouter(prefix="/api/robots")


# Catalog Response Models
class RobotTaskInfoAPI(BaseModel):
    name: str
    docs: str = ""
    env: Optional[Dict[str, str]] = None  # Environment variables from robot.yaml


class RobotPackageDetailAPI(BaseModel):
    name: str
    description: Optional[str] = None
    path: str
    environment_hash: str = ""
    tasks: List[RobotTaskInfoAPI] = []


class RobotCatalogResponseAPI(BaseModel):
    robots: List[RobotPackageDetailAPI]


def _get_robot_yaml_file(package_dir: Path) -> Optional[Path]:
    """
    Get the robot configuration file from a package directory.

    Supports both:
    - robot.yaml (older RCC format)
    - package.yaml with tasks (newer format)

    Returns the path to the config file, or None if not found.
    """
    # Check for robot.yaml first (older format)
    robot_yaml = package_dir / "robot.yaml"
    if robot_yaml.exists():
        return robot_yaml

    # Check for package.yaml with tasks (newer format)
    package_yaml = package_dir / "package.yaml"
    if package_yaml.exists():
        try:
            with open(package_yaml, "r") as f:
                pkg_data = yaml.safe_load(f)
            if pkg_data and pkg_data.get("tasks"):
                return package_yaml
        except Exception:
            pass

    return None


def _discover_robots_in_dir(base_dir: Path) -> List[RobotPackageDetailAPI]:
    """
    Discover robot packages in a directory.

    Looks for either:
    - robot.yaml (older RCC format with conda.yaml for deps)
    - package.yaml with tasks defined (newer format)
    """
    robots: list[RobotPackageDetailAPI] = []

    if not base_dir.exists():
        return robots

    # Track discovered directories to avoid duplicates
    discovered_dirs = set()

    # Look for robot.yaml files (older format)
    for robot_yaml in base_dir.rglob("robot.yaml"):
        package_dir = robot_yaml.parent
        if package_dir in discovered_dirs:
            continue
        discovered_dirs.add(package_dir)

        try:
            with open(robot_yaml, "r") as f:
                robot_data = yaml.safe_load(f)

            if not robot_data:
                continue

            # Parse tasks from robot.yaml format
            tasks_data = robot_data.get("tasks", {})
            if not tasks_data:
                continue

            tasks = []
            for task_name, task_info in tasks_data.items():
                docs = ""
                env = None
                if isinstance(task_info, dict):
                    docs = (
                        task_info.get("documentation")
                        or task_info.get("docs")
                        or task_info.get("description")
                        or ""
                    )
                    # Extract env vars if present
                    task_env = task_info.get("env")
                    if task_env and isinstance(task_env, dict):
                        env = {str(k): str(v) for k, v in task_env.items()}
                tasks.append(RobotTaskInfoAPI(name=task_name, docs=docs, env=env))

            robot = RobotPackageDetailAPI(
                name=robot_data.get("name", package_dir.name),
                description=robot_data.get("description"),
                path=str(package_dir.absolute()),
                environment_hash="",
                tasks=tasks,
            )
            robots.append(robot)

        except Exception as e:
            log.warning(f"Error parsing {robot_yaml}: {e}")
            continue

    # Look for package.yaml files with tasks (newer format)
    for package_yaml in base_dir.rglob("package.yaml"):
        package_dir = package_yaml.parent
        if package_dir in discovered_dirs:
            continue
        discovered_dirs.add(package_dir)

        try:
            with open(package_yaml, "r") as f:
                pkg_data = yaml.safe_load(f)

            if not pkg_data:
                continue

            # Check if this is a robot (has tasks defined)
            tasks_data = pkg_data.get("tasks", {})
            if not tasks_data:
                continue

            # Parse tasks
            tasks = []
            for task_name, task_info in tasks_data.items():
                docs = ""
                env = None
                if isinstance(task_info, dict):
                    docs = task_info.get("docs") or task_info.get("description") or ""
                    # Extract env vars if present
                    task_env = task_info.get("env")
                    if task_env and isinstance(task_env, dict):
                        env = {str(k): str(v) for k, v in task_env.items()}
                tasks.append(RobotTaskInfoAPI(name=task_name, docs=docs, env=env))

            robot = RobotPackageDetailAPI(
                name=pkg_data.get("name", package_dir.name),
                description=pkg_data.get("description"),
                path=str(package_dir.absolute()),
                environment_hash="",  # Will be populated when env is created
                tasks=tasks,
            )
            robots.append(robot)

        except Exception as e:
            log.warning(f"Error parsing {package_yaml}: {e}")
            continue

    return robots


@robots_api_router.get("/catalog", response_model=RobotCatalogResponseAPI)
async def get_robot_catalog():
    """
    Get catalog of available robot packages.

    Scans configured directories for robot packages (package.yaml with tasks).
    """
    settings = get_settings()
    robots = []

    # Scan the datadir for robots
    if settings.datadir:
        robots.extend(_discover_robots_in_dir(Path(settings.datadir)))

    # Also check for a dedicated robots directory
    robots_dir = Path.home() / ".robots"
    if robots_dir.exists():
        robots.extend(_discover_robots_in_dir(robots_dir))

    # Deduplicate by path
    seen_paths = set()
    unique_robots = []
    for robot in robots:
        if robot.path not in seen_paths:
            seen_paths.add(robot.path)
            unique_robots.append(robot)

    return RobotCatalogResponseAPI(robots=unique_robots)


# Import Response Model
class RobotImportResponseAPI(BaseModel):
    success: bool
    message: str
    robot_path: Optional[str] = None
    robot_name: Optional[str] = None


class _RobotImportLimitError(ValueError):
    pass


def _validate_zip_members(
    members: list[zipfile.ZipInfo],
) -> tuple[bool, str, set[str]]:
    normalized_paths: set[str] = set()
    normalized_prefixes: dict[str, str] = {}
    normalized_directories: set[str] = set()
    root_dirs: set[str] = set()
    advertised_expanded_bytes = 0

    if len(members) > _MAX_ARCHIVE_ENTRIES:
        return False, "Zip contains too many entries", set()

    for member in members:
        name = member.filename
        if not name or "\x00" in name:
            return False, "Zip contains an invalid member path", set()
        if "\\" in name:
            return False, "Zip contains an ambiguous path separator", set()

        path = PurePosixPath(name)
        if path.is_absolute() or PureWindowsPath(name).drive:
            return False, "Zip contains an absolute or drive-qualified path", set()

        raw_parts = name.rstrip("/").split("/")
        if not raw_parts or any(part in {"", ".", ".."} for part in raw_parts):
            return False, "Zip contains an unsafe package root path", set()

        normalized_parts = [
            unicodedata.normalize("NFC", part).casefold() for part in raw_parts
        ]
        normalized = "/".join(normalized_parts)
        for index in range(1, len(normalized_parts) + 1):
            normalized_prefix = "/".join(normalized_parts[:index])
            raw_prefix = "/".join(raw_parts[:index])
            previous_prefix = normalized_prefixes.get(normalized_prefix)
            if previous_prefix is not None and previous_prefix != raw_prefix:
                return False, "Zip contains duplicate or case-colliding paths", set()
            normalized_prefixes[normalized_prefix] = raw_prefix
            if (
                index < len(normalized_parts)
                and normalized_prefix in normalized_paths
                and normalized_prefix not in normalized_directories
            ):
                return False, "Zip contains a file used as a directory", set()
        if normalized in normalized_paths:
            return False, "Zip contains duplicate or case-colliding paths", set()
        normalized_paths.add(normalized)

        entry_type = stat.S_IFMT((member.external_attr >> 16) & 0xFFFF)
        if entry_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
            return False, "Zip contains a link or special filesystem entry", set()

        if member.file_size < 0 or member.compress_size < 0:
            return False, "Zip contains invalid size metadata", set()
        if member.file_size > _MAX_ARCHIVE_MEMBER_BYTES:
            return False, "Zip member exceeds the size limit", set()
        advertised_expanded_bytes += member.file_size
        if advertised_expanded_bytes > _MAX_ARCHIVE_EXPANDED_BYTES:
            return False, "Zip expanded size exceeds the limit", set()
        if member.file_size and not member.compress_size:
            return False, "Zip member has invalid compression metadata", set()
        if member.compress_size and (
            member.file_size / member.compress_size > _MAX_ARCHIVE_EXPANSION_RATIO
        ):
            return False, "Zip expansion ratio exceeds the limit", set()

        if entry_type == stat.S_IFDIR and not member.is_dir():
            return False, "Zip contains invalid directory metadata", set()
        if member.is_dir():
            normalized_directories.add(normalized)

        root_dirs.add(raw_parts[0])

    return True, "", root_dirs


def _confined_staging_path(staging_root: Path, member_name: str) -> Path:
    parts = member_name.rstrip("/").split("/")
    candidate = staging_root.joinpath(*parts)
    staging = staging_root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(staging)
    except ValueError:
        raise _RobotImportLimitError("Zip member escapes staging")

    current = staging
    for part in parts[:-1]:
        current = current / part
        try:
            current_stat = current.lstat()
        except FileNotFoundError:
            current.mkdir()
        else:
            if stat.S_ISLNK(current_stat.st_mode) or not stat.S_ISDIR(
                current_stat.st_mode
            ):
                raise _RobotImportLimitError("Zip member uses an unsafe staging path")

    return candidate


def _validate_staged_tree(root: Path) -> None:
    root_stat = root.lstat()
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise _RobotImportLimitError("Staged robot package is not a directory")

    for entry in root.rglob("*"):
        entry_stat = entry.lstat()
        if stat.S_ISLNK(entry_stat.st_mode):
            raise _RobotImportLimitError("Staged robot package contains a link")
        if not (stat.S_ISDIR(entry_stat.st_mode) or stat.S_ISREG(entry_stat.st_mode)):
            raise _RobotImportLimitError(
                "Staged robot package contains a special filesystem entry"
            )


def _sanitized_robot_name(value: Optional[str]) -> str:
    name = "".join(c for c in (value or "") if c.isalnum() or c in "._- ").strip()
    if name in {"", ".", ".."}:
        return "imported_robot"
    return name[:128]


def _publish_robot_package(
    package_dir: Path, robot_name: Optional[str], extracted_name: Optional[str]
) -> tuple[str, Path]:
    robots_root = ROBOTS_DIR.resolve()
    base_name = _sanitized_robot_name(robot_name or extracted_name)

    for _ in range(100):
        final_name = base_name
        target_dir = robots_root / final_name
        if os.path.lexists(target_dir):
            final_name = f"{base_name}_{uuid.uuid4().hex[:8]}"
            target_dir = robots_root / final_name
            if os.path.lexists(target_dir):
                continue

        temporary_target = robots_root / f".{final_name}.staging-{uuid.uuid4().hex}"
        try:
            shutil.copytree(package_dir, temporary_target, symlinks=True)
            _validate_staged_tree(temporary_target)
            if os.path.lexists(target_dir):
                raise FileExistsError(target_dir)
            os.replace(temporary_target, target_dir)
            return final_name, target_dir
        except FileExistsError:
            if not os.path.lexists(target_dir):
                raise
        finally:
            if os.path.lexists(temporary_target):
                if temporary_target.is_dir() and not temporary_target.is_symlink():
                    shutil.rmtree(temporary_target)
                else:
                    temporary_target.unlink()

    raise _RobotImportLimitError("Unable to allocate a safe robot publication path")


def _validate_download_url(url: str) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except (TypeError, ValueError):
        return False, "Robot download URL is invalid"

    if scheme != "https" or not hostname:
        return False, "Robot download URL must use an allowed HTTPS host"
    if parsed.username or parsed.password or parsed.fragment:
        return False, "Robot download URL contains disallowed credentials or fragment"
    if any(ord(character) < 0x20 for character in url):
        return False, "Robot download URL contains invalid characters"
    if port is not None and not 1 <= port <= 65535:
        return False, "Robot download URL has an invalid port"

    normalized_host = hostname.rstrip(".").lower()
    if normalized_host in {"localhost", "localhost.localdomain"}:
        return False, "Robot download URL targets a private host"

    try:
        addresses = {str(ipaddress.ip_address(normalized_host))}
    except ValueError:
        try:
            address_info = socket.getaddrinfo(
                normalized_host, port, type=socket.SOCK_STREAM
            )
            addresses = {str(ipaddress.ip_address(item[4][0])) for item in address_info}
        except (OSError, UnicodeError, ValueError):
            return False, "Robot download URL host cannot be verified"

    if not addresses or any(
        not ipaddress.ip_address(address).is_global for address in addresses
    ):
        return False, "Robot download URL targets a private host"

    return True, ""


async def _save_uploaded_robot(file: UploadFile) -> Path:
    temporary_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
            temporary_path = Path(tmp_file.name)
            total_bytes = 0
            while True:
                chunk = await file.read(_ROBOT_IO_CHUNK_SIZE)
                if not chunk:
                    break
                if len(chunk) > _ROBOT_IO_CHUNK_SIZE:
                    raise _RobotImportLimitError("Robot upload chunk exceeds the limit")
                total_bytes += len(chunk)
                if total_bytes > _MAX_UPLOAD_BYTES:
                    raise _RobotImportLimitError("Robot upload exceeds the size limit")
                tmp_file.write(chunk)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        return temporary_path
    except Exception:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        raise


def _validate_robot_package(package_dir: Path) -> tuple[bool, str, Optional[str]]:
    """
    Validate that a directory contains a valid robot package.

    Supports both:
    - robot.yaml (older RCC format with conda.yaml for deps)
    - package.yaml with tasks (newer format)

    Returns: (is_valid, message, robot_name)
    """
    robot_yaml = package_dir / "robot.yaml"
    package_yaml = package_dir / "package.yaml"

    # Try robot.yaml first (older format)
    if robot_yaml.exists():
        try:
            with open(robot_yaml, "r") as f:
                robot_data = yaml.safe_load(f)

            if not robot_data:
                return False, "robot.yaml is empty", None

            # Check for tasks
            tasks = robot_data.get("tasks", {})
            if not tasks:
                return False, "No tasks defined in robot.yaml", None

            robot_name = robot_data.get("name", package_dir.name)
            return (
                True,
                f"Valid robot package (robot.yaml) with {len(tasks)} task(s)",
                robot_name,
            )

        except yaml.YAMLError as e:
            return False, f"Invalid YAML in robot.yaml: {e}", None
        except Exception as e:
            return False, f"Error reading robot.yaml: {e}", None

    # Try package.yaml (newer format)
    if package_yaml.exists():
        try:
            with open(package_yaml, "r") as f:
                pkg_data = yaml.safe_load(f)

            if not pkg_data:
                return False, "package.yaml is empty", None

            # Check for tasks (robot packages have tasks)
            tasks = pkg_data.get("tasks", {})
            if not tasks:
                return (
                    False,
                    "No tasks defined in package.yaml - this may be an action package, not a robot",
                    None,
                )

            robot_name = pkg_data.get("name", package_dir.name)
            return (
                True,
                f"Valid robot package (package.yaml) with {len(tasks)} task(s)",
                robot_name,
            )

        except yaml.YAMLError as e:
            return False, f"Invalid YAML in package.yaml: {e}", None
        except Exception as e:
            return False, f"Error reading package.yaml: {e}", None

    return False, "No robot.yaml or package.yaml found in the package", None


def _extract_zip_to_robots(
    zip_path: Path, robot_name: Optional[str] = None
) -> tuple[bool, str, Optional[Path]]:
    """
    Extract a zip file to the robots directory.

    Returns: (success, message, extracted_path)
    """
    try:
        if not zip_path.is_file():
            return False, "Zip file is not a regular file", None
        if zip_path.stat().st_size > _MAX_ARCHIVE_INPUT_BYTES:
            return False, "Zip input exceeds the size limit", None

        ROBOTS_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            members = zip_ref.infolist()
            if not members:
                return False, "Zip file is empty", None

            valid, message, _root_dirs = _validate_zip_members(members)
            if not valid:
                return False, message, None

            # Create a temp directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                started_at = time.monotonic()
                expanded_bytes = 0
                for member in members:
                    if time.monotonic() - started_at > _MAX_ARCHIVE_SECONDS:
                        raise _RobotImportLimitError(
                            "Zip extraction exceeded the time limit"
                        )

                    member_path = _confined_staging_path(temp_path, member.filename)
                    if member.is_dir():
                        member_path.mkdir(exist_ok=True)
                        continue

                    actual_member_bytes = 0
                    with zip_ref.open(member, "r") as source, member_path.open(
                        "xb"
                    ) as destination:
                        while True:
                            chunk = source.read(_ROBOT_IO_CHUNK_SIZE)
                            if not chunk:
                                break
                            actual_member_bytes += len(chunk)
                            expanded_bytes += len(chunk)
                            if actual_member_bytes > _MAX_ARCHIVE_MEMBER_BYTES:
                                raise _RobotImportLimitError(
                                    "Zip member exceeds the size limit"
                                )
                            if expanded_bytes > _MAX_ARCHIVE_EXPANDED_BYTES:
                                raise _RobotImportLimitError(
                                    "Zip expanded size exceeds the limit"
                                )
                            if time.monotonic() - started_at > _MAX_ARCHIVE_SECONDS:
                                raise _RobotImportLimitError(
                                    "Zip extraction exceeded the time limit"
                                )
                            destination.write(chunk)

                    if actual_member_bytes != member.file_size:
                        raise _RobotImportLimitError(
                            "Zip member size could not be verified"
                        )
                    if member.compress_size and (
                        actual_member_bytes / member.compress_size
                        > _MAX_ARCHIVE_EXPANSION_RATIO
                    ):
                        raise _RobotImportLimitError(
                            "Zip expansion ratio exceeds the limit"
                        )

                _validate_staged_tree(temp_path)
                top_level = list(temp_path.iterdir())
                if len(top_level) == 1 and top_level[0].is_dir():
                    package_dir = top_level[0]
                else:
                    package_dir = temp_path

                # Validate the package
                is_valid, message, extracted_name = _validate_robot_package(package_dir)
                if not is_valid:
                    return False, message, None

                final_name, target_dir = _publish_robot_package(
                    package_dir, robot_name, extracted_name
                )

                return True, f"Successfully imported robot '{final_name}'", target_dir

    except _RobotImportLimitError as e:
        return False, str(e), None
    except zipfile.BadZipFile:
        return False, "Invalid zip file", None
    except Exception as e:
        log.exception("Error extracting robot package")
        return False, f"Error extracting package: {e}", None


async def _download_from_url(url: str) -> tuple[bool, str, Optional[Path]]:
    """
    Download a robot package from a URL.

    Supports:
    - Direct .zip file URLs
    - GitHub repository URLs (converts to zip download)

    Returns: (success, message, downloaded_path)
    """
    import httpx2 as httpx

    try:
        parsed = urlparse(url)
    except (TypeError, ValueError):
        return False, "Robot download URL is invalid", None

    # Handle GitHub repository URLs, while keeping the host match exact.
    try:
        parsed_hostname = parsed.hostname
    except ValueError:
        return False, "Robot download URL is invalid", None

    valid_url, message = _validate_download_url(url)
    if not valid_url:
        return False, message, None

    if parsed_hostname in {"github.com", "www.github.com"}:
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            owner, repo = path_parts[0], path_parts[1]
            repo = repo.removesuffix(".git")
            url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"

    valid_url, message = _validate_download_url(url)
    if not valid_url:
        return False, message, None

    temporary_path: Optional[Path] = None
    download_succeeded = False
    try:
        async with asyncio.timeout(_MAX_ARCHIVE_SECONDS):
            async with httpx.AsyncClient(
                follow_redirects=False, timeout=_MAX_ARCHIVE_SECONDS
            ) as client:
                current_url = url
                for redirect_count in range(_MAX_REDIRECTS + 1):
                    valid_url, message = _validate_download_url(current_url)
                    if not valid_url:
                        return False, message, None

                    async with client.stream("GET", current_url) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location:
                                return False, "Robot download redirect is invalid", None
                            if redirect_count >= _MAX_REDIRECTS:
                                return (
                                    False,
                                    "Robot download has too many redirects",
                                    None,
                                )
                            current_url = urljoin(current_url, location)
                            continue

                        if response.status_code >= 400:
                            return False, f"HTTP error: {response.status_code}", None

                        content_type = response.headers.get("content-type", "")
                        content_type = content_type.split(";", 1)[0].strip().lower()
                        if (
                            content_type
                            and content_type not in _ALLOWED_ZIP_CONTENT_TYPES
                        ):
                            return False, "Robot download is not a ZIP archive", None

                        content_length = response.headers.get("content-length")
                        if content_length is not None:
                            try:
                                advertised_length = int(content_length)
                            except ValueError:
                                return (
                                    False,
                                    "Robot download has invalid size metadata",
                                    None,
                                )
                            if (
                                advertised_length < 0
                                or advertised_length > _MAX_DOWNLOAD_BYTES
                            ):
                                return (
                                    False,
                                    "Robot download exceeds the size limit",
                                    None,
                                )

                        with tempfile.NamedTemporaryFile(
                            suffix=".zip", delete=False
                        ) as tmp_file:
                            temporary_path = Path(tmp_file.name)
                            total_bytes = 0
                            started_at = time.monotonic()
                            async for chunk in response.aiter_bytes(
                                chunk_size=_ROBOT_IO_CHUNK_SIZE
                            ):
                                if len(chunk) > _ROBOT_IO_CHUNK_SIZE:
                                    raise _RobotImportLimitError(
                                        "Robot download chunk exceeds the limit"
                                    )
                                total_bytes += len(chunk)
                                if total_bytes > _MAX_DOWNLOAD_BYTES:
                                    raise _RobotImportLimitError(
                                        "Robot download exceeds the size limit"
                                    )
                                if time.monotonic() - started_at > _MAX_ARCHIVE_SECONDS:
                                    raise _RobotImportLimitError(
                                        "Robot download exceeded the time limit"
                                    )
                                tmp_file.write(chunk)
                            tmp_file.flush()
                            os.fsync(tmp_file.fileno())

                        download_succeeded = True
                        return True, "Downloaded successfully", temporary_path

    except _RobotImportLimitError as e:
        return False, str(e), None
    except asyncio.TimeoutError:
        return False, "Robot download exceeded the time limit", None
    except httpx.RequestError:
        return False, "Robot download request failed", None
    except Exception:
        log.warning("Robot package download failed")
        return False, "Robot download failed", None
    finally:
        if (
            not download_succeeded
            and temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink(missing_ok=True)


@robots_api_router.post("/import", response_model=RobotImportResponseAPI)
async def import_robot(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
):
    """
    Import a robot package from a file upload or URL.

    Either 'file' (a .zip upload) or 'url' (a URL to download from) must be provided.

    The robot package must contain a package.yaml with tasks defined.
    """
    if not file and not url:
        return RobotImportResponseAPI(
            success=False,
            message="Either a file upload or URL must be provided",
        )

    temp_zip_path: Optional[Path] = None

    try:
        if file:
            # Handle file upload
            if not file.filename or not file.filename.endswith(".zip"):
                return RobotImportResponseAPI(
                    success=False,
                    message="File must be a .zip archive",
                )

            temp_zip_path = await _save_uploaded_robot(file)

        elif url:
            # Handle URL download
            success, message, downloaded_path = await _download_from_url(url)
            if not success:
                return RobotImportResponseAPI(
                    success=False,
                    message=message,
                )
            temp_zip_path = downloaded_path

        # Extract and validate the package
        assert temp_zip_path is not None, "temp_zip_path should be set by now"
        success, message, robot_path = _extract_zip_to_robots(temp_zip_path)

        if success and robot_path:
            return RobotImportResponseAPI(
                success=True,
                message=message,
                robot_path=str(robot_path),
                robot_name=robot_path.name,
            )
        else:
            return RobotImportResponseAPI(
                success=False,
                message=message,
            )

    except _RobotImportLimitError as e:
        return RobotImportResponseAPI(success=False, message=str(e))
    finally:
        # Clean up temp file
        if temp_zip_path and temp_zip_path.exists():
            try:
                temp_zip_path.unlink()
            except Exception:
                pass


class RobotRunRequestAPI(BaseModel):
    robot_package_path: str  # Absolute path to the robot package
    task_name: str  # Name of the task to run
    inputs: Optional[Dict[str, str]] = None  # Optional task inputs
    use_secrets: bool = False  # Whether to pass secrets file to RCC


class RobotRunResponseAPI(BaseModel):
    run_id: str  # The assigned run ID
    status: str  # Current run status
    message: Optional[str] = None  # Optional status message


@robots_api_router.post("/run", response_model=RobotRunResponseAPI)
async def run_robot_task(
    request: RobotRunRequestAPI,
    background_tasks: fastapi.BackgroundTasks,
    http_request: fastapi.Request,
):
    """
    Execute a robot task and track its execution.

    The task is executed asynchronously and the run status can be monitored
    via the /api/runs/{run_id} endpoint.
    """
    import datetime
    import json
    import uuid
    from pathlib import Path

    from actions.server._models import RUN_ID_COUNTER, Counter, Run, RunStatus, get_db

    # Get settings for paths
    settings = get_settings()
    db = get_db()

    # Extract work item queue header if present
    workitem_queue = http_request.headers.get("x-workitem-queue", "")

    run_id = f"run-{uuid.uuid4()}"
    relative_artifacts_path = f"runs/{run_id}"
    from actions.server._artifact_storage import get_artifact_storage

    artifacts_dir = get_artifact_storage().create_run_artifacts_dir(
        relative_artifacts_path
    )

    # Create initial run record
    run_kwargs = dict(
        id=run_id,
        status=RunStatus.NOT_RUN,
        action_id="",  # No action ID for robot runs
        start_time=datetime_to_str(datetime.datetime.now(datetime.timezone.utc)),
        run_time=None,
        inputs=json.dumps(request.inputs or {}),
        result=None,
        error_message=None,
        relative_artifacts_dir=relative_artifacts_path,
        request_id="",  # No request ID for robot runs yet
        run_type="robot",
        robot_package_path=request.robot_package_path,
        robot_task_name=request.task_name,
        robot_env_hash="",  # Will be populated when environment is created
    )

    # Insert the run record with an atomic numbered ID
    with db.transaction():
        with db.cursor() as cursor:
            db.execute_update_returning(
                cursor,
                "UPDATE counter SET value=value+1 WHERE id=? RETURNING value",
                [RUN_ID_COUNTER],
            )
            counter_record = cursor.fetchall()
            if not counter_record:
                raise RuntimeError(
                    f"Error. No counter found for run_id. Counters in db: {db.all(Counter)}"
                )
            run_kwargs["numbered_id"] = counter_record[0][0]
            run = Run(**run_kwargs)  # type: ignore[arg-type]
            db.insert(run)

    get_artifact_storage().bind_run(run.id, run.relative_artifacts_dir, run.__dict__)

    # Notify run state listeners
    get_global_runs_state().on_run_inserted(run)

    # Schedule background task to execute the robot
    async def _execute_robot():
        # Use robots RCC instance (uses ROBOTS_HOME / ~/.robots) to avoid holotree lock contention with actions
        rcc = get_rcc_robots()

        # Set up paths
        package_path = Path(request.robot_package_path)
        if not package_path.exists():
            raise RuntimeError(f"Robot package not found: {package_path}")

        # Detect which config format is used: robot.yaml (older) or package.yaml (newer)
        robot_yaml = package_path / "robot.yaml"
        package_yaml = package_path / "package.yaml"

        # Determine the config file for RCC task run and the env file for environment creation
        if robot_yaml.exists():
            # Older robot.yaml format - uses separate conda.yaml for dependencies
            robot_config_file = robot_yaml

            # Find conda.yaml for environment creation
            # It's typically in the same directory, referenced in environmentConfigs
            conda_yaml = package_path / "conda.yaml"
            if not conda_yaml.exists():
                # Try to find it from environmentConfigs in robot.yaml
                try:
                    with open(robot_yaml, "r") as f:
                        robot_data = yaml.safe_load(f)
                    env_configs = robot_data.get("environmentConfigs", [])
                    for env_config in env_configs:
                        if env_config.endswith("conda.yaml"):
                            potential_conda = package_path / env_config
                            if potential_conda.exists():
                                conda_yaml = potential_conda
                                break
                except Exception:
                    pass

            if not conda_yaml.exists():
                raise RuntimeError(
                    f"conda.yaml not found in {package_path} (required for robot.yaml format)"
                )

            env_config_file = conda_yaml
            log.info(
                f"Using robot.yaml format with conda.yaml for environment: {robot_config_file}"
            )
        elif package_yaml.exists():
            # Newer package.yaml format - dependencies are inline
            robot_config_file = package_yaml
            env_config_file = package_yaml
            log.info(f"Using package.yaml format: {robot_config_file}")
        else:
            raise RuntimeError(f"No robot.yaml or package.yaml found in {package_path}")

        try:
            # Update run status to running
            run.status = RunStatus.RUNNING
            with db.transaction():
                db.update(run, "status")
            get_global_runs_state().on_run_changed(run, {"status": RunStatus.RUNNING})

            # Get environment variables for the robot task
            # Use env_config_file (conda.yaml or package.yaml) for environment creation
            env_result = rcc.create_env_and_get_vars(
                settings.datadir,
                env_config_file,
                package_yaml_hash=rcc.get_package_yaml_hash(
                    env_config_file, devenv=False
                ),
                devenv=False,
            )
            if not env_result.success:
                raise RuntimeError(
                    f"Failed to create robot environment: {env_result.message}"
                )

            # Update env hash
            run.robot_env_hash = env_result.result.env.get("CONDA_ENVIRONMENT_HASH", "")
            with db.transaction():
                db.update(run, "robot_env_hash")

            # Determine secrets file if requested
            # Note: secrets support requires secrets_dir to be configured
            secrets_file = None
            if request.use_secrets:
                # Look for secrets in datadir/secrets/ directory
                secrets_dir = settings.datadir / "secrets" if settings.datadir else None
                if secrets_dir and secrets_dir.exists():
                    robot_secrets = secrets_dir / f"{package_path.name}_secrets.json"
                    if robot_secrets.exists():
                        secrets_file = robot_secrets
                    else:
                        default_secrets = secrets_dir / "secrets.json"
                        if default_secrets.exists():
                            secrets_file = default_secrets

            # Set up RCC args
            # Use robot_config_file (robot.yaml or package.yaml) for the --robot argument
            # Note: RCC v18.x doesn't have --artifacts flag; artifacts go to the directory
            # specified in robot.yaml's artifactsDir (defaults to 'output')
            rcc_args = [
                "task",
                "run",
                "--robot",
                str(robot_config_file),
                "--task",
                request.task_name,
                "--silent",  # Reduce verbose RCC output
            ]

            # Create environment JSON file for work items configuration
            # RCC's -e flag expects a JSON file path, not inline VAR:value syntax
            env_vars = {}

            # RC_WORKITEM_DB_PATH: path to shared SQLite database for work items
            workitems_db_path = str(settings.datadir / "workitems.db")
            env_vars["RC_WORKITEM_DB_PATH"] = workitems_db_path

            # RC_WORKITEM_QUEUE_NAME: the queue to read work items from
            if workitem_queue:
                env_vars["RC_WORKITEM_QUEUE_NAME"] = workitem_queue

            # Write env vars to a temp JSON file if we have any
            env_file = None
            if env_vars:
                env_file = artifacts_dir / "env.json"
                env_file.write_text(json.dumps(env_vars, indent=2))
                rcc_args.extend(["-e", str(env_file)])

            # Only add --space if we have an env hash (for pre-built environments)
            if run.robot_env_hash:
                rcc_args.extend(["--space", run.robot_env_hash])

            if secrets_file and secrets_file.exists():
                rcc_args.extend(["--secrets", str(secrets_file)])

            # Output file for capturing robot logs
            output_file = artifacts_dir / "__action_server_output.txt"

            # Run the robot task
            result = rcc._run_rcc(
                rcc_args,
                timeout=3600,  # 1 hour timeout
                cwd=str(package_path),
                show_interactive_output=True,
            )

            # Save output to file for logs page
            try:
                output_content = result.result or ""
                if result.message and not result.success:
                    output_content += f"\n\n--- Error ---\n{result.message}"
                output_file.write_text(output_content, encoding="utf-8")
            except Exception as write_err:
                log.warning(f"Failed to write robot output file: {write_err}")

            # Copy robot output files to artifacts directory
            # RCC puts output in the robot's 'output' directory by default
            # This includes .robolog files (from robocorp-log) and RF output files
            robot_output_dir = package_path / "output"
            if robot_output_dir.exists():
                # Copy .robolog files for log.html generation
                for robolog_file in robot_output_dir.glob("*.robolog"):
                    try:
                        shutil.copy2(robolog_file, artifacts_dir / robolog_file.name)
                        log.debug(f"Copied {robolog_file.name} to artifacts")
                    except Exception as copy_err:
                        log.warning(f"Failed to copy {robolog_file.name}: {copy_err}")

                # Also copy Robot Framework output files if present
                for output_name in ["log.html", "output.xml", "report.html"]:
                    src_file = robot_output_dir / output_name
                    if src_file.exists():
                        try:
                            shutil.copy2(src_file, artifacts_dir / output_name)
                            log.debug(f"Copied {output_name} to artifacts")
                        except Exception as copy_err:
                            log.warning(f"Failed to copy {output_name}: {copy_err}")

            if result.success:
                run.status = RunStatus.PASSED
                run.result = json.dumps(
                    {
                        "output": result.result,
                        "artifacts_dir": str(artifacts_dir),
                    }
                )
            else:
                run.status = RunStatus.FAILED
                run.error_message = result.message

            with db.transaction():
                db.update(run, "status", "result", "error_message")

            get_global_runs_state().on_run_changed(
                run,
                {
                    "status": run.status,
                    "result": run.result,
                    "error_message": run.error_message,
                },
            )

        except Exception as e:
            log.exception("Error executing robot task")
            run.status = RunStatus.FAILED
            run.error_message = str(e)
            with db.transaction():
                db.update(run, "status", "error_message")
            get_global_runs_state().on_run_changed(
                run, {"status": RunStatus.FAILED, "error_message": str(e)}
            )

    background_tasks.add_task(_execute_robot)

    return RobotRunResponseAPI(
        run_id=run_id,
        status="REQUESTED",
        message="Robot task execution requested",
    )
