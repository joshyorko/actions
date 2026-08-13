#!/usr/bin/env python3
"""Verify that the actions-core wheel works from an isolated installation."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path


TIMEOUT_SECONDS = 60


def _run(argv, cwd, env):
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"command timed out: argv={argv!r}, cwd={cwd}, returncode=None, "
            f"stdout={error.stdout!r}, stderr={error.stderr!r}"
        ) from error
    if result.returncode:
        raise RuntimeError(
            f"command failed: argv={argv!r}, cwd={cwd}, "
            f"returncode={result.returncode}, stdout={result.stdout!r}, "
            f"stderr={result.stderr!r}"
        )
    return result


def _venv_bin(venv_dir):
    return Path(venv_dir) / ("Scripts" if os.name == "nt" else "bin")


def verify(wheel):
    wheel = Path(wheel).resolve()
    if wheel.suffix != ".whl" or not wheel.is_file():
        raise ValueError(f"expected an existing wheel: {wheel}")

    with tempfile.TemporaryDirectory(prefix="actions-core-clean-") as temporary:
        root = Path(temporary)
        venv_dir = root / "venv"
        fixture_dir = root / "fixture"
        fixture_dir.mkdir()
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        python = _venv_bin(venv_dir) / ("python.exe" if os.name == "nt" else "python")
        command_dir = python.parent
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("VIRTUAL_ENV", None)
        environment["PATH"] = os.pathsep.join(
            [str(command_dir), environment.get("PATH", "")]
        )

        _run([str(python), "-m", "pip", "install", str(wheel)], root, environment)
        metadata = json.loads(
            _run(
                [
                    str(python),
                    "-c",
                    "import importlib.metadata as m, json; "
                    "d=m.distribution('actions-core'); "
                    "print(json.dumps({'name': d.metadata['Name'], 'version': d.version, "
                    "'scripts': [{'name': e.name, 'value': e.value} for e in d.entry_points "
                    "if e.group == 'console_scripts'], 'direct_url': "
                    "json.loads(d.read_text('direct_url.json')) if d.read_text('direct_url.json') else None}))",
                ],
                root,
                environment,
            ).stdout
        )
        if metadata["name"] != "actions-core" or metadata["version"] != "1.0.0":
            raise AssertionError(f"unexpected installed distribution: {metadata!r}")
        scripts = [
            script for script in metadata["scripts"] if script["name"] == "actions"
        ]
        if scripts != [{"name": "actions", "value": "actions.cli:main"}]:
            raise AssertionError(f"unexpected actions entry points: {scripts!r}")
        if metadata["direct_url"] and metadata["direct_url"].get("dir_info"):
            raise AssertionError(
                "installed distribution contains editable direct_url metadata"
            )

        executable = shutil.which("actions", path=str(command_dir))
        if executable is None or Path(executable).parent != command_dir:
            raise AssertionError(
                f"actions command is not owned by the clean environment: {executable!r}"
            )
        action_file = fixture_dir / "actions.py"
        action_file.write_text(
            "from actions import action\n"
            "@action\n"
            "def hello(name: str = 'world') -> str:\n"
            "    return f'Hello, {name}!'\n"
        )
        listed = _run(
            [executable, "list", str(action_file), "--skip-lint"],
            fixture_dir,
            environment,
        )
        if [entry["name"] for entry in json.loads(listed.stdout)] != ["hello"]:
            raise AssertionError(f"unexpected list output: {listed.stdout!r}")
        output_file = fixture_dir / "result.json"
        _run(
            [
                executable,
                "run",
                str(action_file),
                "-a",
                "hello",
                f"--json-output={output_file}",
            ],
            fixture_dir,
            environment,
        )
        if json.loads(output_file.read_text()) != {
            "result": "Hello, world!",
            "message": "",
            "status": "PASS",
        }:
            raise AssertionError(f"unexpected run output: {output_file.read_text()!r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    verify(args.wheel)
    print(f"verified clean actions-core wheel: {args.wheel.resolve()}")


if __name__ == "__main__":
    main()
