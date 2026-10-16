import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location(
    "recovery_qualification",
    Path(__file__).with_name("qualify_runtime_release_recovery.py"),
)
qualify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualify)


class DisposableGuard(unittest.TestCase):
    def setUp(self):
        pin = patch.object(qualify, "DISPOSABLE_PREPARATION", 456, create=True)
        pin.start()
        self.addCleanup(pin.stop)
        for key, value in [("CREATION_CONTROLLER", 900), ("CREATION_SHA", "c" * 40)]:
            item = patch.object(qualify, key, value, create=True)
            item.start()
            self.addCleanup(item.stop)

    def fixture(self):
        request = {
            "source_sha": "a" * 40,
            "qualification_sha": "b" * 40,
            "version": "1.0.4",
        }
        manifest = {
            "preparation_run_id": 456,
            "preparation_run_attempt": 1,
            "controller_sha": "a" * 40,
            **request,
        }
        proof = {
            "status": "PASS",
            "purpose": "disposable-recovery-rehearsal",
            "disposable_preparation_run_id": 456,
            "creation_controller_run_id": 900,
            "creation_controller_sha": "c" * 40,
            "bundles": [
                {
                    "label": "disposable",
                    "run_id": 456,
                    "manifest_sha256": "d" * 64,
                    "artifact_id": 700,
                    "artifact_digest": "sha256:" + "e" * 64,
                    **request,
                }
            ],
        }
        return request, manifest, proof

    def authorize(self, proof, manifest, request, digest="d" * 64):
        function = getattr(qualify, "authorize_disposable", None)
        self.assertIsNotNone(function, "disposable authorization guard missing")
        return function(proof, manifest, digest, request)

    def test_fresh_explicit_disposable_receipt_is_admitted(self):
        request, manifest, proof = self.fixture()
        self.assertEqual(self.authorize(proof, manifest, request), 456)

    def test_owner_id_is_forbidden_even_with_a_forged_matching_receipt(self):
        request, manifest, proof = self.fixture()
        manifest["preparation_run_id"] = qualify.PROTECTED_OWNER
        proof["disposable_preparation_run_id"] = qualify.PROTECTED_OWNER
        proof["bundles"][0]["run_id"] = qualify.PROTECTED_OWNER
        with self.assertRaisesRegex(
            qualify.support.QualificationError, "protected owner"
        ):
            self.authorize(proof, manifest, request)

    def test_another_run_cannot_be_marked_disposable_by_forging_the_receipt(self):
        request, manifest, proof = self.fixture()
        manifest["preparation_run_id"] = 457
        proof["disposable_preparation_run_id"] = 457
        proof["bundles"][0]["run_id"] = 457
        with self.assertRaisesRegex(
            qualify.support.QualificationError, "explicitly created rehearsal"
        ):
            self.authorize(proof, manifest, request)

    def test_receipt_purpose_status_and_creation_are_required(self):
        for field, value in [
            ("purpose", "owner-backup"),
            ("status", "FAILED"),
            ("creation_controller_run_id", 0),
            ("creation_controller_sha", "community"),
            ("creation_controller_sha", "f" * 40),
        ]:
            request, manifest, proof = self.fixture()
            proof[field] = value
            with self.assertRaises(qualify.support.QualificationError):
                self.authorize(proof, manifest, request)

    def test_manifest_source_version_identity_and_attempt_must_match(self):
        for field, value in [
            ("preparation_run_id", 457),
            ("source_sha", "f" * 40),
            ("qualification_sha", "f" * 40),
            ("version", "1.0.5"),
            ("preparation_run_attempt", 2),
        ]:
            request, manifest, proof = self.fixture()
            manifest[field] = value
            with self.assertRaises(qualify.support.QualificationError):
                self.authorize(proof, manifest, request)

    def test_wrong_reviewed_digest_or_extra_bundle_cannot_be_adopted(self):
        request, manifest, proof = self.fixture()
        with self.assertRaises(qualify.support.QualificationError):
            self.authorize(proof, manifest, request, "0" * 64)
        proof["bundles"].append(copy.deepcopy(proof["bundles"][0]))
        with self.assertRaises(qualify.support.QualificationError):
            self.authorize(proof, manifest, request)

    def destroy(self, proof, manifest, request):
        function = getattr(qualify, "destroy_disposable", None)
        self.assertIsNotNone(function, "guarded destructive operation missing")
        report = {"dispatches": [], "runs": [], "bundles": []}
        function(report, request, proof, manifest, "d" * 64)
        return report

    def test_destroy_entry_refuses_owner_before_any_api_call(self):
        request, manifest, proof = self.fixture()
        proof["disposable_preparation_run_id"] = qualify.PROTECTED_OWNER
        manifest["preparation_run_id"] = qualify.PROTECTED_OWNER
        proof["bundles"][0]["run_id"] = qualify.PROTECTED_OWNER
        with patch.object(
            qualify.support,
            "api",
            side_effect=AssertionError("owner mutation or API call"),
        ):
            with self.assertRaisesRegex(
                qualify.support.QualificationError, "protected owner"
            ):
                self.destroy(proof, manifest, request)

    def api_fixture(self, *, latest_attempt=1, uncertain=False):
        calls = []

        def api(endpoint, **kwargs):
            if kwargs.get("method", "GET") != "GET":
                calls.append(endpoint)
                self.assertEqual(
                    endpoint, f"repos/{qualify.support.REPO}/actions/runs/456/rerun"
                )
                if uncertain:
                    raise RuntimeError("response uncertain")
                raise AssertionError("unexpected destructive request")
            if "/runs/900/" in endpoint:
                return {
                    "id": 900,
                    "run_attempt": 1,
                    "head_sha": "c" * 40,
                    "head_branch": "qualification/runtime-release-recovery-20261016",
                    "path": ".github/workflows/runtime-release-recovery-qualification.yml",
                    "event": "push",
                    "status": "completed",
                    "conclusion": "success",
                    "repository": {"full_name": qualify.support.REPO},
                    "head_repository": {"full_name": qualify.support.REPO},
                }
            if "/git/ref/heads/community" in endpoint:
                return {"object": {"sha": "a" * 40}}
            if "/artifacts/700" in endpoint:
                return {
                    "id": 700,
                    "digest": "sha256:" + "e" * 64,
                    "workflow_run": {"id": 456},
                }
            return {
                "id": 456,
                "run_attempt": latest_attempt,
                "head_sha": "a" * 40,
                "head_branch": "community",
                "path": ".github/workflows/runtime-release-prepare.yml",
                "event": "workflow_dispatch",
                "status": "completed",
                "conclusion": "success",
                "repository": {"full_name": qualify.support.REPO},
                "head_repository": {"full_name": qualify.support.REPO},
            }

        return api, calls

    def test_already_rerun_preparation_is_never_posted_again(self):
        request, manifest, proof = self.fixture()
        api, calls = self.api_fixture(latest_attempt=2)
        with patch.object(qualify.support, "api", side_effect=api), patch.object(
            qualify.support, "snapshot"
        ):
            with self.assertRaisesRegex(
                qualify.support.QualificationError, "already rerun"
            ):
                self.destroy(proof, manifest, request)
        self.assertEqual(calls, [])

    def test_uncertain_rerun_response_is_not_retried(self):
        from types import SimpleNamespace

        request, manifest, proof = self.fixture()
        api, calls = self.api_fixture(uncertain=True)
        fake = SimpleNamespace(
            verify_recovery=lambda *args: {
                "original_archive_sha256": "e" * 64,
                "backups": [{"run_id": 201}, {"run_id": 202}],
            }
        )
        with patch.object(qualify, "button", fake, create=True), patch.object(
            qualify.support, "api", side_effect=api
        ), patch.object(qualify.support, "snapshot"):
            function = getattr(qualify, "destroy_disposable", None)
            self.assertIsNotNone(function, "guarded destructive operation missing")
            report = {"dispatches": [], "runs": [], "bundles": []}
            with self.assertRaisesRegex(RuntimeError, "response uncertain"):
                function(report, request, proof, manifest, "d" * 64)
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            report["destructive_operation"]["outcome"], "request uncertain"
        )

    def test_publication_operation_is_rejected_before_any_api_call(self):
        with patch.object(
            qualify.Path, "read_text", return_value='{"operation":"publish"}'
        ), patch.object(
            qualify.support, "api", side_effect=AssertionError("unexpected API call")
        ):
            with self.assertRaisesRegex(
                qualify.support.QualificationError,
                "unsupported qualification operation",
            ):
                qualify.main()


if __name__ == "__main__":
    unittest.main()
