#!/usr/bin/env python3
"""Generate or verify immutable, checked-in contract-port provenance."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "contracts" / "ported-tests.json"
PROVENANCE_PATH = ROOT / "contracts" / "contract-port-provenance.json"
SURFACE_PATH = ROOT / "contracts" / "public-surface-fixtures.json"
LEDGER_PATH = ROOT / "contracts" / "compatibility-ledger.json"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _test_nodes(path: Path, suite: str) -> dict[str, str]:
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    nodes = {}
    def node_digest(node):
        starts = [node.lineno, *(decorator.lineno for decorator in node.decorator_list)]
        return _digest("".join(lines[min(starts) - 1 : node.end_lineno]).encode())

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            key = f"{suite}::{node.name}"
            nodes[key] = node_digest(node)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                    key = f"{suite}::{node.name}::{child.name}"
                    nodes[key] = node_digest(child)
    return nodes


def _artifact() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text())
    selected = {
        origin: {case["source_test"] for case in manifest["cases"] if case["origin"] == origin}
        for origin in manifest["sources"]
    }
    ports = {}
    files = {MANIFEST_PATH, SURFACE_PATH, LEDGER_PATH}
    for origin, source in manifest["sources"].items():
        ports[origin] = {}
        discovered = set()
        for suite, paths in source["ports"].items():
            source_path = ROOT / paths["source"]
            adapted_path = ROOT / paths["adapted"]
            files.update((source_path, adapted_path))
            source_nodes = _test_nodes(source_path, suite)
            adapted_nodes = _test_nodes(adapted_path, suite)
            required = selected[origin] & source_nodes.keys()
            assert required == selected[origin] & adapted_nodes.keys()
            discovered.update(required)
            ports[origin][suite] = {
                "selected_nodes": {name: source_nodes[name] for name in sorted(required)},
                "adapted_nodes": {name: adapted_nodes[name] for name in sorted(required)},
                "source_unselected": sorted(source_nodes.keys() - required),
                "declared_exclusions": source["excluded"],
            }
        assert discovered == selected[origin]
    return {
        "schema_version": 1,
        "files": {
            str(path.relative_to(ROOT)): _digest(path.read_bytes()) for path in sorted(files)
        },
        "ports": ports,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(_artifact(), indent=2, sort_keys=True) + "\n"
    if args.write:
        PROVENANCE_PATH.write_text(rendered)
        return 0
    if not PROVENANCE_PATH.exists() or PROVENANCE_PATH.read_text() != rendered:
        raise SystemExit(
            "contract provenance is stale; review the baseline/port change, then run "
            "`python scripts/check_contract_port_provenance.py --write`"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
