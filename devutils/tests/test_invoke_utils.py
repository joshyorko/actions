from pathlib import Path

import tomlkit

from devutils.invoke_utils import build_common_tasks, collect_deps_pyprojects


def test_collects_neutral_helper_without_legacy_directory(tmp_path: Path):
    consumer = tmp_path / "actions"
    helper = tmp_path / "actions-http-helper"
    consumer.mkdir()
    helper.mkdir()
    (consumer / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "actions"\nversion = "1.0.0"\n'
        "[tool.poetry.dependencies]\n"
        'actions-http-helper = "^1.0.0"\n'
    )
    (helper / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "actions-http-helper"\nversion = "1.0.0"\n'
        '[tool.poetry.dependencies]\npython = ">=3.10"\n'
    )

    discovered = list(collect_deps_pyprojects(consumer / "pyproject.toml"))

    assert discovered == [helper / "pyproject.toml"]
    assert {path.name for path in tmp_path.iterdir()} == {
        "actions",
        "actions-http-helper",
    }


def test_develop_mode_substitutes_neutral_internal_helper(tmp_path: Path):
    consumer = tmp_path / "consumer"
    helper = tmp_path / "actions-http-helper"
    consumer.mkdir()
    helper.mkdir()
    (consumer / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "consumer"\nversion = "1.0.0"\n'
        "[tool.poetry.dependencies]\n"
        'actions-http-helper = "^1.0.0"\n'
    )
    (consumer / "poetry.lock").write_text("lock")
    (helper / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "actions-http-helper"\nversion = "1.0.0"\n'
        '[tool.poetry.dependencies]\npython = ">=3.10"\n'
    )
    (helper / "poetry.lock").write_text("lock")

    tasks = build_common_tasks(consumer, "consumer")
    with tasks["mark_as_develop_mode"](all_packages=True):
        contents = tomlkit.loads((consumer / "pyproject.toml").read_text())
        assert contents["tool"]["poetry"]["dependencies"]["actions-http-helper"] == {
            "path": "../actions-http-helper/",
            "develop": True,
        }

    assert 'actions-http-helper = "^1.0.0"' in (consumer / "pyproject.toml").read_text()
