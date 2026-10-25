import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def producer(monkeypatch):
    scripts = Path(__file__).parents[2] / "action_server/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "producer_327", scripts / "produce_consumer_sbom_327.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_explicit_target_and_validated_reproducible_format(producer, tmp_path):
    command = producer.producer_command(
        tmp_path / "consumer/python", tmp_path / "result.json"
    )
    assert command[2:5] == [
        "cyclonedx_py",
        "environment",
        str(tmp_path / "consumer/python"),
    ]
    assert command[command.index("--spec-version") + 1] == "1.6"
    assert command[command.index("--output-format") + 1] == "JSON"
    assert "--validate" in command and "--output-reproducible" in command
    assert "--no-validate" not in command and "--short-PURLs" not in command


def test_existing_output_is_never_overwritten(producer, tmp_path):
    marker = tmp_path / "retain"
    marker.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        producer.produce(SimpleNamespace(output_dir=tmp_path))
    assert marker.read_bytes() == b"original"
    assert not (tmp_path / "receipt.json").exists()


def test_wrong_producer_version_retains_failure_before_execution(
    producer, tmp_path, monkeypatch
):
    monkeypatch.setattr(producer.importlib.metadata, "version", lambda name: "0.0.0")

    def forbidden(*args):
        pytest.fail("wrong producer must not start child processes")

    monkeypatch.setattr(producer, "run", forbidden)
    output = tmp_path / "new"
    with pytest.raises(ValueError, match="producer version"):
        producer.produce(SimpleNamespace(output_dir=output))
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["result"] == "failed"
    assert "producer version" in receipt["error"]
