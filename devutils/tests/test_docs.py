import sys
from types import ModuleType

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
