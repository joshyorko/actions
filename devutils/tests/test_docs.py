import sys
from types import ModuleType

import pytest

from devutils.docs import normalize_generic_alias_docs


def test_generic_alias_docs_match_python_310_and_312_renderings(tmp_path, monkeypatch):
    module = ModuleType("alias_fixture")
    module.__all__ = ["Row"]
    module.Row = list[str]
    monkeypatch.setitem(sys.modules, "alias_fixture", module)
    canonical = "# Module alias_fixture\n\n# Variables\n\n- **Row**\n- **RowValue**\n\n# Class `Table`\n\nA real class.\n"
    old = (
        canonical.replace("- **Row**\n", "")
        + "\n# Class `list`\n\nBuilt-in mutable sequence.\n\nIf no argument is given, the constructor creates a new empty list.\n"
    )
    module_file = tmp_path / "alias_fixture.md"
    overview_file = tmp_path / "README.md"
    overview = "# API\n\n- [`alias_fixture.Table`](./alias_fixture.md#class-table)\n"
    for rendering in (old, canonical):
        module_file.write_text(rendering)
        overview_file.write_text(
            overview
            + "- [`builtins.list`](./builtins.md#class-list): Built-in mutable sequence.\n"
        )
        normalize_generic_alias_docs(tmp_path, "alias_fixture")
        assert module_file.read_text() == canonical
        assert overview_file.read_text() == overview
        normalize_generic_alias_docs(tmp_path, "alias_fixture")
        assert module_file.read_text() == canonical


@pytest.mark.parametrize("heading", ["Exceptions", "Enums", "Functions"])
def test_alias_normalization_preserves_following_top_level_sections(
    tmp_path, monkeypatch, heading
):
    module = ModuleType("alias_fixture")
    module.__all__ = ["Row"]
    module.Row = list[str]
    monkeypatch.setitem(sys.modules, "alias_fixture", module)
    before = "# Variables\n\n- **Row**\n\n"
    after = f"# {heading}\n\nPublic API content.\n"
    (tmp_path / "alias_fixture.md").write_text(
        before + "# Class `list`\n\nBuilt-in mutable sequence.\n\n" + after
    )
    (tmp_path / "README.md").write_text("# API\n")
    normalize_generic_alias_docs(tmp_path, "alias_fixture")
    assert (tmp_path / "alias_fixture.md").read_text() == before + after
