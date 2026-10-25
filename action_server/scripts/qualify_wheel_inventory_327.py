"""Read-only wheel inventory qualification; declarations are not a resolved SBOM."""

import argparse
import base64
import csv
import hashlib
import io
import json
import stat
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath


def qualify(wheel, expected_sha256, expected_version):
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError("selected wheel digest mismatch")
    with zipfile.ZipFile(wheel) as archive:
        members = archive.infolist()
        if len(members) > 100_000 or sum(m.file_size for m in members) > 1024**3:
            raise ValueError("wheel inventory exceeds bounds")
        names = [m.filename for m in members]
        if len(set(names)) != len(names):
            raise ValueError("duplicate archive member")
        for member in members:
            path = PurePosixPath(member.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in member.filename
                or member.is_dir()
                or stat.S_ISLNK(member.external_attr >> 16)
            ):
                raise ValueError("unsafe archive member")
        metadata_names = [n for n in names if n.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise ValueError("expected one METADATA")
        metadata_path = metadata_names[0]
        metadata = BytesParser().parsebytes(archive.read(metadata_path))
        if metadata.get_all("Name") != ["actions-runtime"] or metadata.get_all(
            "Version"
        ) != [expected_version]:
            raise ValueError("distribution identity mismatch")
        record_path = metadata_path.removesuffix("METADATA") + "RECORD"
        rows = list(csv.reader(io.StringIO(archive.read(record_path).decode("utf-8"))))
        records = {}
        for row in rows:
            if len(row) != 3 or row[0] in records:
                raise ValueError("malformed or duplicate RECORD member")
            records[row[0]] = row[1:]
        if set(records) != set(names):
            raise ValueError("RECORD inventory mismatch")
        inventory = []
        for name in sorted(names):
            body = archive.read(name)
            member_digest = hashlib.sha256(body).hexdigest()
            if name == record_path:
                if records[name] != ["", ""]:
                    raise ValueError("RECORD self-entry must be unhashed")
            else:
                encoded = base64.urlsafe_b64encode(hashlib.sha256(body).digest())
                expected = ["sha256=" + encoded.rstrip(b"=").decode(), str(len(body))]
                if records[name] != expected:
                    raise ValueError(f"RECORD bytes mismatch: {name}")
            inventory.append({"path": name, "size": len(body), "sha256": member_digest})
    return {
        "result": "pass",
        "wheel_sha256": digest,
        "version": expected_version,
        "metadata_path": metadata_path,
        "declared_requires_dist": metadata.get_all("Requires-Dist", []),
        "dependency_scope": "wheel METADATA declarations only; not installed/resolved SBOM",
        "inventory": inventory,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = qualify(args.wheel, args.expected_sha256, args.expected_version)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
