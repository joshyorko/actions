# Copyright 2022-2026 Robocorp and contributors.
# Licensed under the Apache License, Version 2.0.
"""Contract-port policy checks; executable assertions live in contract_ports."""

import ast
from pathlib import Path

PORTS = Path(__file__).resolve().parent / "contract_ports"


def test_expected_red_ports_execute_production_behavior():
    for path in PORTS.glob("test_*.py"):
        tree = ast.parse(path.read_text())
        calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        assert not any(
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "pytest"
            and node.func.attr == "fail"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        )
        assert calls & {"reserve_input", "load_payload", "create", "email", "add_file", "seed_input"}
