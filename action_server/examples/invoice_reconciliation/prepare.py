"""Prepare a fresh wheel-only consumer, or launch its verified local example.

This is a distribution acceptance fixture, not a replacement developer bootstrap.
Use Python 3.12.15 from the pinned RCC gateway. No project environment is reused.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_bundle(bundle):
    manifest = json.loads((bundle / "manifest.json").read_text())
    if (
        manifest["schema"] != "actions.example-export/v1"
        or manifest["engine_source_copy"]
    ):
        raise ValueError("exact Actions-owned example export required")
    for relative, expected in manifest["files"].items():
        path = bundle / relative
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(bundle)
            or digest(path) != expected
        ):
            raise ValueError("bundle input changed")
    return manifest


def run(command, log, *, env, cwd):
    with log.open("w") as stream:
        subprocess.run(
            command,
            env=env,
            cwd=cwd,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=900,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--offline-wheelhouse", type=Path)
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parent
    manifest = verify_bundle(bundle)
    dependency_lock = json.loads((bundle / "dependency-hashes.json").read_text())
    if dependency_lock["schema"] != "actions.example-wheel-lock/v1":
        raise ValueError("versioned consumer wheel lock required")
    root = args.root
    if not root.is_absolute() or root.is_symlink():
        raise ValueError("absolute task-owned consumer root required")
    environment = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "POETRY_ACTIVE",
    ):
        environment.pop(key, None)
    environment.update(
        ROBOTS_HOME=str(root / "robots"),
        ROBOCORP_HOME=str(root / "outer-rcc"),
        ACTIONS_HOME=str(root / "outer-rcc"),
        XDG_CACHE_HOME=str(root / "cache"),
        PIP_CACHE_DIR=str(root / "pip-cache"),
        PIP_DISABLE_PIP_VERSION_CHECK="1",
        PIP_NO_CACHE_DIR="1",
    )
    python = root / "venv/bin/python"
    if args.launch:
        consumer = json.loads((root / "consumer.json").read_text())
        if consumer["manifest_sha256"] != digest(bundle / "manifest.json") or consumer[
            "bundle"
        ] != str(bundle):
            raise ValueError("consumer bundle identity differs")
        environment.update(
            ACTIONS_INVOICE_SDK_WHEEL=str(
                bundle / "wheels/actions_work_items-0.5.0a1-py3-none-any.whl"
            ),
            ACTIONS_INVOICE_CANVAS_RESOURCE=str(bundle / "canvas.html"),
        )
        os.execve(
            python,
            [
                str(python),
                "-I",
                str(bundle / "demo.py"),
                "--state",
                str(root / "demo"),
                "--port",
                str(args.port),
            ],
            environment,
        )
    if root.exists() or sys.version_info[:3] != (3, 12, 15) or sys.platform != "linux":
        raise ValueError("fresh root, Linux and pinned Python3.12.15 required")
    root.mkdir(parents=True, mode=0o700)
    venv.create(root / "venv", with_pip=True)
    wheels = root / "wheelhouse"
    wheels.mkdir()
    sdk = bundle / "wheels/actions_work_items-0.5.0a1-py3-none-any.whl"
    runtime = next((bundle / "wheels").glob("actions_runtime-*.whl"))
    pip = [
        str(python),
        "-I",
        "-m",
        "pip",
        "--disable-pip-version-check",
        "--no-cache-dir",
    ]
    if args.offline_wheelhouse is not None:
        source = args.offline_wheelhouse.resolve()
        measured = json.loads((source / "wheelhouse.json").read_text())
        if measured["bundle_manifest_sha256"] != digest(bundle / "manifest.json"):
            raise ValueError("offline wheelhouse belongs to another bundle")
        for name, expected in measured["files"].items():
            path = source / name
            if Path(name).name != name or path.is_symlink() or digest(path) != expected:
                raise ValueError("offline wheel changed")
            shutil.copyfile(path, wheels / name)
    else:
        run(
            [
                *pip,
                "download",
                "--only-binary=:all:",
                "--constraint",
                str(bundle / "dependencies.constraints"),
                "--dest",
                str(wheels),
                str(runtime) + "[data-duckdb]",
                str(sdk),
            ],
            root / "download.log",
            env=environment,
            cwd=root,
        )
    # The exact downloaded closure, including local candidates, is frozen by hash.
    measured = {p.name: digest(p) for p in sorted(wheels.glob("*.whl"))}
    allowed = dict(
        dependency_lock["files"], **{p.name: digest(p) for p in (runtime, sdk)}
    )
    if any(allowed.get(name) != value for name, value in measured.items()):
        raise ValueError(
            "downloaded artifact differs from the authoritative dependency lock"
        )
    for candidate in (runtime, sdk):
        if measured.get(candidate.name) != digest(candidate):
            raise ValueError("candidate wheel absent or altered in closure")
    (wheels / "wheelhouse.json").write_text(
        json.dumps(
            {
                "bundle_manifest_sha256": digest(bundle / "manifest.json"),
                "files": measured,
            },
            indent=2,
        )
        + "\n"
    )
    run(
        [
            *pip,
            "install",
            "--no-index",
            "--only-binary=:all:",
            "--find-links",
            str(wheels),
            "--report",
            str(root / "install-report.json"),
            str(wheels / runtime.name) + "[data-duckdb]",
            str(wheels / sdk.name),
        ],
        root / "install.log",
        env=environment,
        cwd=root,
    )
    run([*pip, "check"], root / "pip-check.log", env=environment, cwd=root)
    probe = """
import hashlib,importlib,importlib.metadata,json,sys
from pathlib import Path
prefix=Path(sys.prefix).resolve(); result={"prefix":str(prefix),"sys_path":sys.path,"modules":{}}
for name in ("actions.server.data_queries.canvas_mcp","actions.work_items","duckdb","actions","actions_http_helper"):
 try: module=importlib.import_module(name)
 except ModuleNotFoundError:
  if name in ("actions","actions_http_helper"): continue
  raise
 if module.__file__:
  path=Path(module.__file__).resolve(); assert path.is_relative_to(prefix),path
  result["modules"][name]={"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
for name in ("actions-runtime","actions-work-items"):
 dist=importlib.metadata.distribution(name); origin=json.loads(dist.read_text("direct_url.json")); path=Path(origin["url"].removeprefix("file://")); assert hashlib.sha256(path.read_bytes()).hexdigest()==origin["archive_info"]["hashes"]["sha256"]
 result[name]={"version":dist.version,"origin":origin}
print(json.dumps(result,indent=2))
"""
    run(
        [str(python), "-I", "-c", probe],
        root / "identity.json",
        env=environment,
        cwd=root,
    )
    (root / "consumer.json").write_text(
        json.dumps(
            {
                "schema": "actions.invoice-consumer/v1",
                "bundle": str(bundle),
                "manifest_sha256": digest(bundle / "manifest.json"),
                "source": manifest["source"],
                "preparation": "offline-wheelhouse"
                if args.offline_wheelhouse
                else "cold-network-download-no-cache",
                "python": sys.version,
                "wheelhouse": measured,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        f"Prepared fresh consumer. Launch: {sys.executable} {__file__} --root {root} --launch --port {args.port}"
    )


if __name__ == "__main__":
    main()
