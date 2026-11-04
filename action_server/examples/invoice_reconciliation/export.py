"""Stage an allowlisted local example and candidate artifacts, without publication."""

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent
REPOSITORY = EXAMPLE.parents[2]
FILES = (
    "README.md",
    "LICENSE",
    "template.json",
    "demo.py",
    "runtime.py",
    "prepare.py",
    "source.py",
    "verify.py",
    "host.html",
    "data/invoices.csv",
    "data/purchase_orders.csv",
    "data/ledger.csv",
)


def wheel(path: Path, name: str, version: str):
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("regular absolute local wheel required")
    with zipfile.ZipFile(path) as archive:
        metadata = BytesParser().parsebytes(
            archive.read(
                next(p for p in archive.namelist() if p.endswith(".dist-info/METADATA"))
            )
        )
        if metadata["Name"] != name or metadata["Version"] != version:
            raise ValueError("candidate wheel metadata mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--runtime-wheel", required=True, type=Path)
    parser.add_argument("--core-wheel", required=True, type=Path)
    parser.add_argument("--sdk-wheel", required=True, type=Path)
    parser.add_argument("--canvas", required=True, type=Path)
    args = parser.parse_args()
    if not args.output.is_absolute() or args.output.exists():
        raise ValueError("fresh absolute task-owned output required")
    pins = json.loads((EXAMPLE / "template.json").read_text())["pins"]
    candidates = {
        "actions-runtime": args.runtime_wheel,
        "actions-core": args.core_wheel,
        "actions-work-items": args.sdk_wheel,
    }
    for name, path in candidates.items():
        wheel(path, name, pins[name])
    if (
        not args.canvas.is_absolute()
        or args.canvas.is_symlink()
        or not args.canvas.is_file()
    ):
        raise ValueError("regular absolute built Canvas resource required")
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True
    ).strip()
    # A dirty example cannot be represented by the recorded source commit.
    changed = subprocess.check_output(
        ["git", "status", "--porcelain", "--", str(EXAMPLE)], cwd=REPOSITORY, text=True
    )
    if changed:
        raise ValueError("commit the example before export")
    args.output.mkdir(parents=True)
    for relative in FILES:
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(EXAMPLE / relative, target)
    shutil.copyfile(args.canvas, args.output / "canvas.html")
    (args.output / "wheels").mkdir()
    for value in candidates.values():
        shutil.copyfile(value, args.output / "wheels" / value.name)
    # Reuse Poetry's graph and the existing verified public-floor constants.
    lock_path = REPOSITORY / "action_server/poetry.lock"
    packages = tomllib.loads(lock_path.read_text())["package"]
    versions = {
        p["name"]: p["version"]
        for p in packages
        if "main" in p["groups"] and p["files"]
    }
    hashes = {
        f["file"]: f["hash"].removeprefix("sha256:")
        for p in packages
        if "main" in p["groups"]
        for f in p["files"]
        if f["file"].endswith(".whl")
    }
    floor_path = REPOSITORY / "action_server/scripts/verify_published_runtime_floor.py"
    spec = importlib.util.spec_from_file_location("owned_public_floor", floor_path)
    floor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(floor)
    for name, value in floor.EXPECTED_PUBLIC_PACKAGES.items():
        if name in candidates:
            continue
        versions[name] = value["version"]
        hashes[value["url"].rsplit("/", 1)[1]] = value["sha256"]
    versions.update({name: pins[name] for name in candidates})
    (args.output / "dependencies.constraints").write_text(
        "".join(f"{name}=={version}\n" for name, version in sorted(versions.items()))
    )
    (args.output / "dependency-hashes.json").write_text(
        json.dumps(
            {
                "schema": "actions.example-wheel-lock/v1",
                "poetry_lock_sha256": hashlib.sha256(
                    lock_path.read_bytes()
                ).hexdigest(),
                "public_floor_verifier_sha256": hashlib.sha256(
                    floor_path.read_bytes()
                ).hexdigest(),
                "public_floor": floor.EXPECTED_PUBLIC_PACKAGES,
                "files": hashes,
            },
            indent=2,
        )
        + "\n"
    )
    files = {
        str(p.relative_to(args.output)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(args.output.rglob("*"))
        if p.is_file()
    }
    manifest = {
        "schema": "actions.example-export/v1",
        "source": source,
        "example": "synthetic-invoice-reconciliation/0.2.0",
        "engine_source_copy": False,
        "publication": False,
        "files": files,
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
