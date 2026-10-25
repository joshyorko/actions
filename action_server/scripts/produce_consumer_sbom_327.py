"""Pinned CycloneDX producer for an explicit owned installed Runtime consumer.

No publication or signing. Raw declared dependencies and selected-profile graph
remain separate. Strict active-graph failures are retained, never rewritten away.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from qualify_consumer_inventory_327 import compare_cyclonedx_graph, qualify
from qualify_declared_graph_327 import explain_declaration_graph
from qualify_wheel_inventory_327 import qualify as qualify_wheel

PRODUCER_VERSION = "7.5.0"
ROOT = Path(__file__).resolve().parents[2]
INSTALLED_PROBE = r"""
import hashlib, importlib.metadata, json, pathlib, sys
inventory = json.loads(pathlib.Path(sys.argv[1]).read_text())
distribution = importlib.metadata.distribution("actions-runtime")
assert distribution.version == inventory["version"]
count = 0
for item in inventory["inventory"]:
    if item["path"].endswith(".dist-info/RECORD"):
        continue  # pip rewrites installed RECORD, not payload/metadata bytes.
    path = pathlib.Path(distribution.locate_file(item["path"])).resolve()
    assert path.is_relative_to(pathlib.Path(sys.prefix).resolve()), path
    data = path.read_bytes()
    assert len(data) == item["size"] and hashlib.sha256(data).hexdigest() == item["sha256"], path
    count += 1
print(json.dumps({"matched_installed_members": count, "prefix": sys.prefix}))
"""


def producer_command(consumer_python, output):
    return [
        sys.executable,
        "-m",
        "cyclonedx_py",
        "environment",
        str(consumer_python),
        "--spec-version",
        "1.6",
        "--output-format",
        "JSON",
        "--output-reproducible",
        "--validate",
        "--output-file",
        str(output),
    ]


def run(command, directory, label):
    environment = os.environ.copy()
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "SOURCE_DATE_EPOCH",
    ):
        environment.pop(key, None)
    try:
        completed = subprocess.run(
            command, cwd=directory, env=environment, capture_output=True, timeout=120
        )
    except subprocess.TimeoutExpired as error:
        (directory / f"{label}.stdout").write_bytes(error.stdout or b"")
        (directory / f"{label}.stderr").write_bytes(error.stderr or b"")
        raise
    (directory / f"{label}.stdout").write_bytes(completed.stdout)
    (directory / f"{label}.stderr").write_bytes(completed.stderr)
    completed.check_returncode()
    return completed.stdout


def produce(args):
    output = args.output_dir.absolute()
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    receipt = {"result": "incomplete", "scope": "installed Python consumer only"}
    try:
        version = importlib.metadata.version("cyclonedx-bom")
        if version != PRODUCER_VERSION:
            raise ValueError("unexpected CycloneDX producer version")
        receipt["producer_version"] = version
        consumer = args.consumer_python.absolute()
        if consumer == Path(sys.executable).absolute():
            raise ValueError("producer must be separate from consumer environment")
        inventory = qualify_wheel(
            args.runtime_wheel, args.expected_sha256, args.expected_runtime
        )
        (output / "wheel-inventory.json").write_text(
            json.dumps(inventory, indent=2) + "\n"
        )
        receipt["wheel_sha256"] = inventory["wheel_sha256"]
        receipt["runtime_version"] = inventory["version"]
        for name, path in (
            ("runtime-lock.toml", args.runtime_lock),
            ("producer-lock.toml", ROOT / "devutils/poetry.lock"),
        ):
            with path.open("rb") as stream:
                data = stream.read(8 * 1024**2 + 1)
            if len(data) > 8 * 1024**2:
                raise ValueError("lockfile exceeds byte bound")
            (output / name).write_bytes(data)
            receipt[name + "_sha256"] = hashlib.sha256(data).hexdigest()
        inspect_command = [str(consumer), "-I", "-m", "pip", "inspect"]
        before = run(inspect_command, output, "inspect-before")
        inspection = json.loads(before)
        qualification = qualify(
            inspection,
            tomllib.loads((output / "runtime-lock.toml").read_text()),
            args.expected_runtime,
            args.extra,
        )
        (output / "resolved-graph.json").write_text(
            json.dumps(qualification, indent=2) + "\n"
        )
        receipt["inspect_sha256"] = hashlib.sha256(before).hexdigest()
        receipt["selected_extras"] = qualification["selected_extras"]
        probe = [
            str(consumer),
            "-I",
            "-c",
            INSTALLED_PROBE,
            str(output / "wheel-inventory.json"),
        ]
        run(probe, output, "installed-before")
        command = producer_command(consumer, output / "python-consumer.cdx.json")
        receipt["producer_command"] = command
        run(command, output, "producer")
        after = run(inspect_command, output, "inspect-after")
        if json.loads(after) != inspection:
            raise ValueError("consumer metadata changed during production")
        run(probe, output, "installed-after")
        with (output / "python-consumer.cdx.json").open("rb") as stream:
            sbom = stream.read(32 * 1024**2 + 1)
        if len(sbom) > 32 * 1024**2:
            raise ValueError("SBOM exceeds byte bound")
        receipt["sbom_sha256"] = hashlib.sha256(sbom).hexdigest()
        document = json.loads(sbom)
        if document.get("specVersion") != "1.6":
            raise ValueError("unexpected SBOM schema version")
        reconciliation = explain_declaration_graph(document, inspection, qualification)
        (output / "declaration-reconciliation.json").write_text(
            json.dumps(reconciliation, indent=2) + "\n"
        )
        receipt["sbom_dependencies"] = "DECLARED"
        receipt[
            "qualification_scope"
        ] = "dependency inventory and provenance evidence only"
        receipt["active_graph_evidence"] = "resolved-graph.json"
        try:
            compare_cyclonedx_graph(document, qualification)
        except ValueError as error:
            receipt["strict_active_graph"] = {"result": "failed", "error": str(error)}
        else:
            receipt["strict_active_graph"] = {"result": "pass"}
        receipt["explained_inactive_edges"] = len(reconciliation["differences"])
        receipt["evidence_sha256"] = {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in ("resolved-graph.json", "declaration-reconciliation.json")
        }
        receipt["result"] = "pass"
    except BaseException as error:
        receipt["result"] = "failed"
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-python", type=Path, required=True)
    parser.add_argument("--runtime-wheel", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-runtime", required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--extra", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    produce(parser.parse_args())


if __name__ == "__main__":
    main()
