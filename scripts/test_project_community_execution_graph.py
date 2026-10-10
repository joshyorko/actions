"""Regression checks for typed community execution relationships."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from project_community_execution_graph import (
    GRAPH_PATH,
    LEDGER_PATH,
    ROOT,
    _topological_order,
    render_markdown,
    sync_supplemental_amendment_note,
    upgrade_relationships,
    validate_graph,
)


def run_cli(command: list[str], repo: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if os.name != "nt":
        # Reproduce a non-UTF-8 process locale on Unix. Windows CI exercises
        # the native Windows default encoding in the same CLI fixture.
        env.update({"LC_ALL": "C", "PYTHONUTF8": "0"})
    result = subprocess.run(command, cwd=repo, capture_output=True, text=True, encoding="utf-8", env=env)
    if result.returncode:
        raise AssertionError(
            f"CLI command failed ({result.returncode}): {command!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


class ExecutionGraphProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
        self.ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))

    def test_manifest_payload_checkout_preserves_exact_git_bytes(self) -> None:
        relative_path = "docs/program/evidence/canvas-execution-graph-amendment-20261009-v4.json"
        attributes = subprocess.run(
            ["git", "check-attr", "text", "--", relative_path],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertTrue(attributes.stdout.rstrip().endswith(": text: unset"), attributes.stdout)

        manifest_path = ROOT / "docs/program/evidence/canvas-execution-graph-amendment-20261009-v4.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = next(item for item in manifest["entries"] if item["path"] == Path(relative_path).name)
        payload = ROOT / relative_path
        content = payload.read_bytes()
        self.assertEqual(entry["size_bytes"], len(content))
        self.assertEqual(entry["sha256"], hashlib.sha256(content).hexdigest())

        receipts = ROOT / "docs/program/evidence/devsy-convergence-20261010"
        manifest_path = receipts / "SHA256SUMS"
        for line in manifest_path.read_text(encoding="ascii").splitlines():
            digest, name = line.split("  ", 1)
            receipt_path = f"docs/program/evidence/devsy-convergence-20261010/{name}"
            attributes = subprocess.run(
                ["git", "check-attr", "text", "--", receipt_path],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertTrue(attributes.stdout.rstrip().endswith(": text: unset"), attributes.stdout)
            receipt = (receipts / name).read_bytes()
            self.assertEqual(digest, hashlib.sha256(receipt).hexdigest(), name)

        current_amendment_path = ROOT / "docs/program" / self.graph["current_program_amendment"]["path"]
        current_amendment = json.loads(current_amendment_path.read_text(encoding="utf-8"))
        for entry in current_amendment["evidence"]:
            receipt_path = f"docs/program/{entry['path']}"
            attributes = subprocess.run(
                ["git", "check-attr", "text", "--", receipt_path],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertTrue(attributes.stdout.rstrip().endswith(": text: unset"), attributes.stdout)
            payload = ROOT / receipt_path
            self.assertEqual(entry["size_bytes"], payload.stat().st_size)
            self.assertEqual(entry["sha256"], hashlib.sha256(payload.read_bytes()).hexdigest())

    def test_canvas_parent_cycle_is_removed_from_execution_dag(self) -> None:
        upgraded = upgrade_relationships(copy.deepcopy(self.graph), self.ledger)
        old_rows = {row["issue"]: row for row in upgraded["issues"]}
        old_edges = defaultdict(set)
        for edge in upgraded["relationship_model"]["superseded_untyped_edges"]:
            old_edges[edge["consumer"]].add(edge["prerequisite"])
        with self.assertRaisesRegex(ValueError, "cycle"):
            _topological_order(old_edges, set(old_rows))

        validate_graph(upgraded, self.ledger)
        by_id = {row["issue"]: row for row in upgraded["issues"]}
        self.assertFalse(set(by_id[127]["unresolved_open_issue_dependencies"]) & {71, 93, 101})
        self.assertIn(127, by_id[71]["full_acceptance_aggregation"])
        self.assertIn(71, by_id[127]["related_product_direction"])
        self.assertIn(93, by_id[127]["coordination_parents"])
        self.assertIn(101, by_id[127]["coordination_parents"])
        self.assertNotIn(99, by_id[71]["unresolved_open_issue_dependencies"])
        self.assertNotIn(100, by_id[71]["unresolved_open_issue_dependencies"])
        self.assertNotIn(99, by_id[127]["unresolved_open_issue_dependencies"])
        self.assertNotIn(100, by_id[127]["unresolved_open_issue_dependencies"])
        self.assertNotIn(97, by_id[99]["unresolved_open_issue_dependencies"])
        self.assertNotIn(98, by_id[99]["unresolved_open_issue_dependencies"])
        self.assertNotIn(125, by_id[126]["unresolved_open_issue_dependencies"])
        gates = upgraded["relationship_model"]["scoped_execution_gates"]
        self.assertTrue(any(edge["prerequisite"] == "125:public-package-boundary" and edge["consumer_slice"] == "126-template" for edge in gates))
        self.assertIn(209, by_id[93]["related_product_direction"])
        self.assertNotIn(209, by_id[93]["full_acceptance_aggregation"])
        self.assertEqual([], by_id[71]["unresolved_open_issue_dependencies"])
        self.assertTrue(any(edge["prerequisite"] == "130:package-revision" and edge["consumer_slice"] == "71-local" for edge in gates))

    def test_real_execution_cycle_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "cycle"):
            _topological_order({1: {2}, 2: {1}}, {1, 2})

    def test_projection_preserves_all_contracts_states_and_single_completion(self) -> None:
        upgraded = upgrade_relationships(copy.deepcopy(self.graph), self.ledger)
        rows = {row["issue"]: row for row in upgraded["issues"]}
        source = {row["issue"]: row for row in self.ledger["issues"]}
        self.assertEqual(54, len(rows))
        for issue, row in rows.items():
            self.assertEqual(source[issue]["state"], row["retained_state"])
            digest = hashlib.sha256(source[issue]["acceptance_contract"].encode()).hexdigest()
            self.assertEqual(digest, row["acceptance_contract_sha256"])
        self.assertEqual([210], [row["issue"] for row in rows.values() if row["classification"] == "COMPLETE"])

    def test_supplemental_issue_gate_does_not_change_original_issue_accounting(self) -> None:
        graph = upgrade_relationships(copy.deepcopy(self.graph), self.ledger)
        self.assertEqual(54, len(self.ledger["issues"]))
        self.assertEqual(54, len(graph["issues"]))
        self.assertEqual({"READY": 0, "ACTIVE": 7, "REVIEW": 8, "BLOCKED": 29, "INTEGRATED": 9, "COMPLETE": 1}, graph["counts"])
        amendment = self.ledger["supplemental_program_amendments"][0]
        gate = amendment["supplemental_issue_gates"][0]
        self.assertEqual(279, gate["issue"])
        self.assertEqual("outside_original_54_issue_accounting", gate["accounting_position"])
        self.assertNotIn(279, {row["issue"] for row in graph["issues"]})
        validate_graph(graph, self.ledger)
        markdown = render_markdown(graph)
        self.assertIn("Supplemental program amendments (outside the retained 54 issue contracts)", markdown)
        self.assertIn("#279", markdown)
        self.assertIn("RETIRED_BY_EXPLICIT_USER_STEERING", str(amendment))

    def test_supplemental_issue_cannot_be_added_to_retained_contract_projection(self) -> None:
        graph = upgrade_relationships(copy.deepcopy(self.graph), self.ledger)
        graph["issues"].append(copy.deepcopy(graph["issues"][0]))
        graph["issues"][-1]["issue"] = 279
        graph["issues"][-1]["classification"] = "BLOCKED"
        with self.assertRaisesRegex(ValueError, "exactly 54 matching issue projections"):
            validate_graph(graph, self.ledger)

    def test_accepted_129_interface_unblocks_only_130_schema_slice(self) -> None:
        graph = upgrade_relationships(copy.deepcopy(self.graph), self.ledger)
        model = graph["relationship_model"]
        criterion = next(item for item in model["criteria"] if item["id"] == "129:deployment-reference-envelope")
        slice_row = next(item for item in model["execution_slices"] if item["id"] == "130-schema")
        self.assertEqual("ACCEPTED_FOR_130_SCHEMA_ONLY", criterion["status"])
        self.assertIn("READY_FOR_BOUNDED_SCHEMA_FIXTURE", slice_row["status"])
        self.assertTrue(any(edge["prerequisite"] == criterion["id"] and edge["consumer_slice"] == "130-schema" for edge in model["scoped_execution_gates"]))
        rows = {item["issue"]: item for item in graph["issues"]}
        self.assertEqual("BLOCKED", rows[130]["classification"])
        self.assertNotIn(129, rows[130]["unresolved_open_issue_dependencies"])
        self.assertIn(129, rows[135]["unresolved_open_issue_dependencies"])

    def test_126_installed_wheel_criterion_does_not_complete_whole_issue(self) -> None:
        graph = upgrade_relationships(copy.deepcopy(self.graph), self.ledger)
        model = graph["relationship_model"]
        issue = next(row for row in graph["issues"] if row["issue"] == 126)
        criterion = next(item for item in model["criteria"] if item["id"] == "126:linux-installed-wheel-offline-project-creation")
        slice_row = next(item for item in model["execution_slices"] if item["id"] == "126-installed-wheel-offline")
        self.assertEqual("ACTIVE", issue["classification"])
        self.assertEqual("NOT_STARTED", issue["retained_state"])
        self.assertEqual("ACCEPTED_LINUX_INSTALLED_WHEEL_TEMPLATE_CREATION_ONLY", criterion["status"])
        self.assertIn("whole #126 remains open", issue["reason"])
        self.assertIn("remaining #126 acceptance stay open", slice_row["status"])

    def test_projection_is_idempotent(self) -> None:
        once = upgrade_relationships(copy.deepcopy(self.graph), self.ledger)
        twice = upgrade_relationships(copy.deepcopy(once), self.ledger)
        self.assertEqual(once, twice)
        twice["issues"][0]["next_bounded_action"] = "Later reviewed typed-graph edit"
        self.assertEqual("Later reviewed typed-graph edit", upgrade_relationships(twice, self.ledger)["issues"][0]["next_bounded_action"])

    def test_unknown_scoped_prerequisite_is_rejected(self) -> None:
        graph = upgrade_relationships(copy.deepcopy(self.graph), self.ledger)
        graph["relationship_model"]["scoped_execution_gates"][0]["prerequisite"] = "125:typo"
        with self.assertRaisesRegex(ValueError, "Unknown criterion or slice"):
            validate_graph(graph, self.ledger)

        graph = copy.deepcopy(self.graph)
        graph["relationship_model"]["scoped_execution_gates"][0]["consumer_slice"] = "404-no-slice"
        with self.assertRaisesRegex(ValueError, "Unknown consumer slice"):
            validate_graph(graph, self.ledger)

    def test_scoped_slice_cycle_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["relationship_model"]["scoped_execution_gates"].append({
            "prerequisite": "127-template",
            "consumer_slice": "100-A",
            "scope": "deliberate cycle regression",
        })
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_graph(graph, self.ledger)

    def test_unknown_issue_execution_edge_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["relationship_model"]["execution_prerequisites"].append({
            "prerequisite": 999,
            "consumer": 71,
            "scope": "deliberate unknown issue regression",
        })
        with self.assertRaisesRegex(ValueError, "Unknown issue"):
            validate_graph(graph, self.ledger)

    def test_typed_row_projection_must_match_edge_model(self) -> None:
        graph = copy.deepcopy(self.graph)
        next(row for row in graph["issues"] if row["issue"] == 127)["coordination_parents"].remove(93)
        with self.assertRaisesRegex(ValueError, "coordination_parents"):
            validate_graph(graph, self.ledger)

    def test_legacy_projection_must_match_audit_edges(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["issues"][0]["prior_untyped_dependency_projection"].append(999)
        with self.assertRaisesRegex(ValueError, "Historical row projection"):
            validate_graph(graph, self.ledger)

    def test_cli_apply_is_reproducible_and_check_passes(self) -> None:
        repo = Path(tempfile.mkdtemp(prefix="community-graph-cli-"))
        self.addCleanup(shutil.rmtree, repo, ignore_errors=True)
        for relative in (
            "scripts/project_community_execution_graph.py",
            "docs/program/community-execution-graph.json",
            "docs/program/community-execution-graph.md",
            "docs/program/community-program-ledger.json",
            "docs/program/community-program-ledger.md",
            "docs/program/community-resume-20261009.json",
            "docs/program/engineering-handoff.md",
            "docs/program/evidence/release-contract-audit-20261009.md",
            "docs/program/evidence/canvas-execution-graph-amendment-20261009-v4.zip",
            "docs/program/evidence/canvas-execution-graph-amendment-20261009-v4.manifest.json",
            "docs/program/evidence/canvas-execution-graph-amendment-20261009-v4.json",
            "docs/program/evidence/canvas-execution-graph-amendment-20261009-v4.md",
            "docs/program/evidence/pr273-multipackage-disable-reproduction-84b8c70a.md",
            "docs/program/evidence/issue-279-readback-20261010T0455Z.json",
            "docs/program/evidence/hosted-robocorp-gate-retirement-20261010T0455Z.json",
            "docs/program/evidence/program-amendment-20261010T0501Z.json",
            "docs/program/evidence/pr129-pr130-contract-review-20261010T0455Z.md",
            "docs/program/evidence/issue-130-criterion-acceptance-6094007327.json",
            "docs/program/evidence/program-amendment-20261010T0503Z.json",
            "docs/program/evidence/program-amendment-20261010T0509Z.json",
            "docs/program/evidence/devsy-convergence-status-20261010T0508Z.json",
            "docs/program/evidence/program-amendment-20261010T0514Z.json",
            "docs/program/evidence/devsy-current-slice-status-20261010T0514Z.json",
            "docs/program/evidence/mcp126-installed-wheel-offline-template-proof-20261010T050851Z.json",
            "docs/program/evidence/cas-dispatch-20261010T0500Z.json",
            "docs/program/evidence/cas-owner-pod-failed-20261010T0505Z.json",
            "docs/program/evidence/cas-evidence-branch-readback-20261010T0506Z.json",
            "docs/skills/repository-operations.md",
        ):
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        source_evidence = ROOT / "docs/program/evidence/devsy-convergence-20261010"
        destination_evidence = repo / "docs/program/evidence/devsy-convergence-20261010"
        destination_evidence.mkdir(parents=True, exist_ok=True)
        for relative in ["SHA256SUMS"] + [
            line.split("  ", 1)[1]
            for line in (source_evidence / "SHA256SUMS").read_text(encoding="ascii").splitlines()
        ]:
            shutil.copy2(source_evidence / relative, destination_evidence / relative)
        graph_path = repo / "docs/program/community-execution-graph.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph.pop("relationship_amendment", None)
        for row in graph["issues"]:
            row["unresolved_open_issue_dependencies"] = row["prior_untyped_dependency_projection"]
            row.pop("prior_untyped_dependency_projection", None)
            for field in ("coordination_parents", "related_product_direction", "full_acceptance_aggregation"):
                row.pop(field, None)
        graph.pop("relationship_schema_version", None)
        graph.pop("relationship_model", None)
        graph_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")

        command = [sys.executable, str(repo / "scripts/project_community_execution_graph.py"), "--apply"]
        run_cli(command, repo)
        outputs = [
            (repo / relative).read_bytes()
            for relative in (
                "docs/program/community-execution-graph.json",
                "docs/program/community-execution-graph.md",
                "docs/program/community-program-ledger.json",
                "docs/program/community-program-ledger.md",
                "docs/program/community-resume-20261009.json",
                "docs/program/engineering-handoff.md",
            )
        ]
        run_cli(command, repo)
        self.assertEqual(outputs, [
            (repo / relative).read_bytes()
            for relative in (
                "docs/program/community-execution-graph.json",
                "docs/program/community-execution-graph.md",
                "docs/program/community-program-ledger.json",
                "docs/program/community-program-ledger.md",
                "docs/program/community-resume-20261009.json",
                "docs/program/engineering-handoff.md",
            )
        ])
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph["issues"][0]["next_bounded_action"] = "Preserve future typed graph edits"
        graph_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
        run_cli(command, repo)
        self.assertEqual("Preserve future typed graph edits", next(row["next_bounded_action"] for row in json.loads(graph_path.read_text(encoding="utf-8"))["issues"] if row["issue"] == graph["issues"][0]["issue"]))
        check = [sys.executable, str(repo / "scripts/project_community_execution_graph.py"), "--check"]
        checked = subprocess.run(check, cwd=repo, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, checked.returncode, checked.stdout + checked.stderr)

    def test_markdown_is_deterministic_and_relationship_types_are_visible(self) -> None:
        upgraded = upgrade_relationships(copy.deepcopy(self.graph), self.ledger)
        output = render_markdown(upgraded)
        self.assertIn("Parent / coordination", output)
        self.assertIn("Full-acceptance aggregation", output)
        self.assertIn("#127", next(line for line in output.splitlines() if "#71]" in line))
        self.assertIn("100-A", output)
        self.assertIn("83:run-attempt-authority", output)
        self.assertEqual(output, render_markdown(upgraded))

    def test_supplemental_markers_are_separated_from_following_prose(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            document = Path(temporary) / "handoff.md"
            document.write_text(
                "Intro.\n\n<!-- supplemental-program-amendment:start -->\nold\n"
                "<!-- supplemental-program-amendment:end --> Following historical text.\n",
                encoding="utf-8",
            )
            sync_supplemental_amendment_note(
                document,
                "unused anchor",
                [{"observed_at_utc": "2026-10-10T05:03:14Z", "summary": "Current status."}],
            )
            rendered = document.read_text(encoding="utf-8")
        self.assertIn("<!-- supplemental-program-amendment:end -->\n\nFollowing historical text.", rendered)


if __name__ == "__main__":
    unittest.main()
