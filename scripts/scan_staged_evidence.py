"""Reject credential-valued fields before publishing staged JSON evidence.

This checks Git's index, not a possibly different working copy. It reports paths
and field names only. It is not a general secret detector or screenshot review.
"""

import argparse
import json
import subprocess
from pathlib import Path


SENSITIVE_FIELDS = {
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "appsession",
    "api_key",
    "apikey",
    "authorization",
    "client_secret",
    "password",
}


def unique_object(pairs):
    value = {}
    for key, child in pairs:
        if key in value:
            raise ValueError("ambiguous JSON evidence")
        value[key] = child
    return value


def inspect(value, path, errors):
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                key.lower() in SENSITIVE_FIELDS
                and isinstance(child, str)
                and child
                and not (child.startswith("[redacted") and child.endswith("]"))
            ):
                errors.append(f"{path}: credential-valued field {key!r}")
            else:
                inspect(child, path, errors)
    elif isinstance(value, list):
        for child in value:
            inspect(child, path, errors)


def scan(repo):
    names = (
        subprocess.check_output(
            [
                "git",
                "-C",
                str(repo),
                "diff",
                "--cached",
                "--name-only",
                "-z",
                "--diff-filter=ACMR",
            ]
        )
        .decode()
        .split("\0")
    )
    errors = []
    for name in names:
        if not name.startswith("docs/program/evidence/") or not name.endswith(".json"):
            continue
        raw = subprocess.check_output(["git", "-C", str(repo), "show", ":" + name])
        try:
            value = json.loads(raw, object_pairs_hook=unique_object)
        except (ValueError, UnicodeError):
            errors.append(f"{name}: invalid JSON evidence")
            continue
        inspect(value, name, errors)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    errors = scan(args.repo)
    for error in errors:
        print(error)
    if errors:
        print("Evidence scan failed; commit and push must not run.")
        return 1
    print(
        "Staged JSON evidence scan passed; screenshot/content review remains separate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
