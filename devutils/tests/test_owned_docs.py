"""Behavior contracts for the owned generator and custom docstring rules."""

import sys
from types import ModuleType

import pytest

from devutils.owned_docs import generate_docs
from devutils.owned_docs.validation import section_errors


def test_namespace_exports_and_root(tmp_path, monkeypatch):
    module = ModuleType("owned_docs_fixture")
    module.__path__ = []
    module.__all__ = ["PublicValue"]

    class PublicValue:
        """Public re-exported class."""

    module.PublicValue = PublicValue
    monkeypatch.setitem(sys.modules, module.__name__, module)
    generate_docs(
        [module.__name__],
        output_path=str(tmp_path),
        watermark=False,
        overview_file="README.md",
    )
    assert "PublicValue" in (tmp_path / "owned_docs_fixture.md").read_text()
    assert (tmp_path / "README.md").exists()


@pytest.mark.parametrize(
    "body,expected",
    [
        ("Returns:\n        Value.\n\n    Args:\n        value: Value.", ["D420"]),
        (
            "Args:\n        value:\n            Value.\n\n    Returns:\n        Value.",
            ["D421"],
        ),
        ("Args:\n        value: Value.\n\n    Returns:\n        Value.", []),
        ("Raises:\n        ValueError:\n            Bad value.", ["D421"]),
    ],
)
def test_custom_validation(body, expected):
    source = (
        'def use(value):\n    """Use value.\n\n    '
        + body
        + '\n    """\n    return value\n'
    )
    assert [code for code, _ in section_errors(source)] == expected


def test_discovery_failure_is_not_silenced(tmp_path, monkeypatch):
    from devutils.owned_docs import generation

    package = tmp_path / "owned_broken_fixture"
    package.mkdir()
    (package / "__init__.py").write_text('"""Owned package."""')
    (package / "child.py").write_text('"""Owned child."""')
    monkeypatch.syspath_prepend(str(tmp_path))

    def broken(*args):
        raise ImportError("synthetic discovery failure")

    monkeypatch.setattr(generation, "get_module", broken)
    with pytest.raises(RuntimeError, match="owned_broken_fixture.child"):
        generate_docs(
            ["owned_broken_fixture"],
            output_path=str(tmp_path / "docs"),
            src_root_path=str(tmp_path),
            watermark=False,
        )
    sys.modules.pop("owned_broken_fixture", None)


def test_validation_entrypoint_uses_official_and_owned_rules(tmp_path):
    from devutils.owned_docs.validation import validate_path

    path = tmp_path / "public.py"
    path.write_text(
        'def use(value):\n    """Use value.\n\n    Returns:\n        Value.\n\n    Args:\n        value: Value.\n    """\n    return value\n'
    )
    assert any("D420" in error for error in validate_path(str(path)))
    with pytest.raises(ValueError, match="D420"):
        generate_docs(
            [str(path)], validate=True, output_path=str(tmp_path / "not-created")
        )
    assert not (tmp_path / "not-created").exists()


def test_import_validation_does_not_expand_to_package_descendants(
    tmp_path, monkeypatch
):
    from devutils.owned_docs.validation import validate_path

    package = tmp_path / "owned_validation_scope"
    package.mkdir()
    (package / "__init__.py").write_text('"""Owned package."""\n')
    (package / "child.py").write_text(
        'def broken():\n    """\n    Missing first-line summary.\n    """\n'
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    assert validate_path("owned_validation_scope") == []
    assert any("D212" in error for error in validate_path(str(package)))
