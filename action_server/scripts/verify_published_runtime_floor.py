"""Clean-install one Runtime wheel and prove its released Core/Helper origins."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urlsplit

EXPECTED_CORE = "1.0.2"
EXPECTED_HELPER = "1.0.3"
EXPECTED_RUNTIME = "1.0.3"
EXPECTED_PUBLIC_PACKAGES = {
    "actions-core": {
        "version": EXPECTED_CORE,
        "url": "https://files.pythonhosted.org/packages/b6/ed/33c5999ac5e932434fcc5b392420efdf9b25922ca02a76622b856759ea16/actions_core-1.0.2-py3-none-any.whl",
        "sha256": "9d527edf540978172178894546add75f117f240786aec804cb75c308615a7e80",
    },
    "actions-http-helper": {
        "version": EXPECTED_HELPER,
        "url": "https://files.pythonhosted.org/packages/53/3b/cefc0608e6ec71697c60c68ede2efa306fd7d50b1736c4b6b094b3424dc6/actions_http_helper-1.0.3-py3-none-any.whl",
        "sha256": "46ed7ce0e0d3e2e05456d937b5b24bc9dfa0d7d4b98f8119b9fdf00d4fa7e9f9",
    },
}
REPO_ROOT = Path(__file__).resolve().parents[2]
IMPORT_PATH_MARKER = "REGISTRY_FLOOR_IMPORT_PATHS="


def select_runtime_wheel(directory: Path) -> Path:
    candidates = []
    for wheel in sorted(directory.glob("actions_runtime-*.whl")):
        if "-cp312-" not in wheel.name:
            continue
        with zipfile.ZipFile(wheel) as archive:
            metadata_paths = [
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_paths) != 1:
                raise ValueError(f"Expected one Runtime wheel METADATA: {wheel.name}")
            metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
            if metadata.get("Name") != "actions-runtime":
                raise ValueError(f"Unexpected distribution in {wheel.name}")
            if metadata.get("Version") != EXPECTED_RUNTIME:
                raise ValueError(f"Unexpected Runtime version in {wheel.name}")
        candidates.append(wheel)
    if len(candidates) != 1:
        raise ValueError(
            "Expected exactly one cp312 actions-runtime 1.0.3 wheel in "
            f"{directory}, found {len(candidates)}"
        )
    return candidates[0]


def isolated_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if source is None else source)
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "PYTHONSTARTUP"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def assert_no_checkout_imports(
    repository: Path,
    search_paths: list[str],
    module_files: dict[str, str],
) -> None:
    root = repository.resolve()
    offenders: list[str] = []
    entries = [
        (f"sys.path[{index}]", value) for index, value in enumerate(search_paths)
    ]
    entries.extend((f"module {name}", value) for name, value in module_files.items())
    for source, value in entries:
        if not value:
            value = "."
        path = Path(value).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        offenders.append(f"{source}: {path}")
    if offenders:
        raise RuntimeError(
            "Imports or module search paths point into the source checkout:\n"
            + "\n".join(offenders)
        )


def build_import_path_guard(repository: Path) -> str:
    """Return a child-interpreter preflight that rejects checkout search paths."""
    return f"""
import pathlib, sys
root = pathlib.Path({str(repository.resolve())!r})
offenders = []
for index, value in enumerate(sys.path):
    path = pathlib.Path(value or pathlib.Path.cwd()).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        continue
    offenders.append(f"sys.path[{{index}}]: {{path}}")
if offenders:
    message = "Python search paths point into the source checkout:\\n"
    raise SystemExit(message + "\\n".join(offenders))
"""


def verify_public_package_report(report_path: Path) -> dict[str, dict[str, str]]:
    report = json.loads(report_path.read_text())
    observed: dict[str, dict[str, str]] = {}
    for item in report.get("install", []):
        metadata = item.get("metadata", {})
        name = metadata.get("name", "").lower().replace("_", "-")
        if name not in EXPECTED_PUBLIC_PACKAGES:
            continue
        expected = EXPECTED_PUBLIC_PACKAGES[name]
        if metadata.get("version") != expected["version"]:
            raise RuntimeError(f"Unexpected {name} version in pip report")
        download = item.get("download_info", {})
        url = download.get("url", "")
        if url != expected["url"] or urlsplit(url).hostname != "files.pythonhosted.org":
            raise RuntimeError(f"Unexpected {name} public PyPI wheel URL")
        sha256 = download.get("archive_info", {}).get("hashes", {}).get("sha256")
        if sha256 != expected["sha256"]:
            raise RuntimeError(f"Unexpected {name} PyPI artifact SHA-256")
        observed[name] = {"version": expected["version"], "url": url, "sha256": sha256}
    if set(observed) != set(EXPECTED_PUBLIC_PACKAGES):
        missing = sorted(set(EXPECTED_PUBLIC_PACKAGES) - set(observed))
        raise RuntimeError(f"Pip report omits required public packages: {missing}")
    return observed


def install_command(python: Path, wheel: Path, report: Path) -> list[str]:
    return [
        str(python),
        "-m",
        "pip",
        "install",
        "--isolated",
        "--no-cache-dir",
        "--index-url",
        "https://pypi.org/simple",
        "--only-binary=:all:",
        "--report",
        str(report),
        str(wheel.resolve()),
    ]


def verify_installed(python: Path, isolated_workdir: Path, report_path: Path) -> None:
    environment = isolated_environment()
    guard = build_import_path_guard(REPO_ROOT)
    subprocess.run(
        [str(python), "-c", guard],
        check=True,
        cwd=isolated_workdir,
        env=environment,
    )
    probe = (
        guard
        + f"""
import json, pathlib, sys
from importlib.metadata import version
assert version('actions-runtime') == {EXPECTED_RUNTIME!r}
assert version('actions-core') == {EXPECTED_CORE!r}
assert version('actions-http-helper') == {EXPECTED_HELPER!r}
import actions
import actions.server
import actions.mcp
import actions_http
print({IMPORT_PATH_MARKER!r} + json.dumps({{
    'sys_path': [str(pathlib.Path.cwd()) if not entry else entry for entry in sys.path],
    'modules': {{
        'actions': actions.__file__,
        'actions.server': actions.server.__file__,
        'actions.mcp': actions.mcp.__file__,
        'actions_http': actions_http.__file__,
    }},
}}))
"""
    )
    subprocess.run(
        [str(python), "-m", "pip", "check"],
        check=True,
        cwd=isolated_workdir,
        env=environment,
    )
    result = subprocess.run(
        [str(python), "-c", probe],
        check=True,
        cwd=isolated_workdir,
        env=environment,
        capture_output=True,
        text=True,
    )
    line = next(
        (
            line
            for line in result.stdout.splitlines()
            if line.startswith(IMPORT_PATH_MARKER)
        ),
        None,
    )
    if line is None:
        raise RuntimeError("Installed-package probe did not report import paths")
    imports = json.loads(line[len(IMPORT_PATH_MARKER) :])
    assert_no_checkout_imports(REPO_ROOT, imports["sys_path"], imports["modules"])
    public_packages = verify_public_package_report(report_path)
    print(
        "Verified uncached PyPI Runtime dependency artifacts: "
        + json.dumps(public_packages, sort_keys=True)
    )
    subprocess.run(
        [str(python), "-m", "actions.server", "version"],
        check=True,
        cwd=isolated_workdir,
        env=environment,
    )


def main() -> None:
    wheel = select_runtime_wheel(Path(sys.argv[1]))
    with tempfile.TemporaryDirectory(prefix="runtime-registry-floor-") as temp:
        workdir = Path(temp)
        env_dir = workdir / "venv"
        subprocess.run(
            [sys.executable, "-m", "venv", str(env_dir)],
            check=True,
            env=isolated_environment(),
        )
        python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        report = workdir / "pip-install-report.json"
        subprocess.run(
            install_command(python, wheel, report),
            check=True,
            cwd=workdir,
            env=isolated_environment(),
        )
        verify_installed(python, workdir, report)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_published_runtime_floor.py WHEEL_DIRECTORY")
    main()
