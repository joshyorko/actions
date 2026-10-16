import importlib.util
import unittest
from unittest.mock import patch
import subprocess
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "qualify", Path(__file__).with_name("qualify_runtime_release_button.py")
)
qualify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualify)


class DispatchContract(unittest.TestCase):
    def test_job_log_escape_sequences_are_captured_and_removed(self):
        def cli(command, **kwargs):
            if "--allow-escape-sequences" not in command:
                return subprocess.CompletedProcess(
                    command, 1, "", "the response contains terminal escape sequences"
                )
            self.assertTrue(kwargs["capture_output"])
            return subprocess.CompletedProcess(
                command, 0, "\x1b[31mnever rerun preparation\x1b[0m\n", ""
            )

        with (
            patch.object(qualify.subprocess, "run", side_effect=cli),
            patch.object(qualify.time, "monotonic", side_effect=[0, 181]),
        ):
            self.assertEqual(qualify.job_logs(123), "never rerun preparation\n")

    def test_saved_preparation_rejects_another_source(self):
        saved = {
            "id": 123,
            "run_attempt": 1,
            "head_sha": "b" * 40,
            "head_branch": "community",
            "event": "workflow_dispatch",
            "path": ".github/workflows/runtime-release-prepare.yml",
            "status": "completed",
            "conclusion": "success",
        }
        with patch.object(qualify, "api", return_value=saved):
            with self.assertRaisesRegex(
                qualify.QualificationError, "saved preparation identity mismatch"
            ):
                qualify.saved_preparation(123, "a" * 40)

    def test_job_log_read_waits_for_availability(self):
        pending = subprocess.CompletedProcess([], 1, "", "gh: Not Found (HTTP 404)")
        ready = subprocess.CompletedProcess([], 0, "never rerun preparation", "")
        with (
            patch.object(qualify.subprocess, "run", side_effect=[pending, ready]),
            patch.object(qualify.time, "sleep"),
        ):
            self.assertEqual(qualify.job_logs(123), "never rerun preparation")

    def test_job_log_read_reports_bounded_failure(self):
        pending = subprocess.CompletedProcess([], 1, "", "gh: Not Found (HTTP 404)")
        with (
            patch.object(qualify.subprocess, "run", return_value=pending),
            patch.object(qualify.time, "monotonic", side_effect=[0, 181]),
        ):
            with self.assertRaisesRegex(
                qualify.QualificationError, "job123 logs unavailable.*HTTP 404"
            ):
                qualify.job_logs(123)

    def test_validation_can_never_select_publication(self):
        workflow, inputs = qualify.dispatch_input(
            "validate", "a" * 40, "b" * 40, "1.0.4", 123, "c" * 64
        )
        self.assertEqual(workflow, qualify.VALIDATE)
        self.assertEqual(inputs["operation"], "validate")
        with self.assertRaises(qualify.QualificationError):
            qualify.dispatch_input(
                "publish", "a" * 40, "b" * 40, "1.0.4", 123, "c" * 64
            )

    def test_source_inputs_are_fixed_and_cannot_inject(self):
        for source in ("community", "a" * 39, "a" * 40 + ";exit"):
            with self.assertRaises(qualify.QualificationError):
                qualify.dispatch_input("prepare", source, "b" * 40, "1.0.4")
        with self.assertRaises(qualify.QualificationError):
            qualify.dispatch_input("prepare", "a" * 40, "b" * 40, "1.0.3")

    def test_no_ambiguous_or_stale_dispatch_can_be_adopted(self):
        run = {
            "id": 12,
            "head_sha": "a" * 40,
            "display_title": "expected",
            "event": "workflow_dispatch",
            "head_branch": "community",
        }
        arguments = dict(after=11, source="a" * 40, title="expected")
        self.assertEqual(qualify.select_run([run], **arguments), run)
        self.assertIsNone(qualify.select_run([dict(run, id=10)], **arguments))
        with self.assertRaises(qualify.QualificationError):
            qualify.select_run([run, dict(run, id=13)], **arguments)

    def test_write_allowlist_blocks_publication_and_other_mutations(self):
        for path in (
            f"repos/{qualify.REPO}/releases",
            f"repos/{qualify.REPO}/git/refs",
        ):
            with self.assertRaises(qualify.QualificationError):
                qualify.api(path, method="POST", data={})
        endpoint = (
            f"repos/{qualify.REPO}/actions/workflows/{qualify.VALIDATE}/dispatches"
        )
        with self.assertRaises(qualify.QualificationError):
            qualify.api(
                endpoint,
                method="POST",
                data={"ref": "community", "inputs": {"operation": "publish"}},
            )


if __name__ == "__main__":
    unittest.main()
