"""Explicit input names for the legacy Robot task compatibility API."""

import json
import os
import re
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

import yaml

_MAX_INPUT_COUNT = 32
_MAX_INPUT_NAME_LENGTH = 128
_MAX_INPUT_VALUE_BYTES = 4096
_MAX_INPUT_BYTES = 16 * 1024
_MAX_CONFIG_BYTES = 1024 * 1024
_ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*", re.ASCII)
_PROTECTED_NAMES = frozenset(
    {
        "PATH",
        "PATHEXT",
        "HOME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "APPDATA",
        "LOCALAPPDATA",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "TMPDIR",
        "SHELL",
        "COMSPEC",
        "BASH_ENV",
        "ENV",
        "IFS",
        "CDPATH",
        "VIRTUAL_ENV",
        "_CE_CONDA",
        "_CE_M",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
        "_JAVA_OPTIONS",
        "BASHOPTS",
        "SHELLOPTS",
        "GCONV_PATH",
        "GLIBC_TUNABLES",
        "LOCPATH",
        "NLSPATH",
        "OPENSSL_CONF",
        "SSLKEYLOGFILE",
    }
)
_PROTECTED_PREFIXES = (
    "PYTHON",
    "PYTEST_",
    "LD_",
    "DYLD_",
    "RCC_",
    "ROBOCORP_",
    "ROBOT_",
    "RC_",
    "RPA_",
    "ACTIONS_",
    "SEMA4AI_",
    "S4_",
    "CONDA_",
    "MAMBA_",
    "UV_",
    "PIP_",
    "POETRY_",
    "NODE_",
    "NPM_",
    "JAVA_",
    "JDK_",
    "PERL",
    "RUBY",
    "GEM_",
    "BUNDLE_",
    "AWS_",
    "AZURE_",
    "GOOGLE_",
    "GCP_",
)
_SECRET_SUFFIXES = ("_TOKEN", "_SECRET", "_PASSWORD", "_KEY")


def _validate_name(name: object) -> str:
    if (
        not isinstance(name, str)
        or len(name) > _MAX_INPUT_NAME_LENGTH
        or not _ENVIRONMENT_NAME.fullmatch(name)
    ):
        raise ValueError(
            "Robot input names must be portable environment names of at most 128 characters"
        )
    normalized = name.upper()
    if (
        normalized in _PROTECTED_NAMES
        or normalized.startswith(_PROTECTED_PREFIXES)
        or normalized.endswith(_SECRET_SUFFIXES)
    ):
        raise ValueError(
            "Robot inputs cannot use process, Runtime, or secret environment names"
        )
    return name


def validate_robot_inputs(
    package_path: Path, task_name: str, inputs: dict[str, str] | None
) -> dict[str, str]:
    """Validate nonempty inputs against the selected task's inputEnvironment list.

    The package is trusted executable source, not a sandbox. The positive
    declaration prevents API callers from choosing additional environment names.
    Empty inputs preserve execution of existing packages without declarations.
    """
    if inputs is None:
        return {}
    if not isinstance(inputs, dict):
        raise ValueError("Robot inputs must be a string-to-string object")
    if not inputs:
        return {}
    if not package_path.is_dir():
        raise ValueError("Nonempty Robot inputs require an unpacked package directory")
    if len(inputs) > _MAX_INPUT_COUNT:
        raise ValueError("Robot inputs allow at most 32 values")
    validated: dict[str, str] = {}
    for name, value in inputs.items():
        _validate_name(name)
        if not isinstance(value, str) or "\x00" in value:
            raise ValueError(
                "Robot input values must be strings without NUL characters"
            )
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError(
                "Robot input values must contain valid UTF-8 text"
            ) from None
        if len(encoded) > _MAX_INPUT_VALUE_BYTES:
            raise ValueError("Each Robot input value allows at most 4096 UTF-8 bytes")
        validated[name] = value
    serialized = json.dumps(validated, ensure_ascii=False, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > _MAX_INPUT_BYTES:
        raise ValueError("Robot inputs allow at most 16384 UTF-8 JSON bytes")

    config_path = package_path / "robot.yaml"
    if not config_path.is_file():
        config_path = package_path / "package.yaml"
    try:
        with config_path.open("rb") as stream:
            contents = stream.read(_MAX_CONFIG_BYTES + 1)
        if len(contents) > _MAX_CONFIG_BYTES:
            raise ValueError(
                "Robot input declarations require a configuration of at most 1 MiB"
            )
        config = yaml.safe_load(contents)
    except (OSError, yaml.YAMLError, UnicodeError, RecursionError):
        raise ValueError("Unable to read Robot task input declarations") from None
    tasks = config.get("tasks") if isinstance(config, dict) else None
    task = tasks.get(task_name) if isinstance(tasks, dict) else None
    declaration = task.get("inputEnvironment") if isinstance(task, dict) else None
    if not isinstance(declaration, list) or len(declaration) > _MAX_INPUT_COUNT:
        raise ValueError(
            "Nonempty Robot inputs require a selected-task inputEnvironment list of at most 32 names"
        )
    allowed: set[str] = set()
    normalized_names: set[str] = set()
    for name in declaration:
        name = _validate_name(name)
        normalized = name.upper()
        if normalized in normalized_names:
            raise ValueError(
                "Robot inputEnvironment names must be unique ignoring case"
            )
        normalized_names.add(normalized)
        allowed.add(name)
    if not validated.keys() <= allowed:
        raise ValueError("Robot inputs contain names not declared by the selected task")
    return validated


@contextmanager
def robot_task_environment(environment: Mapping[str, str]) -> Iterator[Path]:
    """Keep RCC task values in an owned temporary directory until execution ends."""
    with tempfile.TemporaryDirectory(prefix="actions-robot-env-") as directory:
        path = Path(directory) / "env.json"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(dict(environment), stream)
        yield path
