#!/usr/bin/env python3
"""Refuse an explicitly budgeted local test run before storage exhaustion."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def check(path: Path, required_free_bytes: int) -> dict:
    if required_free_bytes <= 0:
        raise ValueError("a positive explicit free-space budget is required")
    resolved = path.resolve(strict=True)
    usage = shutil.disk_usage(resolved)
    return {
        "path": str(resolved),
        "required_free_bytes": required_free_bytes,
        "available_bytes": usage.free,
        "status": "PASS" if usage.free >= required_free_bytes else "BLOCKED",
        "scope": "point-in-time preflight; concurrent writers still require monitoring",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--required-free-bytes", type=int, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    result = check(args.path, args.required_free_bytes)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.report:
        # Do not overwrite a previous preflight receipt.
        with args.report.open("x") as stream:
            stream.write(encoded)
    print(encoded, end="")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
