import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "qualify", Path(__file__).with_name("qualify_runtime_release_button.py")
)
qualify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualify)


class DispatchContract(unittest.TestCase):
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
