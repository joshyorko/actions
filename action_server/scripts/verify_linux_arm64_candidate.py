"""Test-only installed Runtime/RCC candidate proof; never a release pin writer.

Run inside an isolated RCC test environment on native Linux ARM64. Install the
candidate Runtime wheel there first; do not run from an editable source install.
The RCC path/digest override exists only in child CLI processes in this harness.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rcc", type=Path, required=True)
    parser.add_argument("--rcc-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine().lower() not in (
        "aarch64",
        "arm64",
    ):
        parser.error("native Linux ARM64 required; emulation/x64 is not acceptance")
    if not os.environ.get("RCC_VERSION"):
        parser.error("run inside an isolated RCC test environment")
    rcc = args.rcc.resolve(strict=True)
    actual = hashlib.sha256(rcc.read_bytes()).hexdigest()
    if actual != args.rcc_sha256:
        parser.error("candidate RCC checksum mismatch")

    import actions.server
    from actions.server import _rcc_platform

    distribution = importlib.metadata.distribution("actions-runtime")
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    if direct.get("dir_info") is not None:
        parser.error("install a candidate wheel, not an editable/source tree")
    wheel_hash = direct.get("archive_info", {}).get("hashes", {}).get("sha256")
    if not wheel_hash:
        parser.error("installed candidate wheel must retain its direct_url SHA256")
    _rcc_platform.LINUX_ARM64_RELEASE_SHA256["candidate-test-only"] = actual
    _rcc_platform.verify_rcc(rcc, "candidate-test-only", "rcc-linuxarm64")
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    with tempfile.TemporaryDirectory(prefix="runtime-arm64-candidate-") as temporary:
        root = Path(temporary)
        wrapper = root / "candidate_cli.py"
        wrapper.write_text(
            "from pathlib import Path\n"
            "from actions.server import _download_rcc, _rcc_platform\n"
            f"_rcc_platform.LINUX_ARM64_RELEASE_SHA256[_download_rcc.RCC_VERSION] = {actual!r}\n"
            f"_download_rcc.get_default_rcc_location = lambda: Path({str(rcc)!r})\n"
            "from actions.server.cli import main\nmain()\n"
        )
        package = root / "arm64_synthetic"
        package.mkdir()
        (package / "package.yaml").write_text(
            "name: arm64-synthetic\nversion: 0.1\nspec-version: v2\n"
            "dependencies:\n  conda-forge:\n    - python=3.12.15\n"
            "  pypi:\n    - actions-core=1.1.0\n"
        )
        (package / "synthetic_actions.py").write_text(
            "from actions import action\n\n@action\n"
            "def echo(value: str) -> str:\n"
            '    """Return a harmless synthetic input.\n\n'
            '    Args:\n        value: Synthetic text.\n    """\n'
            "    return 'arm64:' + value\n"
        )
        datadir = root / "datadir"
        base = [sys.executable, str(wrapper)]
        with (root / "import.log").open("w+") as log:
            result = subprocess.run(
                [*base, "import", "--datadir", str(datadir)],
                cwd=package,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=600,
            )
            if result.returncode:
                log.seek(0)
                raise RuntimeError(log.read())
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        with (root / "server.log").open("w+") as log:
            process = subprocess.Popen(
                [
                    *base,
                    "start",
                    "--datadir",
                    str(datadir),
                    "--address",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--actions-sync=false",
                    "--api-key",
                    "synthetic-only",
                ],
                cwd=package,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                url = f"http://127.0.0.1:{port}"
                deadline = time.monotonic() + 90
                while True:
                    try:
                        with urllib.request.urlopen(
                            url + "/openapi.json", timeout=2
                        ) as response:
                            schema = json.load(response)
                        break
                    except (OSError, urllib.error.URLError):
                        if process.poll() is not None or time.monotonic() > deadline:
                            log.seek(0)
                            raise RuntimeError(log.read())
                        time.sleep(0.25)
                routes = [
                    path for path in schema["paths"] if path.endswith("/echo/run")
                ]
                if len(routes) != 1:
                    raise RuntimeError(f"expected one synthetic echo route: {routes}")
                request = urllib.request.Request(
                    url + routes[0],
                    data=b'{"value":"synthetic"}',
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer synthetic-only",
                    },
                )
                with urllib.request.urlopen(request, timeout=120) as response:
                    result = json.load(response)
                if result != "arm64:synthetic":
                    raise RuntimeError(f"unexpected synthetic result: {result!r}")
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
        args.output.write_text(
            json.dumps(
                {
                    "qualification": "candidate-test-only; not release or deployment acceptance",
                    "machine": platform.machine(),
                    "python": sys.version,
                    "runtime_version": distribution.version,
                    "runtime_import": str(Path(actions.server.__file__).resolve()),
                    "installed_wheel_sha256": wheel_hash,
                    "rcc_sha256": actual,
                    "rcc_version": subprocess.check_output(
                        [str(rcc), "version"], text=True
                    ).strip(),
                    "import_exit": 0,
                    "synthetic_result": result,
                    "listener": "127.0.0.1 only; stopped",
                    "temporary_files": "removed",
                },
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
