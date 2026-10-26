import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def checker():
    path = (
        Path(__file__).parents[2]
        / "action_server/scripts/qualify_consumer_inventory_327.py"
    )
    spec = importlib.util.spec_from_file_location("consumer_inventory_327", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evidence():
    return {
        "environment": {},
        "installed": [
            {
                "metadata": {
                    "name": "actions-runtime",
                    "version": "1.1.0a38",
                    "provides_extra": ["data"],
                    "requires_dist": ['provider[adapter]>=1; extra == "data"'],
                }
            },
            {
                "metadata": {
                    "name": "provider",
                    "version": "1",
                    "requires_dist": ['adapter==2; extra == "adapter"'],
                }
            },
            {"metadata": {"name": "adapter", "version": "2"}},
            {"metadata": {"name": "pip", "version": "25"}},
        ],
    }, {
        "package": [
            {"name": "provider", "version": "1"},
            {"name": "adapter", "version": "2"},
        ]
    }


def test_selected_optional_dependency_closure(checker):
    installed, lock = evidence()
    result = checker.qualify(installed, lock, "1.1.0a38", ["data"])
    assert result["dependencies"]["provider"] == ["adapter"]
    assert result["selected_extras"]["provider"] == ["adapter"]
    with pytest.raises(ValueError, match="outside selected"):
        checker.qualify(installed, lock, "1.1.0a38", [])
    with pytest.raises(ValueError, match="undeclared"):
        checker.qualify(installed, lock, "1.1.0a38", ["missing-provider"])


@pytest.mark.parametrize("mutation", ["missing", "unlocked", "duplicate"])
def test_resolved_inventory_failures(checker, mutation):
    installed, lock = evidence()
    if mutation == "missing":
        installed["installed"].pop(2)
    elif mutation == "unlocked":
        installed["installed"][2]["metadata"]["version"] = "3"
    else:
        installed["installed"].append(installed["installed"][1])
    with pytest.raises(ValueError):
        checker.qualify(installed, lock, "1.1.0a38", ["data"])


@pytest.mark.parametrize("mutation", [None, "missing", "stale", "duplicate"])
def test_cyclonedx_components_must_match_actual_consumer(checker, mutation):
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": [{"name": "example", "version": "1"}],
    }
    if mutation == "missing":
        sbom["components"] = []
    elif mutation == "stale":
        sbom["components"][0]["version"] = "0"
    elif mutation == "duplicate":
        sbom["components"].append(dict(sbom["components"][0]))
    if mutation is None:
        checker.compare_cyclonedx(sbom, {"example": "1"})
    else:
        with pytest.raises(ValueError):
            checker.compare_cyclonedx(sbom, {"example": "1"})


@pytest.mark.parametrize("vendor", ["Sema4AI_HTTP_Helper", "sema4ai.common"])
@pytest.mark.parametrize("location", ["installed", "inactive_dependency"])
def test_replaced_vendor_packages_cannot_return(checker, vendor, location):
    installed, lock = evidence()
    if location == "installed":
        installed["installed"].append({"metadata": {"name": vendor, "version": "1"}})
        lock["package"].append({"name": vendor, "version": "1"})
    else:
        installed["installed"][0]["metadata"]["requires_dist"].append(
            f'{vendor}>=1; extra == "not-selected"'
        )
    with pytest.raises(ValueError, match="replaced vendor"):
        checker.qualify(installed, lock, "1.1.0a38", ["data"])
