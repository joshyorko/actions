from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import tomlkit
import pytest
from invoke import Context

from devutils.invoke_utils import (
    REPOSITORY_URL,
    build_common_tasks,
    collect_deps_pyprojects,
    get_tag,
)


def test_common_quality_tasks_use_current_ruff_subcommands(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    context = Context()
    context.run = Mock()
    tasks = build_common_tasks(tmp_path, "example")

    tasks["lint"](context)
    tasks["pretty"](context)

    commands = [call.args[0] for call in context.run.call_args_list]
    assert commands[0] == "poetry run ruff check src tests"
    assert "poetry run ruff check --fix src tests" in commands


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


def test_make_release_rejects_master_before_any_other_release_operation(tmp_path):
    task = build_common_tasks(tmp_path, "actions", tag_prefix="actions-core")[
        "make_release"
    ]
    context = Context()
    context.run = Mock(return_value=SimpleNamespace(stdout="master\n"))

    with pytest.raises(SystemExit) as error:
        task(context)

    assert error.value.code == 1
    assert [call.args[0] for call in context.run.call_args_list] == [
        "git rev-parse --abbrev-ref HEAD"
    ]


def test_make_release_rejects_noncanonical_community_repository_before_tagging(
    tmp_path,
):
    task = build_common_tasks(tmp_path, "actions", tag_prefix="actions-core")[
        "make_release"
    ]
    context = Context()
    context.run = Mock(
        side_effect=[
            SimpleNamespace(stdout="community\n"),
            SimpleNamespace(stdout="https://github.com/fork/actions.git\n"),
        ]
    )

    with pytest.raises(SystemExit) as error:
        task(context)

    assert error.value.code == 1
    assert [call.args[0] for call in context.run.call_args_list] == [
        "git rev-parse --abbrev-ref HEAD",
        "git remote get-url origin",
    ]


def test_get_tag_fails_when_release_tags_exist_but_none_is_reachable(monkeypatch):
    results = iter(
        [
            SimpleNamespace(
                returncode=128,
                stdout="",
                stderr="fatal: No names found, cannot describe anything.\n",
            ),
            SimpleNamespace(
                returncode=0,
                stdout="actions-core-1.0.1\n",
                stderr="",
            ),
        ]
    )
    monkeypatch.setattr(
        "devutils.invoke_utils.subprocess.run", lambda *a, **k: next(results)
    )

    with pytest.raises(RuntimeError, match="release tag.*not reachable"):
        get_tag("actions-core")


def test_make_release_rejects_invalid_module_version_before_creating_tag(
    tmp_path, monkeypatch
):
    task = build_common_tasks(tmp_path, "actions", tag_prefix="actions-core")[
        "make_release"
    ]
    commands = iter(
        [
            SimpleNamespace(stdout="community\n"),
            SimpleNamespace(stdout="https://github.com/joshyorko/actions.git\n"),
            SimpleNamespace(stdout=""),
            SimpleNamespace(stdout=""),
            SimpleNamespace(stdout="1.0.2-rc1\n"),
        ]
    )
    context = Context()
    context.run = Mock(side_effect=lambda *args, **kwargs: next(commands))
    monkeypatch.setattr(
        "devutils.invoke_utils.get_tag", lambda prefix: "actions-core-1.0.1"
    )

    with pytest.raises(SystemExit) as error:
        task(context)

    assert error.value.code == 1
    assert not any(
        "git tag" in call.args[0] or "git push" in call.args[0]
        for call in context.run.call_args_list
    )


def test_make_release_rejects_already_existing_current_tag(tmp_path, monkeypatch):
    task = build_common_tasks(tmp_path, "actions", tag_prefix="actions-core")[
        "make_release"
    ]
    responses = iter(
        [
            SimpleNamespace(stdout="community\n"),
            SimpleNamespace(stdout="git@github.com:joshyorko/actions.git\n"),
            SimpleNamespace(stdout=""),
            SimpleNamespace(stdout=""),
            SimpleNamespace(stdout="1.0.2\n"),
            SimpleNamespace(stdout="actions-core-1.0.2\n"),
        ]
    )
    context = Context()
    context.run = Mock(side_effect=lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(
        "devutils.invoke_utils.get_tag", lambda prefix: "actions-core-1.0.1"
    )

    with pytest.raises(SystemExit) as error:
        task(context)

    assert error.value.code == 1
    commands = [call.args[0] for call in context.run.call_args_list]
    assert "git tag --list actions-core-1.0.2" in commands
    assert not any(command.startswith("git tag -a") for command in commands)
    assert not any(command.startswith("git push") for command in commands)


def test_make_release_tags_only_a_valid_community_commit(tmp_path, monkeypatch):
    task = build_common_tasks(tmp_path, "actions", tag_prefix="actions-core")[
        "make_release"
    ]
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if command == "git rev-parse --abbrev-ref HEAD":
            stdout = "community\n"
        elif command == "git remote get-url origin":
            stdout = "https://github.com/joshyorko/actions.git\n"
        elif (
            command
            == 'poetry run python -c "import actions; print(actions.__version__)"'
        ):
            stdout = "1.0.2\n"
        else:
            stdout = ""
        return SimpleNamespace(stdout=stdout)

    context = Context()
    context.run = Mock(side_effect=run)
    monkeypatch.setattr(
        "devutils.invoke_utils.get_tag", lambda prefix: "actions-core-1.0.1"
    )

    task(context)

    assert commands[:4] == [
        "git rev-parse --abbrev-ref HEAD",
        "git remote get-url origin",
        "git fetch --no-tags origin community:refs/remotes/origin/community",
        "git merge-base --is-ancestor HEAD origin/community",
    ]
    assert commands[-3:] == [
        "git tag --list actions-core-1.0.2",
        'git tag -a actions-core-1.0.2 -m "Release 1.0.2 for actions"',
        "git push origin actions-core-1.0.2",
    ]


def test_make_release_does_not_tag_commit_outside_community_ancestry(
    tmp_path, monkeypatch
):
    task = build_common_tasks(tmp_path, "actions", tag_prefix="actions-core")[
        "make_release"
    ]
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if command == "git rev-parse --abbrev-ref HEAD":
            return SimpleNamespace(stdout="community\n")
        if command == "git remote get-url origin":
            return SimpleNamespace(stdout="git@github.com:joshyorko/actions.git\n")
        if command == "git merge-base --is-ancestor HEAD origin/community":
            raise RuntimeError("HEAD is not an ancestor")
        return SimpleNamespace(stdout="")

    context = Context()
    context.run = Mock(side_effect=run)

    with pytest.raises(SystemExit) as error:
        task(context)

    assert error.value.code == 1
    assert not any(
        "git tag" in command or "git push" in command for command in commands
    )


def test_api_doc_source_links_target_maintained_community_source():
    assert REPOSITORY_URL == "https://github.com/joshyorko/actions/blob/community/"
