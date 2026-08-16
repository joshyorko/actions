"""Cross-platform RCC developer task dispatcher."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
RCC_VERSION = "v18.18.1"
PACKAGES = ("actions", "actions-http-helper", "devutils", "work-items", "action_server")
PYPROJECTS = ("actions", "actions-http-helper", "devutils", "work-items", "action_server")
ACTIVE_ENVIRONMENT_VARIABLES = (
    "VIRTUAL_ENV",
    "POETRY_ACTIVE",
    "CONDA_PREFIX",
    "CONDA_DEFAULT_ENV",
    "CONDA_PROMPT_MODIFIER",
    "CONDA_SHLVL",
    "CONDA_EXE",
    "_CE_CONDA",
    "_CE_M",
    "PYTHONHOME",
    "PYTHONPATH",
)


def package_environment() -> dict[str, str]:
    """Keep package Poetry environments separate from RCC's holotree."""
    environment = os.environ.copy()
    for name in ACTIVE_ENVIRONMENT_VARIABLES:
        environment.pop(name, None)
    environment.update(
        {
            "POETRY_VIRTUALENVS_CREATE": "true",
            "POETRY_VIRTUALENVS_IN_PROJECT": "true",
            "POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES": "false",
        }
    )
    return environment


def run(command: list[str], cwd: Path = REPOSITORY_ROOT) -> None:
    """Run a command without shell parsing so it works on every RCC platform."""
    print("+", " ".join(command), f"(in {cwd})", flush=True)
    subprocess.run(command, cwd=cwd, env=package_environment(), check=True)


def poetry(package: str, *arguments: str) -> None:
    run(["poetry", *arguments], REPOSITORY_ROOT / package)


def doctor() -> None:
    required = ("python", "poetry", "invoke", "node", "go", "git")
    missing = [name for name in required if shutil.which(name) is None]
    if missing:
        raise SystemExit(f"RCC toolkit environment is missing: {', '.join(missing)}")

    active_rcc_version = os.environ.get("RCC_VERSION")
    if active_rcc_version and active_rcc_version != RCC_VERSION:
        raise SystemExit(
            f"RCC toolkit requires {RCC_VERSION}, active RCC is {active_rcc_version}"
        )

    print(f"Python: {sys.version.split()[0]}")
    commands = (
        ("poetry", "--version"),
        ("invoke", "--version"),
        ("node", "--version"),
        ("go", "version"),
    )
    for command in commands:
        run(list(command))

    for package in PYPROJECTS:
        directory = REPOSITORY_ROOT / package
        if not (directory / "pyproject.toml").is_file():
            raise SystemExit(f"Missing pyproject.toml: {directory}")
        if not (directory / "poetry.lock").is_file():
            raise SystemExit(f"Missing poetry.lock: {directory}")
    print("RCC developer toolkit checks passed.")


def bootstrap() -> None:
    run(["invoke", "install"])


def package_task(task: str) -> None:
    for package in PACKAGES:
        if package == "devutils":
            if task == "test":
                poetry(package, "run", "pytest", "tests")
            elif task == "lint":
                poetry(package, "run", "ruff", "check", "src", "tests")
            elif task == "typecheck":
                # devutils has no configured package typecheck gate. Do not
                # invent a stricter command than the package declares.
                continue
            else:
                raise ValueError(f"Unsupported devutils task: {task}")
        else:
            poetry(package, "run", "invoke", task)


def test() -> None:
    toolkit_test()
    package_task("test")


def toolkit_test() -> None:
    run([sys.executable, "-m", "ruff", "check", "developer"])
    run([sys.executable, "-m", "pytest", "developer/tests"])


def lint() -> None:
    package_task("lint")


def typecheck() -> None:
    package_task("typecheck")


def docs() -> None:
    run(["invoke", "docs"])


def check_all() -> None:
    doctor()
    lint()
    typecheck()
    test()


def frontend_test() -> None:
    run(["npm", "ci", "--no-audit", "--no-fund"], REPOSITORY_ROOT / "action_server" / "frontend")
    run(["npm", "run", "test"], REPOSITORY_ROOT / "action_server" / "frontend")


def build_community() -> None:
    # ``build-frontend`` is the community build in the public Action Server
    # task contract; it has no tier option. Keep this wiring explicit so an
    # Invoke CLI option drift is caught by the dispatcher contract test.
    poetry("action_server", "run", "invoke", "build-frontend")
    poetry("action_server", "run", "invoke", "build-executable", "--go-wrapper")


COMMANDS = {
    "doctor": doctor,
    "bootstrap": bootstrap,
    "test": test,
    "toolkit-test": toolkit_test,
    "lint": lint,
    "typecheck": typecheck,
    "docs": docs,
    "check-all": check_all,
    "frontend-test": frontend_test,
    "build-community": build_community,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=sorted(COMMANDS))
    arguments = parser.parse_args()
    COMMANDS[arguments.task]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
