"""Regression coverage for owned documentation validation path selection."""

from pathlib import Path

from devutils.owned_docs.validation import validate_path


def _write(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_directory_under_temp_runs_official_and_owned_rules(tmp_path):
    root = tmp_path / "external_temp" / "_temp" / "fixture"
    _write(
        root / "public.py",
        'def use(value):\n    """Use value.\n\n    Returns:\n        Value.\n\n    Args:\n        value: Value.\n    """\n    return value\n',
    )
    _write(
        root / "child.py",
        'def broken():\n    """\n    Missing first-line summary.\n    """\n',
    )

    errors = validate_path(str(root))

    assert any("D420" in error for error in errors)
    assert any("D212" in error for error in errors)


def test_explicit_file_scope_and_nested_private_filter_under_temp(tmp_path):
    root = tmp_path / "external_temp" / "_temp" / "fixture"
    public = root / "public.py"
    _write(public, '"""Public module."""\n')
    _write(
        root / "child.py",
        'def broken():\n    """\n    Missing first-line summary.\n    """\n',
    )
    private = root / "_private" / "hidden.py"
    _write(
        private,
        'def broken():\n    """\n    Missing first-line summary.\n    """\n',
    )

    assert validate_path(str(public)) == []
    errors = validate_path(str(root))

    assert sum("D212" in error for error in errors) == 1
    assert all(str(private) not in error for error in errors)
