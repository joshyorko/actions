"""Qualify the private offline restore helper from a supplied candidate wheel.

Run with the prepared package-local Poetry Python. This is deliberately not a
full CLI, dependency-resolution, historical-binary or active-job recovery gate.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PROBE = r"""
import hashlib
import importlib.metadata
import json
import sqlite3
import sys
import zipfile
from pathlib import Path
from actions.server import _datadir_restore as restore

wheel, root = map(Path, sys.argv[1:])
origin = Path(restore.__file__).resolve()
assert origin.is_relative_to(Path(sys.prefix).resolve()), origin
with zipfile.ZipFile(wheel) as archive:
    member = archive.read("actions/server/_datadir_restore.py")
assert origin.read_bytes() == member
source = root / "source"
source.mkdir()
attachment = source / "work_item_files" / "item-1" / "report.txt"
attachment.parent.mkdir(parents=True)
attachment.write_bytes(b"retained report")
with sqlite3.connect(source / "workitems.db") as db:
    db.execute("CREATE TABLE work_items (id TEXT PRIMARY KEY)")
    db.execute("INSERT INTO work_items VALUES ('item-1')")
    db.execute("CREATE TABLE work_item_files (id TEXT PRIMARY KEY, work_item_id TEXT, "
               "name TEXT, original_name TEXT, file_path TEXT, created_at TEXT)")
    db.execute("INSERT INTO work_item_files VALUES (?, ?, ?, ?, ?, ?)",
               ("file-1", "item-1", "report.txt", "report.txt", str(attachment), "now"))
original = (source / "workitems.db").read_bytes()
manifest = restore.capture_offline_manifest(source, offline=True)
target = root / "relocated"
receipt = restore.restore_offline(manifest, target, offline=True)
with sqlite3.connect(target / "workitems.db") as db:
    path = Path(db.execute("SELECT file_path FROM work_item_files").fetchone()[0])
assert path == target / "work_item_files/item-1/report.txt"
assert path.read_bytes() == b"retained report"
assert (source / "workitems.db").read_bytes() == original
assert receipt.rebased_attachments == 1
attachment.write_bytes(b"tampered")
try:
    restore.restore_offline(manifest, root / "refused", offline=True)
except ValueError:
    pass
else:
    raise AssertionError("Changed retained bytes were admitted")
assert not (root / "refused").exists()
print(json.dumps({"version": importlib.metadata.version("actions-runtime"),
                  "origin": str(origin), "helper_sha256": hashlib.sha256(member).hexdigest(),
                  "relocation": "pass", "source_preservation": "pass",
                  "tamper_rejection": "pass"}, sort_keys=True))
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    root = args.evidence.resolve()
    root.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CONDA_PREFIX"):
        environment.pop(key, None)
    python = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    commands = [
        [sys.executable, "-m", "venv", str(root / "venv")],
        [
            str(python),
            "-I",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            str(wheel),
        ],
        [str(python), "-I", "-c", PROBE, str(wheel), str(root)],
    ]
    receipt = {
        "wheel": str(wheel),
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "scope": "installed private offline SQLite restore helper",
        "result": "incomplete",
        "steps": [],
    }
    try:
        for index, command in enumerate(commands):
            result = subprocess.run(
                command,
                cwd=root,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            (root / f"step-{index}.log").write_text(result.stdout)
            receipt["steps"].append(
                {"command": command, "returncode": result.returncode}
            )
            result.check_returncode()
        receipt["result"] = "pass"
    finally:
        (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
