"""The starter action runs offline with owned Core and the standard library."""

import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "text,expected",
    [("hello world", 2), ("", 0), ("one\n two\tthree", 3), ("  café 世界  ", 2)],
)
def test_count_words(text: str, expected: int) -> None:
    path = Path(__file__).resolve().parents[1] / "text_actions.py"
    spec = importlib.util.spec_from_file_location("basic_text_actions", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.count_words(text).result == expected


def test_template_dependencies_are_owned_and_minimal() -> None:
    manifest = (Path(__file__).resolve().parents[1] / "package.yaml").read_text()
    assert "actions-core=" in manifest
    assert "robocorp-browser" not in manifest
    assert "wikipedia" not in manifest
