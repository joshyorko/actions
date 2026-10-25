"""Real shell regression: failed scans/commits must never reach publication."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


WRAPPER = Path(__file__).resolve().parents[2] / "scripts/publish_evidence.sh"


class EvidencePublicationTests(unittest.TestCase):
    def run_pipeline(
        self, payload, *, commit_exit=0, working_copy=None, raw_json=None, mode=None
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_git = shutil.which("git")
            subprocess.run([real_git, "init", "-q", str(root)], check=True)
            evidence = root / "docs/program/evidence/test/receipt.json"
            evidence.parent.mkdir(parents=True)
            evidence.write_text(
                raw_json if raw_json is not None else json.dumps(payload)
            )
            subprocess.run([real_git, "-C", str(root), "add", "."], check=True)
            if working_copy is not None:
                evidence.write_text(json.dumps(working_copy))
            calls = root / "publication-calls"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_git = fake_bin / "git"
            fake_git.write_text(
                "#!/usr/bin/env python3\n"
                "import os,subprocess,sys\n"
                "args=sys.argv[1:]\n"
                "operation=args[2] if args[:1]==['-C'] else args[0]\n"
                "if operation in ('commit','push'):\n"
                " with open(os.environ['TEST_PUBLICATION_CALLS'],'a') as f: f.write(operation+'\\n')\n"
                " sys.exit(int(os.environ['TEST_COMMIT_EXIT']) if operation=='commit' else 0)\n"
                "sys.exit(subprocess.call([os.environ['TEST_REAL_GIT'],*args]))\n"
            )
            fake_git.chmod(0o755)
            environment = dict(
                os.environ,
                PATH=str(fake_bin) + os.pathsep + os.environ["PATH"],
                TEST_REAL_GIT=real_git,
                TEST_PUBLICATION_CALLS=str(calls),
                TEST_COMMIT_EXIT=str(commit_exit),
            )
            result = subprocess.run(
                ["bash", str(WRAPPER), "existing-test-branch", "test evidence"]
                + ([mode] if mode is not None else []),
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
            )
            return result, calls.read_text().splitlines() if calls.exists() else []

    def test_failed_scan_stops_shell_before_commit_and_push(self):
        secret = "synthetic-do-not-print-" + "x" * 43
        result, calls = self.run_pipeline({"_meta": {"token": secret}})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_scan_reads_index_even_if_working_copy_was_redacted(self):
        result, calls = self.run_pipeline(
            {"token": "synthetic-staged-value"},
            working_copy={"token": "[redacted]"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_failed_commit_stops_shell_before_push(self):
        result, calls = self.run_pipeline({"token": "[redacted]"}, commit_exit=23)
        self.assertEqual(result.returncode, 23)
        self.assertEqual(calls, ["commit"])

    def test_duplicate_json_fields_cannot_hide_a_value(self):
        result, calls = self.run_pipeline(
            {}, raw_json='{"token":"synthetic-hidden-value","token":"[redacted]"}'
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        self.assertNotIn("synthetic-hidden-value", result.stdout + result.stderr)

    def test_invalid_json_stops_shell_before_commit_and_push(self):
        result, calls = self.run_pipeline({}, raw_json="{invalid evidence")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_successful_scan_and_commit_allow_push_in_order(self):
        result, calls = self.run_pipeline({"token": "[redacted-stopped-session]"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, ["commit", "push"])

    def test_commit_only_still_scans_and_never_pushes(self):
        result, calls = self.run_pipeline({"token": "[redacted]"}, mode="--commit-only")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, ["commit"])
        result, calls = self.run_pipeline(
            {"token": "synthetic-secret"}, mode="--commit-only"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_unknown_mode_cannot_fall_through_to_push(self):
        result, calls = self.run_pipeline({}, mode="--unknown")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
