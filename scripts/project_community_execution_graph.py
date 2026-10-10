"""Validate and render the active community execution-graph projection.

The issue ledger remains the source for retained contracts and raw states. The
operational graph carries typed, non-interchangeable relationships and is the
only input to execution-DAG validation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "docs" / "program"
GRAPH_PATH = PROGRAM / "community-execution-graph.json"
LEDGER_PATH = PROGRAM / "community-program-ledger.json"
MARKDOWN_PATH = PROGRAM / "community-execution-graph.md"
RESUME_PATH = PROGRAM / "community-resume-20261009.json"
LEDGER_MARKDOWN_PATH = PROGRAM / "community-program-ledger.md"
HANDOFF_PATH = PROGRAM / "engineering-handoff.md"

AMENDMENT_NOTE = (
    "Canvas graph amendment (2026-10-09): execution prerequisites remain separate from scoped slice/criterion gates, "
    "parent coordination, related product direction and full-acceptance aggregation. #127 consumes accepted template slices "
    "and relevant #125/#98 criteria, not whole #71/#93/#101 closure. At the 2026-10-09T21:02Z snapshot, #99-A's current "
    "renderer head is c971ccec; the six component tests, TypeScript and schema PASS were reported at its prior 842c32d5 head, "
    "while production main/bridge/browser remain NOT_RUN. #100-A PR263 has accepted source review, with broader configured "
    "Cloud gates blocked; E is beginning #100-B's Python roundtrip on F's shared fixture. #126 PR265 generator repair has "
    "49 focused and four template tests reported PASS locally; clean-wheel is NOT_RUN and hosted checks are pending. "
    "Common #83 Run/Attempt, #129 Workspace Deployment/authorization, #130 Package Revision/capability and #135 compiler "
    "criteria were unaccepted at the 2026-10-09T21:02Z snapshot. The 2026-10-10T05:01Z supplement accepts only the named "
    "#129 deployment-reference-envelope criterion for bounded #130 schema/fixture work; full #129 production acceptance "
    "remains open. Integration is 446ff1b3; PR254 is a docs-only merge and does not complete #100. See "
    "evidence/current-worker-inventory-20261009T2102Z.json and "
    "evidence/canvas-common-api-authorization-seams-20261009.md. Historical untyped edges remain audit provenance; "
    "all 54 retained issue contracts and raw states are unchanged."
)


def _is_canvas_parent_or_child_edge(source: int, target: int) -> str | None:
    """Classify known Canvas parent/aggregation/product links from owner steering."""
    if source == 93 and target == 101:
        return "coordination"
    if source == 127 and target in {93, 101}:
        return "coordination"
    if source == 127 and target == 71:
        return "related"
    if source == 71 and target == 127:
        return "aggregation"
    if source == 93 and target in {96, 97, 98, 99, 100, 126, 127, 208}:
        return "aggregation"
    if source == 93 and target == 209:
        return "related"
    return None


def apply_named_scoped_criteria(graph: dict, ledger: dict) -> dict:
    """Apply owner-accepted criterion gates without promoting whole issues."""
    amendments = ledger.get("supplemental_program_amendments", [])
    for amendment in amendments:
        graph.setdefault("current_active_workers", {}).update(amendment.get("current_active_workers", {}))
        if amendment.get("worker_stage_snapshot"):
            graph["worker_stage_snapshot"] = amendment["worker_stage_snapshot"]
        for decision in amendment.get("accepted_scoped_criteria", []):
            model = graph["relationship_model"]
            issue = decision["owner_issue"]
            consumer_slice = decision["consumer_slice"]
            criterion_id = decision["criterion_id"]
            issue_row = next(row for row in graph["issues"] if row["issue"] == decision["consumer_issue"])
            issue_row["unresolved_open_issue_dependencies"] = [
                dependency for dependency in issue_row["unresolved_open_issue_dependencies"]
                if dependency not in decision.get("superseded_issue_level_prerequisites", [])
            ]
            model["execution_prerequisites"] = [
                edge for edge in model["execution_prerequisites"]
                if not (
                    edge["consumer"] == decision["consumer_issue"]
                    and edge["prerequisite"] in decision.get("superseded_issue_level_prerequisites", [])
                )
            ]
            criterion = {
                "id": criterion_id,
                "owner_issue": issue,
                "description": decision["description"],
                "status": decision["status"],
                "evidence_basis": decision["decision"],
            }
            model["criteria"] = [item for item in model["criteria"] if item["id"] != criterion_id]
            model["criteria"].append(criterion)
            slice_row = {
                "id": consumer_slice,
                "issue": decision["consumer_issue"],
                "description": decision["consumer_slice_description"],
                "status": decision["consumer_slice_status"],
            }
            model["execution_slices"] = [item for item in model["execution_slices"] if item["id"] != consumer_slice]
            model["execution_slices"].append(slice_row)
            gate = {
                "prerequisite": criterion_id,
                "consumer_slice": consumer_slice,
                "scope": decision["gate_scope"],
            }
            model["scoped_execution_gates"] = [
                edge for edge in model["scoped_execution_gates"]
                if not (edge["prerequisite"] == criterion_id and edge["consumer_slice"] == consumer_slice)
            ]
            model["scoped_execution_gates"].append(gate)
            issue_row["reason"] = decision["consumer_issue_reason"]
            issue_row["next_bounded_action"] = decision["consumer_issue_next_action"]
            if decision.get("consumer_issue_classification"):
                issue_row["classification"] = decision["consumer_issue_classification"]
    graph["counts"] = {
        stage: sum(row["classification"] == stage for row in graph["issues"])
        for stage in ["READY", "ACTIVE", "REVIEW", "BLOCKED", "INTEGRATED", "COMPLETE"]
    }
    return graph


def apply_active_substages(graph: dict, ledger: dict) -> dict:
    """Project latest bounded work without changing retained issue stages."""
    amendments = ledger.get("supplemental_program_amendments", [])
    latest = amendments[-1] if amendments else {}
    graph["active_substages"] = copy.deepcopy(latest.get("active_substages", []))
    graph["active_substages_observed_at_utc"] = latest.get("observed_at_utc") if graph["active_substages"] else None
    return graph


def upgrade_relationships(graph: dict, ledger: dict) -> dict:
    """Migrate one legacy projection; schema-v2 data is authoritative thereafter."""
    if graph.get("relationship_schema_version") == 2 and graph.get("relationship_amendment") == "canvas-execution-graph-20261009-v4":
        graph = apply_named_scoped_criteria(graph, ledger)
        graph = apply_active_substages(graph, ledger)
        validate_graph(graph, ledger)
        return graph
    if graph.get("relationship_schema_version") == 2 and graph.get("relationship_amendment") not in (None, "canvas-execution-graph-20261009-v1", "canvas-execution-graph-20261009-v2", "canvas-execution-graph-20261009-v3"):
        raise ValueError(f"Unsupported typed graph amendment: {graph['relationship_amendment']}")
    if graph.get("relationship_schema_version") == 2:
        graph = copy.deepcopy(graph)
        graph.pop("relationship_schema_version", None)
        graph.pop("relationship_amendment", None)
        graph.pop("relationship_model", None)
        for row in graph["issues"]:
            row["unresolved_open_issue_dependencies"] = row.get("prior_untyped_dependency_projection", [])
            row.pop("prior_untyped_dependency_projection", None)
            for field in ("coordination_parents", "related_product_direction", "full_acceptance_aggregation"):
                row.pop(field, None)
    ledger_issues = {item["issue"]: item for item in ledger["issues"]}
    rows = {item["issue"]: item for item in graph["issues"]}
    if len(rows) != 54 or set(rows) != set(ledger_issues):
        raise ValueError("Graph projection must preserve exactly the 54 ledger issues")

    prior_edges: list[dict] = []
    execution_edges: list[dict] = []
    coordination_edges: list[dict] = []
    related_edges: list[dict] = []
    aggregation_edges: list[dict] = []

    for issue, row in rows.items():
        old = list(row.get("prior_untyped_dependency_projection", row.get("unresolved_open_issue_dependencies", [])))
        row["prior_untyped_dependency_projection"] = old
        row["unresolved_open_issue_dependencies"] = []
        row["coordination_parents"] = []
        row["related_product_direction"] = []
        row["full_acceptance_aggregation"] = []
        for dependency in old:
            prior_edges.append({"prerequisite": dependency, "consumer": issue})
            disposition = _is_canvas_parent_or_child_edge(issue, dependency)
            if disposition == "coordination":
                coordination_edges.append({"parent_or_coordinator": dependency, "child_or_scope": issue})
                row["coordination_parents"].append(dependency)
            elif disposition == "related":
                related_edges.append({"issue": issue, "related_issue": dependency, "basis": "product direction; nonblocking"})
                row["related_product_direction"].append(dependency)
            elif disposition == "aggregation":
                aggregation_edges.append({"child": dependency, "parent": issue, "basis": "full acceptance aggregation; not an execution prerequisite"})
                row["full_acceptance_aggregation"].append(dependency)
            else:
                row["unresolved_open_issue_dependencies"].append(dependency)
                execution_edges.append({"prerequisite": dependency, "consumer": issue, "scope": "current projected contract gate"})

    # Preserve the historical issue-level dependency field's meaning in the
    # retained ledger. Add the newly approved criterion slices separately.
    rows[71]["unresolved_open_issue_dependencies"] = []
    execution_edges = [edge for edge in execution_edges if edge["consumer"] != 71]

    # These contracts consume bounded criteria, not completion of the entire
    # upstream issue. Preserve the historical edges below for audit, while
    # recording the active prerequisite in the slice DAG.
    for consumer, prerequisites in {71: {83, 99, 100, 129, 130, 135}, 99: {97, 98}, 126: {125}, 127: {99, 100}, 130: {129}}.items():
        rows[consumer]["unresolved_open_issue_dependencies"] = [
            issue for issue in rows[consumer]["unresolved_open_issue_dependencies"]
            if issue not in prerequisites
        ]
        execution_edges = [
            edge for edge in execution_edges
            if not (edge["consumer"] == consumer and edge["prerequisite"] in prerequisites)
        ]

    # Parent and related links are not blockers for execution. Use the latest
    # owner-authored Canvas amendment, while retaining the full acceptance
    # relationships as a separate projection.
    coordination_edges.extend([
        {"parent_or_coordinator": 101, "child_or_scope": 93},
        {"parent_or_coordinator": 93, "child_or_scope": 99},
        {"parent_or_coordinator": 93, "child_or_scope": 100},
        {"parent_or_coordinator": 93, "child_or_scope": 126},
        {"parent_or_coordinator": 93, "child_or_scope": 127},
        {"parent_or_coordinator": 101, "child_or_scope": 126},
        {"parent_or_coordinator": 101, "child_or_scope": 127},
    ])
    for issue, parent in [(93, 101), (99, 93), (100, 93), (126, 93), (127, 93), (126, 101), (127, 101)]:
        if parent not in rows[issue]["coordination_parents"]:
            rows[issue]["coordination_parents"].append(parent)

    for issue, related in {
        71: [93],
        99: [71],
        100: [71, 99],
        126: [71, 99, 100, 127],
        127: [71],
    }.items():
        for target in related:
            if target not in rows[issue]["related_product_direction"]:
                rows[issue]["related_product_direction"].append(target)
                related_edges.append({"issue": issue, "related_issue": target, "basis": "current owner-authored Canvas amendment; nonblocking"})

    # These scoped gates are distinct from whole-issue completion. A template
    # can follow the small accepted authoring/rendering slices; it never waits
    # for the foundry or either umbrella to close.
    slices = [
        {"id": "100-A", "issue": 100, "description": "Public tool UI metadata and ui:// resource authoring/serving", "status": "ACTIVE"},
        {"id": "100-B", "issue": 100, "description": "Versioned CanvasSpec interchange and Python/JSON/TypeScript fixture", "status": "PROPOSED_REVIEW_ONLY"},
        {"id": "99-A", "issue": 99, "description": "Portable MCP App View renderer/resource bridge using the agreed fixture", "status": "NOT_IMPLEMENTED"},
        {"id": "99-B", "issue": 99, "description": "Optional host-specific ChatGPT projection and actual-host proof", "status": "NOT_IMPLEMENTED"},
        {"id": "127-template", "issue": 127, "description": "Packaged template round trip over accepted authoring and renderer slices", "status": "NOT_IMPLEMENTED"},
        {"id": "126-template", "issue": 126, "description": "Relevant public-package/template boundary slice consumed by the SDK and template contract", "status": "NOT_IMPLEMENTED"},
        {"id": "126-source-protocol", "issue": 126, "description": "Bounded source-protocol proof; not SDK/template acceptance", "status": "ACTIVE"},
        {"id": "71-local", "issue": 71, "description": "Local generated application vertical on common Package/Deployment/Run/compiler services", "status": "NOT_IMPLEMENTED"},
        {"id": "71-host", "issue": 71, "description": "Optional host/distribution acceptance after portable product behavior", "status": "NOT_IMPLEMENTED"},
        {"id": "130-schema", "issue": 130, "description": "Bounded immutable Package Revision schema and deterministic fixtures", "status": "READY_FOR_BOUNDED_SCHEMA_FIXTURE; assigned to DevsySol; no production/full #130 acceptance"},
    ]
    criteria = [
        {"id": "125:public-package-boundary", "owner_issue": 125, "description": "Relevant public package and MCP resource boundary", "status": "PARTIAL_NOT_ACCEPTED", "evidence_basis": "Graph stage INTEGRATED; retained state IMPLEMENTED_UNVERIFIED; PR128 foundation merged but full #125 acceptance remains open."},
        {"id": "97:ui-foundation", "owner_issue": 97, "description": "Consumed UI, offline and CSP foundation criteria", "status": "PARTIAL_NOT_ACCEPTED", "evidence_basis": "Graph stage INTEGRATED; retained state IMPLEMENTED_UNVERIFIED; PR119 foundation merged and acceptance gates remain open."},
        {"id": "98:canvas-artifact", "owner_issue": 98, "description": "Consumed Canvas artifact, manifest and build criteria", "status": "PARTIAL_NOT_ACCEPTED", "evidence_basis": "Graph stage INTEGRATED; retained state IMPLEMENTED_UNVERIFIED; PR115 foundation merged and acceptance gates remain open."},
        {"id": "83:run-attempt-authority", "owner_issue": 83, "description": "Minimum local Run/Attempt ownership and lifecycle semantics", "status": "NOT_IMPLEMENTED", "evidence_basis": "Graph stage BLOCKED; retained state NOT_STARTED; no accepted Run/Attempt implementation recorded."},
        {"id": "129:deployment-binding", "owner_issue": 129, "description": "Minimum local Deployment identity and bindings", "status": "PARTIAL_NOT_ACCEPTED", "evidence_basis": "Graph stage INTEGRATED; retained state IMPLEMENTED_UNVERIFIED; PR250 contains a design-only probe, not production Deployment acceptance."},
        {"id": "129:deployment-reference-envelope", "owner_issue": 129, "description": "Interface prerequisite for #130 schema work: full Workspace/Package/immutable revision references; package-scoped RuntimePlanRef digest plus schema/compatibility identity; logical binding references separated from deployed values; explicit declared-plan selection with no fallback; Run/retry pinning remains owned by #83.", "status": "ACCEPTED_FOR_130_SCHEMA_ONLY", "evidence_basis": "Root architecture decision 2026-10-10, based on live #129/#130 bodies, merged PR250 design/probe, and independent contract review; does not approve the paused full #129 packet or production acceptance. See evidence/pr129-pr130-contract-review-20261010T0455Z.md."},
        {"id": "130:package-revision", "owner_issue": 130, "description": "Immutable generated Package Revision contract", "status": "NOT_IMPLEMENTED", "evidence_basis": "Graph stage BLOCKED; retained state NOT_STARTED; no accepted Package Revision implementation recorded."},
        {"id": "135:compiler", "owner_issue": 135, "description": "Minimum package-to-revision/compiler contract", "status": "NOT_IMPLEMENTED", "evidence_basis": "Graph stage BLOCKED; retained state NOT_STARTED; no accepted compiler implementation recorded."},
        {"id": "91:authorization-boundary", "owner_issue": 91, "description": "Host-mode authorization boundary when protected/share functionality is exposed", "status": "PARTIAL_NOT_ACCEPTED", "evidence_basis": "Graph stage INTEGRATED; retained state NOT_STARTED; PR250 is a bounded SDK/auth foundation, while public authorization remains open."},
        {"id": "214:public-edge-boundary", "owner_issue": 214, "description": "Remote/share acceptance boundary, not local fixture proof", "status": "PARTIAL_NOT_ACCEPTED", "evidence_basis": "Graph stage REVIEW; retained state IN_PROGRESS; live provider/TLS and standalone lifecycle gates remain open."},
    ]
    slice_gates = [
        {"prerequisite": "125:public-package-boundary", "consumer_slice": "100-A", "scope": "Only the relevant public package/MCP resource criteria; not all of #125"},
        {"prerequisite": "97:ui-foundation", "consumer_slice": "99-A", "scope": "Consumed UI system and offline/CSP foundation criteria"},
        {"prerequisite": "98:canvas-artifact", "consumer_slice": "99-A", "scope": "Separate Canvas artifact and build/manifest criteria"},
        {"prerequisite": "100-A", "consumer_slice": "127-template", "scope": "Accepted public authoring fixture"},
        {"prerequisite": "100-B", "consumer_slice": "127-template", "scope": "Accepted serialization fixture only if template consumes CanvasSpec"},
        {"prerequisite": "99-A", "consumer_slice": "127-template", "scope": "Accepted renderer/resource/bridge slice"},
        {"prerequisite": "125:public-package-boundary", "consumer_slice": "127-template", "scope": "Relevant public-package/template checks only"},
        {"prerequisite": "125:public-package-boundary", "consumer_slice": "126-template", "scope": "Only the relevant public package/template boundary criteria; not all of #125"},
        {"prerequisite": "98:canvas-artifact", "consumer_slice": "127-template", "scope": "Relevant Canvas artifact pipeline checks only"},
        {"prerequisite": "100-A", "consumer_slice": "71-local", "scope": "Accepted public authoring boundary"},
        {"prerequisite": "100-B", "consumer_slice": "71-local", "scope": "Accepted shared schema only if generated spec uses it"},
        {"prerequisite": "99-A", "consumer_slice": "71-local", "scope": "Accepted portable View/renderer boundary"},
        {"prerequisite": "83:run-attempt-authority", "consumer_slice": "71-local", "scope": "Minimum local Run/Attempt semantics"},
        {"prerequisite": "129:deployment-binding", "consumer_slice": "71-local", "scope": "Minimum local Deployment identity/bindings"},
        {"prerequisite": "130:package-revision", "consumer_slice": "71-local", "scope": "Immutable generated Package Revision contract"},
        {"prerequisite": "135:compiler", "consumer_slice": "71-local", "scope": "Minimum package-to-revision/compiler contract"},
        {"prerequisite": "71-local", "consumer_slice": "71-host", "scope": "Host integration consumes a working portable local vertical"},
        {"prerequisite": "91:authorization-boundary", "consumer_slice": "71-host", "scope": "Only if host mode exposes protected/share functionality"},
        {"prerequisite": "214:public-edge-boundary", "consumer_slice": "71-host", "scope": "Only for remote/share acceptance, not local fixture proof"},
        {"prerequisite": "129:deployment-reference-envelope", "consumer_slice": "130-schema", "scope": "Accepted interface prerequisite only for bounded #130 schema/fixture work; no full #129 API, migration, production, Run/Attempt storage, or #143 dynamic-adapter admission acceptance."},
    ]
    related_edges.extend([
        {"issue": 93, "related_issue": 71, "basis": "product ownership; not a child execution prerequisite"},
        {"issue": 126, "related_issue": 127, "basis": "separate optional template/example; nonblocking"},
    ])
    rows[93]["related_product_direction"].append(71)
    aggregation_edges.extend([
        {"child": 127, "parent": 71, "basis": "full #71 product acceptance; does not block the earlier local #71 slice"},
        *[
            {"child": child, "parent": 93, "basis": "#93 child acceptance aggregation; does not block child execution"}
            for child in [96, 97, 98, 99, 100, 126, 127, 208]
        ],
        {"child": 93, "parent": 101, "basis": "program/factory aggregation; parent is coordination, not prerequisite"},
    ])
    related_edges = [edge for edge in related_edges if (edge["issue"], edge["related_issue"]) != (93, 209)]
    related_edges.append({"issue": 93, "related_issue": 209, "basis": "CI/reconnect relationship; not a #93 child acceptance prerequisite"})
    rows[93]["related_product_direction"].append(209)
    for edge in aggregation_edges:
        rows[edge["parent"]]["full_acceptance_aggregation"].append(edge["child"])

    # The scoped #125 criterion is recorded on the 100-A slice, not copied into
    # the whole #100 issue's prerequisite list. Likewise, shared fixtures allow
    # #99-A and #100-B to progress without whole-issue mutual blocking.
    for row in rows.values():
        for key in ("unresolved_open_issue_dependencies", "coordination_parents", "related_product_direction", "full_acceptance_aggregation"):
            row[key] = sorted(set(row[key]))

    rows[71]["reason"] = "The local Canvas vertical gates on named #83/#129/#130/#135 criteria plus accepted #99-A/#100-A/#100-B slices; it does not wait for whole Canvas issue closure. #127 contributes to full acceptance only."
    rows[99]["reason"] = "#99-A consumes the relevant #97 UI foundation and #98 Canvas artifact criteria; optional host-specific work remains separate in #99-B."
    rows[99]["next_bounded_action"] = "Implement the portable Canvas renderer/resource bridge against the agreed fixture after its consumed #97/#98 criteria are accepted; do not wait for unrelated whole-issue closure."
    rows[126]["classification"] = "ACTIVE"
    rows[126]["reason"] = "A bounded #126 source-protocol proof is active; this is not template/SDK acceptance. The full contract still consumes only relevant #125 criteria, with parent coordination and optional Canvas references nonblocking."
    rows[126]["next_bounded_action"] = "Complete the bounded source-protocol proof on its exact branch and report its limits; keep full SDK/template acceptance and #125's remaining contract open."
    rows[100]["classification"] = "ACTIVE"
    rows[100]["reason"] = "The public authoring 100-A implementation slice is active. PR254 remains an open review-only ADR proposal and is not integrated into the revised scope; the separate 100-B schema slice remains proposal-only."
    rows[100]["next_bounded_action"] = "Continue the isolated 100-A public authoring slice while preserving PR254 as review-only; do not infer 100-B or whole #100 acceptance."
    rows[127]["reason"] = "#127-template consumes accepted #100-A/#100-B/#99-A slices and only relevant #125/#98 criteria. #71 is product direction and full-acceptance aggregation; #93/#101 are coordination, not execution prerequisites."
    rows[127]["next_bounded_action"] = "Build the packaged Canvas template when its scoped authoring, renderer, public-package and artifact gates pass; it does not wait for #71, #93 or #101 to close."
    rows[130]["reason"] = "The named #129 deployment-reference-envelope criterion is accepted only as an interface prerequisite for the bounded 130-schema slice. Full #129 production and full #130 acceptance remain open; #135/#136 implementation order is unchanged."
    rows[130]["next_bounded_action"] = "Under DevsySol, implement the bounded immutable Package Revision schema and deterministic fixtures against accepted criterion 129:deployment-reference-envelope; keep full #129 production, #130 acceptance and the #135/#136 order unchanged."

    def unique_edges(edges: list[dict]) -> list[dict]:
        seen = set()
        output = []
        for edge in edges:
            key = tuple(sorted(edge.items()))
            if key not in seen:
                seen.add(key)
                output.append(edge)
        return output

    execution_edges = unique_edges(execution_edges)
    coordination_edges = unique_edges(coordination_edges)
    related_edges = unique_edges(related_edges)
    aggregation_edges = unique_edges(aggregation_edges)

    graph["relationship_schema_version"] = 2
    graph["relationship_amendment"] = "canvas-execution-graph-20261009-v4"
    graph["counts"] = {stage: sum(row["classification"] == stage for row in rows.values()) for stage in ["READY", "ACTIVE", "REVIEW", "BLOCKED", "INTEGRATED", "COMPLETE"]}
    graph["worker_stage_snapshot"] = "2026-10-09T20:03:01Z"
    graph["current_active_workers"]["100"] = "Issue #100 slice 100-A active in /workspace/work/community-resume/canvas-authoring, branch feature/issue-100a-public-mcp-app-authoring-20261009, base 3fee; current HEAD/dirty state not reported."
    graph["current_active_workers"]["126"] = "Issue #126 bounded source-protocol proof active in /workspace/work/community-resume/mcp-showcase-proof, branch test/mcp-v2-showcase-protocol-20261009, base 3fee; not template completion; current HEAD/dirty state not reported."
    graph["relationship_model"] = {
        "execution_prerequisites": execution_edges,
        "scoped_execution_gates": slice_gates,
        "criteria": criteria,
        "coordination_parent_edges": coordination_edges,
        "related_product_direction_edges": related_edges,
        "full_acceptance_aggregation_edges": aggregation_edges,
        "superseded_untyped_edges": prior_edges,
        "execution_slices": slices,
        "amendment_source": "GitHub #71 comment 6087930051, #93 comment 6087948973, #101 comment 6087955791, #220 comment 6087968408, #254 comment 6087962754",
    }
    graph["scope"] = "Typed operational relationships; retained issue contracts and raw states remain unchanged. Only execution prerequisites participate in cycle/topological validation."
    graph = apply_named_scoped_criteria(graph, ledger)
    graph = apply_active_substages(graph, ledger)
    validate_graph(graph, ledger)
    return graph


def validate_graph(graph: dict, ledger: dict) -> list[int]:
    rows = graph.get("issues", [])
    by_id = {row["issue"]: row for row in rows}
    ledger_by_id = {row["issue"]: row for row in ledger["issues"]}
    if len(rows) != 54 or set(by_id) != set(ledger_by_id):
        raise ValueError("Expected exactly 54 matching issue projections")
    if graph.get("relationship_schema_version") != 2:
        raise ValueError("Expected typed relationship schema version 2")
    if graph.get("relationship_amendment") != "canvas-execution-graph-20261009-v4":
        raise ValueError("Expected the dated Canvas graph amendment identifier")
    for issue, row in by_id.items():
        source = ledger_by_id[issue]
        if row["retained_state"] != source["state"]:
            raise ValueError(f"Raw state changed for #{issue}")
        digest = hashlib.sha256(source["acceptance_contract"].encode()).hexdigest()
        if row["acceptance_contract_sha256"] != digest:
            raise ValueError(f"Retained contract digest changed for #{issue}")
    accepted = set()
    for closure in ledger.get("accepted_issue_closures", []):
        if not (closure.get("accepted") is True and closure.get("closed") is True and closure.get("owner_comment_id") and closure.get("audit")):
            raise ValueError(f"Incomplete whole-issue acceptance receipt: {closure}")
        if not (PROGRAM / closure["audit"]).is_file():
            raise ValueError(f"Missing whole-issue acceptance audit: {closure['audit']}")
        accepted.add(closure["issue"])
    complete = {row["issue"] for row in rows if row["classification"] == "COMPLETE"}
    if complete != accepted:
        raise ValueError(f"Whole-issue completion must match explicit closure receipts: graph={complete}, ledger={accepted}")
    expected_counts = {stage: sum(row["classification"] == stage for row in rows) for stage in ["READY", "ACTIVE", "REVIEW", "BLOCKED", "INTEGRATED", "COMPLETE"]}
    if graph.get("counts") != expected_counts:
        raise ValueError(f"Stage counts are stale: expected {expected_counts}, observed {graph.get('counts')}")
    # Supplemental program gates are dated amendments, not additions to the
    # retained 54-issue contract projection or its stage counts.
    amendments = ledger.get("supplemental_program_amendments", [])
    if graph.get("supplemental_program_amendments", []) != amendments:
        raise ValueError("Supplemental program amendments differ from the ledger source")
    retained_issue_ids = set(by_id)
    for amendment in amendments:
        for gate in amendment.get("supplemental_issue_gates", []):
            if gate.get("issue") in retained_issue_ids:
                raise ValueError("Supplemental issue gate must remain outside the retained issue projection")
            if gate.get("accounting_position") != "outside_original_54_issue_accounting":
                raise ValueError("Supplemental issue gate must declare its separate accounting position")
            if gate.get("issue") == 279 and gate.get("priority") != "P0":
                raise ValueError("The supplemental #279 regression gate must retain its reviewed P0 priority")

    latest_amendment = amendments[-1] if amendments else {}
    expected_substages = latest_amendment.get("active_substages", [])
    if graph.get("active_substages", []) != expected_substages:
        raise ValueError("Current active substage overlay differs from the latest dated amendment")
    expected_substage_time = latest_amendment.get("observed_at_utc") if expected_substages else None
    if graph.get("active_substages_observed_at_utc") != expected_substage_time:
        raise ValueError("Current active substage timestamp differs from its dated amendment")
    substage_ids = set()
    for substage in expected_substages:
        if substage.get("id") in substage_ids:
            raise ValueError(f"Duplicate active substage id: {substage.get('id')}")
        substage_ids.add(substage.get("id"))
        if substage.get("owner_issue") not in retained_issue_ids or substage.get("status") != "ACTIVE":
            raise ValueError(f"Invalid active substage owner or status: {substage}")
        required_fields = ("title", "scope", "limits", "whole_issue_effect", "evidence_basis")
        if not all(substage.get(key) for key in required_fields):
            raise ValueError(f"Incomplete active substage record: {substage}")

    model = graph["relationship_model"]
    ids = set(by_id)
    dependencies: dict[str, set[str]] = defaultdict(set)
    all_nodes = {f"issue:{issue}" for issue in ids}
    row_pairs = {
        (dependency, issue)
        for issue, row in by_id.items()
        for dependency in row["unresolved_open_issue_dependencies"]
    }
    edge_pairs = set()
    for edge in model["execution_prerequisites"]:
        prerequisite, consumer = edge["prerequisite"], edge["consumer"]
        if prerequisite not in ids or consumer not in ids:
            raise ValueError(f"Unknown issue in execution edge: {edge}")
        edge_pairs.add((prerequisite, consumer))
        dependencies[f"issue:{consumer}"].add(f"issue:{prerequisite}")
    if edge_pairs != row_pairs:
        raise ValueError(f"Issue rows and active execution edges disagree: rows={row_pairs ^ edge_pairs}")

    criteria = {item["id"]: item for item in model["criteria"]}
    slices = {item["id"]: item for item in model["execution_slices"]}
    if len(criteria) != len(model["criteria"]) or len(slices) != len(model["execution_slices"]):
        raise ValueError("Duplicate criterion or slice identifier")
    for item in criteria.values():
        if item["owner_issue"] not in ids or not item.get("description") or not item.get("status") or not item.get("evidence_basis"):
            raise ValueError(f"Incomplete criterion registry entry: {item}")
    for item in slices.values():
        if item["issue"] not in ids or not item.get("description") or not item.get("status"):
            raise ValueError(f"Incomplete execution slice entry: {item}")
    criterion_ids, slice_ids = set(criteria), set(slices)
    all_nodes |= {f"criterion:{identifier}" for identifier in criterion_ids}
    all_nodes |= {f"slice:{identifier}" for identifier in slice_ids}
    for edge in model["scoped_execution_gates"]:
        prereq, consumer = edge["prerequisite"], edge["consumer_slice"]
        if consumer not in slice_ids:
            raise ValueError(f"Unknown consumer slice: {edge}")
        if prereq in criterion_ids:
            prerequisite_node = f"criterion:{prereq}"
        elif prereq in slice_ids:
            prerequisite_node = f"slice:{prereq}"
        else:
            raise ValueError(f"Unknown criterion or slice prerequisite: {edge}")
        dependencies[f"slice:{consumer}"].add(prerequisite_node)
    accepted_129_envelope = criteria.get("129:deployment-reference-envelope", {})
    if accepted_129_envelope.get("status") != "ACCEPTED_FOR_130_SCHEMA_ONLY":
        raise ValueError("The #129 reference-envelope criterion must remain scoped to accepted #130 schema work")
    if not any(
        edge.get("prerequisite") == "129:deployment-reference-envelope"
        and edge.get("consumer_slice") == "130-schema"
        for edge in model["scoped_execution_gates"]
    ):
        raise ValueError("The accepted #129 envelope criterion must gate the 130-schema slice")
    topo = _topological_order(dependencies, all_nodes)

    expected_coordination: dict[int, set[int]] = defaultdict(set)
    for edge in model["coordination_parent_edges"]:
        parent, child = edge["parent_or_coordinator"], edge["child_or_scope"]
        if parent not in ids or child not in ids:
            raise ValueError(f"Unknown issue in coordination edge: {edge}")
        expected_coordination[child].add(parent)
    expected_related: dict[int, set[int]] = defaultdict(set)
    for edge in model["related_product_direction_edges"]:
        issue, related_issue = edge["issue"], edge["related_issue"]
        if issue not in ids or related_issue not in ids:
            raise ValueError(f"Unknown issue in related edge: {edge}")
        expected_related[issue].add(related_issue)
    expected_aggregation: dict[int, set[int]] = defaultdict(set)
    for edge in model["full_acceptance_aggregation_edges"]:
        parent, child = edge["parent"], edge["child"]
        if parent not in ids or child not in ids:
            raise ValueError(f"Unknown issue in aggregation edge: {edge}")
        expected_aggregation[parent].add(child)

    prior_pairs = {
        (edge["prerequisite"], edge["consumer"])
        for edge in model["superseded_untyped_edges"]
    }
    row_prior_pairs = {
        (dependency, issue)
        for issue, row in by_id.items()
        for dependency in row["prior_untyped_dependency_projection"]
    }
    if prior_pairs != row_prior_pairs:
        raise ValueError(f"Historical row projection and audit edges disagree: {prior_pairs ^ row_prior_pairs}")
    for issue, row in by_id.items():
        for field, expected in (
            ("coordination_parents", expected_coordination),
            ("related_product_direction", expected_related),
            ("full_acceptance_aggregation", expected_aggregation),
        ):
            if set(row[field]) != expected.get(issue, set()):
                raise ValueError(f"Issue #{issue} field {field} disagrees with typed edge model")

    # The specific false-cycle relations are prohibited from execution edges.
    forbidden = {(71, 127), (93, 127), (101, 127)}  # prerequisite -> consumer
    observed = {(edge["prerequisite"], edge["consumer"]) for edge in model["execution_prerequisites"]}
    if observed & forbidden:
        raise ValueError(f"Canvas parent/product/aggregation edge treated as execution: {observed & forbidden}")
    if set(by_id[127]["unresolved_open_issue_dependencies"]) & {71, 93, 101}:
        raise ValueError("#127 must not wait for #71/#93/#101 completion")
    if 127 not in by_id[71]["full_acceptance_aggregation"]:
        raise ValueError("#71 full acceptance must retain its #127 template aggregation")
    issue_level_gates = {71: {83, 99, 100, 129, 130, 135}, 99: {97, 98}, 126: {125}, 127: {99, 100}, 130: {129}}
    for issue, whole_issue_prerequisites in issue_level_gates.items():
        if set(by_id[issue]["unresolved_open_issue_dependencies"]) & whole_issue_prerequisites:
            raise ValueError(f"#{issue} must use scoped criterion gates instead of whole-issue prerequisites")
    return topo


def _topological_order(dependencies: dict, nodes: set) -> list:
    state: dict = {}
    result: list = []

    def visit(node):
        marker = state.get(node, 0)
        if marker == 1:
            raise ValueError(f"Execution dependency cycle includes {node!r}")
        if marker == 2:
            return
        state[node] = 1
        for prerequisite in sorted(dependencies.get(node, ())):
            visit(prerequisite)
        state[node] = 2
        result.append(node)

    for node in sorted(nodes):
        visit(node)
    return result


def render_markdown(graph: dict) -> str:
    model = graph["relationship_model"]
    parents = defaultdict(list)
    related = defaultdict(list)
    aggregate = defaultdict(list)
    for edge in model["coordination_parent_edges"]:
        parents[edge["child_or_scope"]].append(edge["parent_or_coordinator"])
    for edge in model["related_product_direction_edges"]:
        related[edge["issue"]].append(edge["related_issue"])
    for edge in model["full_acceptance_aggregation_edges"]:
        aggregate[edge["parent"]].append(edge["child"])
    header = [
        "# Actions operational execution graph",
        "",
        f"Worker-stage observation: {graph['worker_stage_snapshot']} (historical whole-issue classification snapshot). All 54 retained contracts remain unfinished except accepted whole issue #210; current active-substage overlays do not change raw states or stage counts.",
        "",
        "Relationship semantics: execution prerequisites gate only the identified implementation slice; parent/coordination and product/related edges never block execution; aggregation edges contribute to full parent acceptance. Only execution edges enter cycle/topological validation.",
        "",
        "Counts: " + ", ".join(f"{key}={graph['counts'].get(key,0)}" for key in ["READY","ACTIVE","REVIEW","BLOCKED","INTEGRATED","COMPLETE"]) + ".",
        "",
        "| Issue | Stage | Execution prerequisites | Parent / coordination | Related / product direction | Full-acceptance aggregation | Partial checkpoint | Next bounded action |",
        "|---|---|---|---|---|---|---|---|",
    ]
    rows = []
    for item in graph["issues"]:
        number = item["issue"]
        deps = ", ".join(f"#{value}" for value in item["unresolved_open_issue_dependencies"]) or "None"
        parent = ", ".join(f"#{value}" for value in sorted(set(parents[number]))) or "None"
        related_text = ", ".join(f"#{value}" for value in sorted(set(related[number]))) or "None"
        aggregates = ", ".join(f"#{value}" for value in sorted(set(aggregate[number]))) or "None"
        checkpoint = item.get("checkpoint_pr") or item.get("foundation_pr")
        partial = f"#{checkpoint}" if checkpoint else "See ledger"
        rows.append(f"| [#{number}](https://github.com/joshyorko/actions/issues/{number}) | {item['classification']} | {deps} | {parent} | {related_text} | {aggregates} | {partial} | {item['next_bounded_action']} |")
    criteria = ["", "## Referenced acceptance criteria", "", "| Criterion | Owner | Evidence state | Definition and evidence basis |", "|---|---:|---|---|"]
    for item in model["criteria"]:
        criteria.append(f"| {item['id']} | #{item['owner_issue']} | {item['status']} | {item['description']} Evidence: {item['evidence_basis']} |")
    slices = ["", "## Canvas implementation slices", "", "| Slice | Owning issue | Current evidence state | Required gates |", "|---|---:|---|---|"]
    for item in model["execution_slices"]:
        gates = [edge["prerequisite"] for edge in model["scoped_execution_gates"] if edge["consumer_slice"] == item["id"]]
        slices.append(f"| {item['id']}: {item['description']} | #{item['issue']} | {item['status']} | {', '.join(gates) if gates else 'None recorded'} |")
    amendments = ["", "## Supplemental program amendments (outside the retained 54 issue contracts)", ""]
    substages = graph.get("active_substages", [])
    if substages:
        amendments = [
            "",
            "## Current active bounded substages",
            "",
            f"Observed {graph['active_substages_observed_at_utc']}. These work records are separate from whole-issue classification and acceptance.",
            "",
        ] + amendments
        for item in substages:
            related = f", related issue #{item['related_issue']}" if item.get("related_issue") else ""
            amendments.insert(
                len(amendments) - 3,
                f"- `{item['id']}` — {item['status']}, owner issue #{item['owner_issue']}{related}: "
                f"{item['title']}. Scope: {item['scope']} Limits: {item['limits']} "
                f"Whole-issue effect: {item['whole_issue_effect']} Evidence basis: {item['evidence_basis']}",
            )
    for amendment in graph.get("supplemental_program_amendments", []):
        amendments.append(f"### {amendment['id']} — {amendment['observed_at_utc']}")
        amendments.append("")
        amendments.append(amendment["summary"])
        amendments.append("")
        amendments.append("| Supplemental gate | Status | Accounting | Scope and evidence |")
        amendments.append("|---|---|---|---|")
        for gate in amendment.get("supplemental_issue_gates", []):
            evidence = gate.get("reproduction", {})
            progress = gate.get("implementation_status", "")
            proof = f"{evidence.get('description', '')} Source `{evidence.get('source_commit', '')}`; [receipt]({evidence.get('path', '')}) (SHA-256 `{evidence.get('sha256', '')}`). Implementation observation: {progress}"
            amendments.append(
                f"| [#{gate['issue']}]({gate['url']}) {gate['title']} | {gate['status']} | outside original 54 | {gate['scope']} {proof} |"
            )
        for gate in amendment.get("retired_hosted_gates", []):
            amendments.append(
                f"| Retired hosted gate: `{gate['name']}` | RETIRED_BY_USER_STEERING | outside issue stages | "
                f"{gate['replacement_contract']} Source `{gate['source_commit']}`; focused local test {gate['focused_test_result']}; "
                f"hosted/external acceptance `{gate['hosted_acceptance']}`."
            )
        for criterion in amendment.get("accepted_scoped_criteria", []):
            amendments.append(
                f"| `#{criterion['owner_issue']}` {criterion['criterion_id']} → `{criterion['consumer_slice']}` | "
                f"{criterion['status']} | scoped criterion only | {criterion['description']} "
                f"Decision: {criterion['decision']} Evidence: [{criterion['evidence_path']}]({criterion['evidence_path']}) "
                f"(SHA-256 `{criterion['evidence_sha256']}`)."
            )
        amendments.append("")
    return "\n".join(header + rows + criteria + slices + amendments).rstrip() + "\n"


def sync_supplemental_amendment_note(path: Path, anchor: str, amendments: list[dict]) -> None:
    """Render the latest supplemental issue/gate amendment in narrative docs."""
    start = "<!-- supplemental-program-amendment:start -->"
    end = "<!-- supplemental-program-amendment:end -->"
    sections = [start, "", "## Supplemental program amendment"]
    for amendment in amendments:
        sections.extend(["", f"Observed {amendment['observed_at_utc']}. {amendment['summary']}"])
        for substage in amendment.get("active_substages", []):
            sections.append(
                f"- Active bounded substage `{substage['id']}` for #{substage['owner_issue']}: {substage['title']}. "
                f"{substage['scope']} Limits: {substage['limits']} Whole-issue effect: {substage['whole_issue_effect']} "
                f"Evidence: {substage['evidence_basis']}"
            )
        workers = amendment.get("current_worker_inventory", {}).get("workers", [])
        if workers:
            sections.append("- Current native/cloud worker inventory: " + ", ".join(
                f"{worker.get('name')} ({worker.get('status')})" for worker in workers
            ) + ".")
        for gate in amendment.get("supplemental_issue_gates", []):
            evidence = gate.get("reproduction", {})
            sections.append(
                f"- [#{gate['issue']}]({gate['url']}) is an OPEN {gate.get('priority', 'scoped')} gate "
                f"outside the original 54 issue contracts. {gate['scope']} Reproduction: "
                f"[source-backed receipt]({evidence.get('path', '')}) (SHA-256 `{evidence.get('sha256', '')}`). "
                f"Implementation: {gate.get('implementation_status', 'not reported')}."
            )
        for gate in amendment.get("retired_hosted_gates", []):
            sections.append(
                f"- `{gate['name']}` was retired as a hosted-service prerequisite by explicit user steering; "
                f"the replacement contract is source `{gate['source_commit']}` and its focused local test passed. "
                f"The change is not yet admitted on the current integration head; hosted/external acceptance is "
                f"`{gate['hosted_acceptance']}`. Details: [{gate['evidence_path']}]({gate['evidence_path']}) "
                f"(SHA-256 `{gate['evidence_sha256']}`)."
            )
        for criterion in amendment.get("accepted_scoped_criteria", []):
            sections.append(
                f"- `{criterion['criterion_id']}` enables only the recorded bounded `{criterion['consumer_slice']}` slice. "
                f"{criterion['decision']} Evidence: [{criterion['evidence_path']}]({criterion['evidence_path']}) "
                f"(SHA-256 `{criterion['evidence_sha256']}`)."
            )
    sections.extend(["", end])
    block = "\n".join(sections)
    text = path.read_text(encoding="utf-8")
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        text = before.rstrip() + "\n\n" + block + "\n\n" + after.lstrip("\n ")
    else:
        if anchor not in text:
            raise ValueError(f"Cannot find supplemental amendment insertion anchor in {path}")
        text = text.replace(anchor, anchor + "\n\n" + block + "\n", 1)
    path.write_text(text, encoding="utf-8")


def sync_markdown_note(path: Path, anchor: str) -> None:
    text = path.read_text(encoding="utf-8")
    start = f"<!-- canvas-graph-amendment:start -->"
    end = f"<!-- canvas-graph-amendment:end -->"
    block = f"{start}\n\n{AMENDMENT_NOTE}\n\n{end}\n"
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        text = before.rstrip() + "\n\n" + block + after.lstrip("\n")
    else:
        if anchor not in text:
            raise ValueError(f"Cannot find documentation insertion anchor in {path}")
        text = text.replace(anchor, anchor + "\n\n" + block.rstrip() + "\n", 1)
    path.write_text(text, encoding="utf-8")


def label_superseded_convergence_snapshots() -> None:
    """Keep immutable prior CI observations visibly historical after amendments."""
    ledger_text = LEDGER_MARKDOWN_PATH.read_text(encoding="utf-8")
    ledger_text = ledger_text.replace("[Active Cloud checkpoint]", "[Previous convergence snapshot]", 1)
    LEDGER_MARKDOWN_PATH.write_text(ledger_text, encoding="utf-8")
    handoff_text = HANDOFF_PATH.read_text(encoding="utf-8")
    handoff_text = handoff_text.replace(
        "## Current convergence — 2026-10-10T04:41:32Z",
        "## Previous convergence snapshot — 2026-10-10T04:41:32Z (superseded by the 05:01 amendment)",
        1,
    )
    handoff_text = handoff_text.replace(
        "## Previous convergence snapshot — 2026-10-10T04:41:32Z (superseded by the 04:58 amendment)",
        "## Previous convergence snapshot — 2026-10-10T04:41:32Z (superseded by the 05:01 amendment)",
        1,
    )
    handoff_text = handoff_text.replace(
        "## Current convergence — 2026-10-10T06:08:00Z",
        "## Previous convergence snapshot — 2026-10-10T06:08:00Z (superseded by the 06:25 amendment)",
        1,
    )
    HANDOFF_PATH.write_text(handoff_text, encoding="utf-8")


def update_graph_metadata(path: Path, graph: dict) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["execution_graph"]["relationship_schema_version"] = 2
    data["execution_graph"]["relationship_policy"] = (
        "Typed execution prerequisites and scoped criterion gates only; parent coordination, related "
        "product direction and full-acceptance aggregation are separately inspectable and nonblocking."
    )
    data["execution_graph"]["counts"] = graph["counts"]
    data["execution_graph"]["whole_contract_complete"] = graph["counts"]["COMPLETE"]
    data["supplemental_program_amendments"] = graph.get("supplemental_program_amendments", [])
    data["current_program_amendment"] = graph.get("current_program_amendment")
    if graph.get("current_program_amendment"):
        current = graph["current_program_amendment"]
        amendment = next(
            item for item in graph.get("supplemental_program_amendments", [])
            if item["id"] == Path(current["path"]).stem
        )
        data["status"] = amendment["summary"]
        data["checkpoint_status"] = amendment["summary"]
        data["checkpoint_observed_at"] = current["observed_at_utc"]
        checkpoint = amendment.get("integration_checkpoint", {})
        data["active_substages"] = copy.deepcopy(graph.get("active_substages", []))
        data["active_substages_observed_at_utc"] = graph.get("active_substages_observed_at_utc")
        data["current_active_workers"] = copy.deepcopy(amendment.get("current_active_workers", {}))
        data["current_worker_inventory"] = copy.deepcopy(amendment.get("current_worker_inventory", {}))
        if checkpoint.get("head"):
            old_head = data.get("integration_head")
            if old_head and old_head != checkpoint["head"]:
                data.setdefault("historical_projection_fields", {}).setdefault(
                    "integration_head_before_current_overlay",
                    {"value": old_head, "status": "historical; superseded by the dated current integration overlay"},
                )
            data["integration_head"] = checkpoint["head"]
            data["integration_head_observed_at_utc"] = current["observed_at_utc"]
            refs = copy.deepcopy(data.get("current_program_refs", {}))
            refs.update(
                observed_at_utc=current["observed_at_utc"],
                community=checkpoint.get("community"),
                integration=checkpoint["head"],
                release_ready=amendment.get("release_ready", False),
                receipt=current["path"],
                receipt_sha256=current["sha256"],
            )
            refs["integration/community-release-20261008"] = checkpoint["head"]
            data["current_program_refs"] = refs
            convergence = copy.deepcopy(checkpoint)
            convergence.update(
                observed_at_utc=current["observed_at_utc"],
                path=current["path"],
                sha256=current["sha256"],
                integration=checkpoint["head"],
                community=checkpoint.get("community"),
                release_ready=amendment.get("release_ready", False),
                issue_acceptance_changed=False,
                stage_counts_unchanged=True,
                retained_original_contracts=54,
            )
            data["current_pr_convergence"] = convergence
        data["projection_freshness"] = {
            "current_overlay_observed_at_utc": current["observed_at_utc"],
            "current_overlay_receipt": current["path"],
            "current_overlay_sha256": current["sha256"],
            "worker_stage_snapshot": {
                "observed_at_utc": data.get("execution_graph", {}).get("worker_stage_snapshot"),
                "meaning": "Historical whole-issue classification snapshot; current bounded work appears in active_substages and current_active_workers.",
            },
        }
        if path == RESUME_PATH:
            data["observed_at"] = current["observed_at_utc"]
    archive = PROGRAM / "evidence" / "canvas-execution-graph-amendment-20261009-v4.zip"
    manifest = PROGRAM / "evidence" / "canvas-execution-graph-amendment-20261009-v4.manifest.json"
    if archive.is_file() and manifest.is_file():
        data["graph_amendment_archive"] = {
            "path": "evidence/" + archive.name,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "size_bytes": archive.stat().st_size,
            "manifest": "evidence/" + manifest.name,
        }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_issue_metadata_updates(graph: dict, ledger: dict) -> None:
    """Apply dated, explicitly scoped operational metadata to both projections."""
    for amendment in ledger.get("supplemental_program_amendments", []):
        for issue, updates in amendment.get("issue_metadata_updates", {}).items():
            for document in (graph, ledger):
                row = next((item for item in document["issues"] if str(item["issue"]) == str(issue)), None)
                if row is None:
                    raise ValueError(f"metadata update references unknown issue #{issue}")
                row.update(updates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply typed edge policy and regenerate the Markdown projection")
    parser.add_argument("--check", action="store_true", help="Validate JSON/contract invariants and exact Markdown reproducibility")
    args = parser.parse_args()
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    if args.apply:
        graph["supplemental_program_amendments"] = copy.deepcopy(ledger.get("supplemental_program_amendments", []))
        graph["current_program_amendment"] = copy.deepcopy(ledger.get("current_program_amendment"))
        graph = upgrade_relationships(graph, ledger)
        apply_issue_metadata_updates(graph, ledger)
        amendments = ledger.get("supplemental_program_amendments", [])
        current = ledger.get("current_program_amendment")
        if not amendments or not current:
            GRAPH_PATH.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            MARKDOWN_PATH.write_text(render_markdown(graph), encoding="utf-8")
            return
        latest_amendment = amendments[-1]
        old_workers = graph.get("current_active_workers", {})
        if old_workers and not graph.get("historical_current_active_workers"):
            graph["historical_current_active_workers"] = {
                "observed_at_utc": graph.get("worker_stage_snapshot"),
                "workers": copy.deepcopy(old_workers),
            }
        graph["current_active_workers"] = copy.deepcopy(latest_amendment.get("current_active_workers", {}))
        graph["current_worker_inventory"] = copy.deepcopy(latest_amendment.get("current_worker_inventory", {}))
        graph["projection_freshness"] = {
            "current_overlay_observed_at_utc": ledger["current_program_amendment"]["observed_at_utc"],
            "current_overlay_receipt": ledger["current_program_amendment"]["path"],
            "current_overlay_sha256": ledger["current_program_amendment"]["sha256"],
            "worker_stage_snapshot": {
                "observed_at_utc": graph.get("worker_stage_snapshot"),
                "meaning": "Historical whole-issue classification snapshot; current bounded work appears in active_substages and current_active_workers.",
            },
        }
        graph["current_program_refs"] = {
            **graph.get("current_program_refs", {}),
            "observed_at_utc": ledger["current_program_amendment"]["observed_at_utc"],
            "community": latest_amendment["integration_checkpoint"]["community"],
            "integration": latest_amendment["integration_checkpoint"]["head"],
            "integration/community-release-20261008": latest_amendment["integration_checkpoint"]["head"],
            "receipt": ledger["current_program_amendment"]["path"],
            "receipt_sha256": ledger["current_program_amendment"]["sha256"],
        }
        graph["current_pr_convergence"] = {
            **latest_amendment["integration_checkpoint"],
            "observed_at_utc": ledger["current_program_amendment"]["observed_at_utc"],
            "path": ledger["current_program_amendment"]["path"],
            "sha256": ledger["current_program_amendment"]["sha256"],
            "integration": latest_amendment["integration_checkpoint"]["head"],
            "community": latest_amendment["integration_checkpoint"]["community"],
            "release_ready": latest_amendment.get("release_ready", False),
            "issue_acceptance_changed": False,
            "stage_counts_unchanged": True,
            "retained_original_contracts": 54,
        }
        graph["active_substages"] = copy.deepcopy(latest_amendment.get("active_substages", []))
        graph["active_substages_observed_at_utc"] = latest_amendment.get("observed_at_utc") if graph["active_substages"] else None
        GRAPH_PATH.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        MARKDOWN_PATH.write_text(render_markdown(graph), encoding="utf-8")
        LEDGER_PATH.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        update_graph_metadata(LEDGER_PATH, graph)
        update_graph_metadata(RESUME_PATH, graph)
        sync_markdown_note(LEDGER_MARKDOWN_PATH, "| Issue | Wave | Retained state | Owner / PR | Next bounded action |")
        sync_markdown_note(HANDOFF_PATH, "# Actions Community engineering handoff — active Cloud checkpoint")
        label_superseded_convergence_snapshots()
        supplemental = graph.get("supplemental_program_amendments", [])
        if supplemental:
            sync_supplemental_amendment_note(
                LEDGER_MARKDOWN_PATH,
                "# Community engineering ledger",
                supplemental,
            )
            sync_supplemental_amendment_note(
                HANDOFF_PATH,
                "# Actions Community engineering handoff — active Cloud checkpoint",
                supplemental,
            )
    elif args.check:
        validate_graph(graph, ledger)
        expected_metadata = {}
        for amendment in ledger.get("supplemental_program_amendments", []):
            for issue, updates in amendment.get("issue_metadata_updates", {}).items():
                expected_metadata.setdefault(str(issue), {}).update(updates)
        for issue, updates in expected_metadata.items():
            for document_name, document in (("community-execution-graph.json", graph), ("community-program-ledger.json", ledger)):
                row = next((item for item in document["issues"] if str(item["issue"]) == issue), None)
                if row is None or any(row.get(key) != value for key, value in updates.items()):
                    raise SystemExit(f"{document_name} has stale metadata for issue #{issue}")
        if MARKDOWN_PATH.read_text(encoding="utf-8") != render_markdown(graph):
            raise SystemExit("community-execution-graph.md is stale; run with --apply")
        for path in (LEDGER_PATH, RESUME_PATH):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("supplemental_program_amendments", []) != graph.get("supplemental_program_amendments", []):
                raise SystemExit(f"{path.name} has stale supplemental program amendments")
            if document.get("current_program_amendment") != graph.get("current_program_amendment"):
                raise SystemExit(f"{path.name} has a stale current program amendment pointer")
            if document["execution_graph"].get("relationship_schema_version") != 2:
                raise SystemExit(f"{path.name} lacks typed graph schema metadata")
            if document["execution_graph"].get("counts") != graph["counts"]:
                raise SystemExit(f"{path.name} has stale stage counts")
            if document["execution_graph"].get("whole_contract_complete") != graph["counts"]["COMPLETE"]:
                raise SystemExit(f"{path.name} has a stale whole-contract completion count")
            current_amendment = document.get("current_program_amendment")
            if current_amendment:
                amendment_path = PROGRAM / current_amendment["path"]
                if hashlib.sha256(amendment_path.read_bytes()).hexdigest() != current_amendment["sha256"]:
                    raise SystemExit(f"{path.name} has an invalid current program amendment hash")
        for path in (LEDGER_MARKDOWN_PATH, HANDOFF_PATH):
            text = path.read_text(encoding="utf-8")
            if "<!-- canvas-graph-amendment:start -->" not in text or AMENDMENT_NOTE not in text:
                raise SystemExit(f"{path.name} lacks the dated graph amendment note")
            amendments = graph.get("supplemental_program_amendments", [])
            if amendments and "<!-- supplemental-program-amendment:start -->" not in text:
                raise SystemExit(f"{path.name} lacks the supplemental program amendment note")
        for path in (LEDGER_PATH, RESUME_PATH):
            document = json.loads(path.read_text(encoding="utf-8"))
            archive = document.get("graph_amendment_archive")
            if archive:
                archive_path = PROGRAM / archive["path"]
                if hashlib.sha256(archive_path.read_bytes()).hexdigest() != archive["sha256"]:
                    raise SystemExit(f"{path.name} has an invalid amendment archive hash")
                manifest_path = PROGRAM / archive["manifest"]
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                expected_members = {"manifest.json"}
                for entry in manifest["entries"]:
                    member = Path(entry["path"])
                    if member.is_absolute() or ".." in member.parts:
                        raise SystemExit(f"Unsafe amendment archive member: {entry['path']}")
                    expected_members.add(entry["path"])
                    payload = PROGRAM / "evidence" / entry["path"]
                    if payload.stat().st_size != entry["size_bytes"] or hashlib.sha256(payload.read_bytes()).hexdigest() != entry["sha256"]:
                        raise SystemExit(f"Amendment archive payload differs from manifest: {entry['path']}")
                with zipfile.ZipFile(archive_path) as zf:
                    if set(zf.namelist()) != expected_members or zf.read("manifest.json") != manifest_path.read_bytes():
                        raise SystemExit("Amendment ZIP members/manifest do not match the checked manifest")
        for amendment in graph.get("supplemental_program_amendments", []):
            for entry in amendment.get("evidence", []):
                evidence_path = PROGRAM / entry["path"]
                if not evidence_path.is_file():
                    raise SystemExit(f"Missing supplemental amendment evidence: {entry['path']}")
                payload = evidence_path.read_bytes()
                if len(payload) != entry["size_bytes"] or hashlib.sha256(payload).hexdigest() != entry["sha256"]:
                    raise SystemExit(f"Supplemental amendment evidence hash mismatch: {entry['path']}")
    else:
        parser.error("choose --apply or --check")
    print(f"validated {len(graph['issues'])} issue projections; COMPLETE={graph['counts'].get('COMPLETE', 0)}")


if __name__ == "__main__":
    main()
