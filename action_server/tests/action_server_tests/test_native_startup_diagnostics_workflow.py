import importlib.util
from pathlib import Path


def test_windows_diagnostics_survive_failed_integration_without_changing_command():
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "diagnostic_workflow_generator", root / ".github/workflows/_gen_workflows.py"
    )
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    steps = generator.ActionServerTests().run_tests()
    integration = next(
        step for step in steps if step.get("name") == "Test (integration)"
    )
    assert (
        integration["run"]
        == f"{generator.run_in_env}poetry run inv test-binary --jobs 0"
    )
    assert integration["env"]["ACTIONS_NATIVE_STARTUP_DIAGNOSTICS_DIR"] == (
        "${{ matrix.os == 'windows-2022' && format('{0}/native-startup-diagnostics', runner.temp) || '' }}"
    )
    upload = steps[-1]
    assert upload["if"] == "always() && matrix.os == 'windows-2022'"
    assert (
        upload["with"]["path"] == "${{ runner.temp }}/native-startup-diagnostics/*.json"
    )
    assert upload["with"]["retention-days"] == 7
