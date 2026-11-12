"""Independent declaration projection evidence; never a release admission gate."""

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from qualify_consumer_inventory_327 import compare_cyclonedx


def explain_declaration_graph(sbom, inspection, qualification):
    """Verify pinned environment-export semantics and explain inactive edges.

    The caller supplies the separately qualified selected-profile graph. Raw BOM
    and inspection are read only. A successful return is not active-graph parity.
    """
    compare_cyclonedx(sbom, qualification["resolved"])
    installed = {}
    for item in inspection["installed"]:
        metadata = item["metadata"]
        name = canonicalize_name(metadata["name"])
        if name in installed:
            raise ValueError("duplicate installed distribution")
        installed[name] = metadata
    refs = {}
    names = set()
    for component in sbom["components"]:
        ref = component.get("bom-ref")
        name = canonicalize_name(component["name"])
        if not isinstance(ref, str) or not ref or ref in refs or name in names:
            raise ValueError("duplicate or missing component reference/name")
        if name not in installed or installed[name]["version"] != component["version"]:
            raise ValueError("component differs from inspected installation")
        refs[ref] = name
        names.add(name)
    if names != set(installed):
        raise ValueError("component inventory differs from installation")
    observed = {}
    for node in sbom["dependencies"]:
        ref = node["ref"]
        targets = node.get("dependsOn", [])
        if ref not in refs or refs[ref] in observed:
            raise ValueError("unknown or duplicate dependency node")
        if len(set(targets)) != len(targets) or not set(targets) <= set(refs):
            raise ValueError("duplicate or dangling edge")
        observed[refs[ref]] = {refs[target] for target in targets}
    expected = {}
    requirements = {}
    for name, metadata in installed.items():
        expected[name] = set()
        for raw in metadata.get("requires_dist", []):
            requirement = Requirement(raw)
            target = canonicalize_name(requirement.name)
            if target in installed and target != name:
                expected[name].add(target)
                requirements.setdefault((name, target), []).append((raw, requirement))
    if observed != expected:
        raise ValueError("raw graph differs from installed declaration projection")
    differences = []
    for name, active in qualification["dependencies"].items():
        if not set(active) <= observed[name]:
            raise ValueError("active edge absent from raw graph")
        for target in sorted(observed[name] - set(active)):
            explanations = []
            for raw, requirement in requirements[name, target]:
                selected = ["", *qualification["selected_extras"].get(name, [])]
                if requirement.marker is None or any(
                    requirement.marker.evaluate(
                        {**inspection["environment"], "extra": extra}
                    )
                    for extra in selected
                ):
                    raise ValueError("unexplained difference: active requirement")
                explanations.append(
                    {
                        "requires_dist": raw,
                        "marker_active": False,
                        "installed_version_satisfies_specifier": requirement.specifier.contains(
                            installed[target]["version"], prereleases=True
                        ),
                    }
                )
            differences.append(
                {
                    "source": name,
                    "target": target,
                    "installed_version": installed[target]["version"],
                    "source_selected_extras": qualification["selected_extras"].get(
                        name, []
                    ),
                    "requirements": explanations,
                }
            )
    return {
        "scope": "declaration projection and difference explanation only",
        "release_admission": "not evaluated",
        "active_graph_equal": not differences,
        "declaration_nodes": len(observed),
        "differences": differences,
    }
