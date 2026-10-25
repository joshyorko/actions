"""Compare pip's resolved consumer evidence with locks and existing CycloneDX.

This is a qualification reader, not a Python SBOM generator or release writer.
Run through the prepared Poetry toolchain, where packaging is already available.
"""

import argparse
import json
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

REPLACED_VENDOR_DISTRIBUTIONS = {"sema4ai-http-helper", "sema4ai-common"}


def qualify(inspect, lock, expected_runtime, extras):
    installed = {}
    for item in inspect["installed"]:
        metadata = item["metadata"]
        name = canonicalize_name(metadata["name"])
        if name in REPLACED_VENDOR_DISTRIBUTIONS:
            raise ValueError(f"replaced vendor distribution installed: {name}")
        for raw in metadata.get("requires_dist", []):
            dependency = canonicalize_name(Requirement(raw).name)
            if dependency in REPLACED_VENDOR_DISTRIBUTIONS:
                raise ValueError(
                    f"replaced vendor dependency declared: {name} -> {dependency}"
                )
        if name in installed:
            raise ValueError("duplicate installed distribution")
        installed[name] = metadata
    locked = {}
    for package in lock["package"]:
        locked.setdefault(canonicalize_name(package["name"]), set()).add(
            package["version"]
        )
    if installed["actions-runtime"]["version"] != expected_runtime:
        raise ValueError("candidate identity mismatch")
    if set(extras) - set(installed["actions-runtime"].get("provides_extra", [])):
        raise ValueError("undeclared candidate extra")
    for name, metadata in installed.items():
        if name not in {"pip", "actions-runtime"} and metadata[
            "version"
        ] not in locked.get(name, set()):
            raise ValueError(f"installed version outside lock: {name}")
    selected = {"actions-runtime": {"", *extras}}
    pending = ["actions-runtime"]
    graph = {}
    while pending:
        name = pending.pop()
        metadata = installed[name]
        graph.setdefault(name, set())
        for value in metadata.get("requires_dist", []):
            requirement = Requirement(value)
            if requirement.marker and not any(
                requirement.marker.evaluate({**inspect["environment"], "extra": extra})
                for extra in selected[name]
            ):
                continue
            dependency = canonicalize_name(requirement.name)
            if dependency not in installed or not requirement.specifier.contains(
                installed[dependency]["version"], prereleases=True
            ):
                raise ValueError(f"unresolved dependency: {name} -> {value}")
            graph[name].add(dependency)
            requested = {"", *requirement.extras}
            if dependency not in selected or not requested <= selected[dependency]:
                selected.setdefault(dependency, set()).update(requested)
                pending.append(dependency)
    if set(installed) - {"pip"} != set(selected):
        raise ValueError(
            "consumer contains distributions outside selected dependency graph"
        )
    return {
        "resolved": {name: installed[name]["version"] for name in sorted(selected)},
        "dependencies": {
            name: sorted(values) for name, values in sorted(graph.items())
        },
        "selected_extras": {
            name: sorted(values - {""})
            for name, values in sorted(selected.items())
            if values - {""}
        },
        "bootstrap_excluded": ["pip"] if "pip" in installed else [],
    }


def compare_cyclonedx(sbom, resolved):
    if sbom.get("bomFormat") != "CycloneDX" or not sbom.get("specVersion"):
        raise ValueError("not the supported CycloneDX format")
    components = {}
    for item in sbom.get("components", []):
        name = canonicalize_name(item["name"])
        if name in components:
            raise ValueError("duplicate CycloneDX component")
        components[name] = item.get("version")
    # pip is explicitly bootstrap tooling, not the Runtime dependency graph.
    components.pop("pip", None)
    if components != resolved:
        raise ValueError("CycloneDX components do not match resolved consumer")


def compare_cyclonedx_graph(sbom, qualification):
    """Require explicit package graph nodes and exact active dependency edges."""
    compare_cyclonedx(sbom, qualification["resolved"])
    references = {}
    for component in sbom["components"]:
        reference = component.get("bom-ref")
        if not isinstance(reference, str) or not reference or reference in references:
            raise ValueError("missing or duplicate component reference")
        references[reference] = canonicalize_name(component["name"])
    root = sbom.get("metadata", {}).get("component", {}).get("bom-ref")
    if root in references:
        raise ValueError("duplicate root/component reference")
    known = set(references) | ({root} if root else set())
    nodes = {}
    for node in sbom.get("dependencies", []):
        reference = node["ref"]
        dependencies = node.get("dependsOn", [])
        if reference not in known or reference in nodes:
            raise ValueError("unknown or duplicate dependency node")
        if (
            len(set(dependencies)) != len(dependencies)
            or not set(dependencies) <= known
        ):
            raise ValueError("duplicate or dangling dependency edge")
        nodes[reference] = dependencies
    observed = {}
    for reference, name in references.items():
        if name == "pip":
            continue
        if reference not in nodes:
            raise ValueError("missing explicit dependency node")
        if any(target == root for target in nodes[reference]):
            raise ValueError("package dependency points to application root")
        observed[name] = sorted(references[target] for target in nodes[reference])
    if observed != qualification["dependencies"]:
        raise ValueError("CycloneDX graph differs from active resolved dependencies")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--expected-runtime", required=True)
    parser.add_argument("--extra", action="append", default=[])
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = qualify(
        json.loads(args.inspect.read_text()),
        tomllib.loads(args.lock.read_text()),
        args.expected_runtime,
        args.extra,
    )
    try:
        compare_cyclonedx_graph(json.loads(args.sbom.read_text()), result)
        result[
            "sbom_comparison"
        ] = "component inventory and active dependency graph match"
    except ValueError as error:
        result["sbom_comparison"] = "rejected: " + str(error)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    if result["sbom_comparison"].startswith("rejected:"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
