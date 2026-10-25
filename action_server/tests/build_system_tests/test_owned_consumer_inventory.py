"""Reject replaced distributions even when metadata resolution would otherwise pass."""
import importlib.util
from pathlib import Path

import pytest


def reader():
    path = Path(__file__).parents[2] / "scripts/qualify_consumer_inventory_327.py"
    spec = importlib.util.spec_from_file_location("consumer_inventory", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "vendor",
    ["robocorp-log", "robocorp-truststore", "sema4ai-common", "sema4ai-http-helper"],
)
@pytest.mark.parametrize("kind", ["installed", "declared"])
def test_replaced_vendor_graph_rejected(vendor, kind):
    metadata = (
        {"name": vendor, "version": "1.0"}
        if kind == "installed"
        else {
            "name": "actions-core",
            "version": "1.1.0a6",
            "requires_dist": [vendor + ">=0"],
        }
    )
    with pytest.raises(ValueError, match="replaced vendor"):
        reader().qualify({"installed": [{"metadata": metadata}]}, {}, "1.1.0a43", [])


def test_official_native_trust_graph_is_accepted():
    installed = [
        {
            "metadata": {
                "name": "actions-runtime",
                "version": "1.1.0a43",
                "requires_dist": ["truststore>=0.10,<1"],
            }
        },
        {"metadata": {"name": "truststore", "version": "0.10.4"}},
    ]
    result = reader().qualify(
        {"installed": installed, "environment": {}},
        {"package": [{"name": "truststore", "version": "0.10.4"}]},
        "1.1.0a43",
        [],
    )
    assert result["dependencies"]["actions-runtime"] == ["truststore"]
