"""Clean-install one built Runtime wheel with its released Core and Helper floors."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import zipfile
from email.parser import BytesParser
from pathlib import Path

EXPECTED_CORE = "1.0.2"
EXPECTED_HELPER = "1.0.3"
EXPECTED_RUNTIME = "1.0.3"


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


def verify_installed(python: Path, isolated_workdir: Path) -> None:
    checkout_root = Path(__file__).resolve().parents[1]
    probe = f"""
from importlib.metadata import version
import pathlib
assert version('actions-runtime') == {EXPECTED_RUNTIME!r}
assert version('actions-core') == {EXPECTED_CORE!r}
assert version('actions-http-helper') == {EXPECTED_HELPER!r}
import actions
import actions.server
import actions.mcp
import actions_http
checkout = pathlib.Path({str(checkout_root)!r})
for module in (actions, actions.server, actions.mcp, actions_http):
    try:
        pathlib.Path(module.__file__).resolve().relative_to(checkout)
    except ValueError:
        pass
    else:
        raise AssertionError(f'Imported from checkout: {{module.__file__}}')
print('registry-floor versions and imports passed')
"""
    subprocess.run(
        [str(python), "-m", "pip", "check"], check=True, cwd=isolated_workdir
    )
    subprocess.run([str(python), "-c", probe], check=True, cwd=isolated_workdir)
    subprocess.run(
        [str(python), "-m", "actions.server", "version"],
        check=True,
        cwd=isolated_workdir,
    )


def main() -> None:
    wheel = select_runtime_wheel(Path(sys.argv[1]))
    with tempfile.TemporaryDirectory(prefix="runtime-registry-floor-") as temp:
        env_dir = Path(temp) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(env_dir)], check=True)
        python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--isolated",
                "--index-url",
                "https://pypi.org/simple",
                "--only-binary=:all:",
                str(wheel.resolve()),
            ],
            check=True,
        )
        verify_installed(python, Path(temp))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_published_runtime_floor.py WHEEL_DIRECTORY")
    main()
