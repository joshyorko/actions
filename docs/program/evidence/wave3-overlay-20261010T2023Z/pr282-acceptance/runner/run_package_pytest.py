from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository))
from developer.toolkit import package_environment

package_directory = repository / "action_server"
environment = package_environment(package_directory)
arguments = sys.argv[1:]
while arguments and arguments[0] == "--env":
    key, separator, value = arguments[1].partition("=")
    if not separator:
        raise SystemExit("--env expects KEY=VALUE")
    environment[key] = value
    arguments = arguments[2:]
subprocess.run(
    ["poetry", "run", "pytest", *arguments],
    cwd=package_directory,
    env=environment,
    check=True,
)
