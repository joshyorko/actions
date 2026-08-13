from pathlib import Path

import tomllib


ROOT = Path(__file__).parents[2]


def test_actions_core_owns_public_namespace_and_absorbed_mcp():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert metadata["tool"]["poetry"]["name"] == "actions-core"
    assert metadata["tool"]["poetry"]["version"] == "1.0.0"
    assert metadata["tool"]["poetry"]["packages"] == [{"include": "actions", "from": "src"}]

    from actions import action
    from actions.mcp import tool

    assert callable(action)
    assert callable(tool)


def test_work_items_does_not_ship_root_actions_initializer():
    work_items_root = ROOT.parent / "work-items" / "src" / "actions"

    assert not (work_items_root / "__init__.py").exists()
