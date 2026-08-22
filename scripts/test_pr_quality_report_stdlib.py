import json
import tempfile
import unittest
from pathlib import Path

from pr_quality_report import build_report, load_records


class PrQualityReportTest(unittest.TestCase):
    def test_audit_workflow_checks_submitted_range(self):
        workflow = Path(__file__).parents[1] / ".github/workflows/ai-audit.yml"
        text = workflow.read_text()
        self.assertIn("fetch-depth: 0", text)
        self.assertIn('git diff --name-only "$BASE_SHA" "$HEAD_SHA"', text)
        self.assertIn('git diff --check "$BASE_SHA" "$HEAD_SHA"', text)
        self.assertIn('[[ "$BASE_SHA" =~ ^[0-9a-f]{40}$ ]]', text)

    def test_report_counts_explicit_fields(self):
        report = build_report([
            {"number": 1, "merged": True, "approved": True, "labels": ["bug"]},
            {"number": 2, "changes_requested": True},
        ])
        self.assertEqual(report["merged"], 1)
        self.assertEqual(report["acceptance_rate"], 0.5)

    def test_schema_rejects_boolean_numbers_and_non_boolean_flags(self):
        for record in ({"number": True}, {"number": 1, "approved": "yes"}):
            with self.subTest(record=record), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "records.jsonl"
                path.write_text(json.dumps(record) + "\n")
                with self.assertRaises(ValueError):
                    load_records(path)


if __name__ == "__main__":
    unittest.main()
