"""An incompatible Actions worker must fail instead of losing managed parameters."""

import builtins
from importlib import metadata

import pytest

from actions.server._preload_actions.preload_actions_server_main import MessagesHandler


def test_old_actions_core_worker_reports_required_upgrade(monkeypatch):
    original_import = builtins.__import__

    def import_without_integration(name, *args, **kwargs):
        if name == "actions.server_integration":
            raise ImportError("published Core 1.0.1 has no integration module")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_integration)
    monkeypatch.setattr(metadata, "version", lambda name: "1.0.1")
    handler = MessagesHandler.__new__(MessagesHandler)
    with pytest.raises(RuntimeError, match=r"actions-core >=1\.0\.2.*1\.0\.1"):
        handler._plugin_manager_kwargs({"request": {"headers": {}, "cookies": {}}})
