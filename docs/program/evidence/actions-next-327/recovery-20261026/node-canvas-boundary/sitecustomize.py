"""Test-only source transformer for one bounded Canvas MCP diagnosis."""
import importlib.abc
import importlib.machinery
import os


def patch(fullname, source):
    helper = (
        "\n\ndef _codex_canvas_probe(event, value):\n"
        "    import json as _probe_json, os as _probe_os\n"
        "    _probe_target = _probe_os.environ.get('ACTIONS_CANVAS_PROBE_EVENTS')\n"
        "    if _probe_target:\n"
        "        with open(_probe_target, 'a', encoding='utf-8') as _probe_stream:\n"
        "            _probe_stream.write(_probe_json.dumps({'event': event, 'value': value}, separators=(',', ':')) + '\\n')\n"
    )
    if fullname.endswith(".mcp"):
        marker = "        caller = await self.principal(ctx)\n        try:\n"
        assert source.count(marker) == 1
        source = source.replace(
            marker,
            "        caller = await self.principal(ctx)\n"
            "        if name == 'canvas_get':\n"
            "            _codex_canvas_probe('authenticated_caller_present', caller is not None)\n"
            "        try:\n",
        )
        marker = "            # Domain authorization, exact app/revision/binding checks and request\n"
        assert source.count(marker) == 1
        source = source.replace(
            marker,
            "            if name == 'canvas_get':\n"
            "                _codex_canvas_probe('canvas_port_entered', True)\n"
            + marker,
        )
        marker = "        except Exception:\n            # Do not expose provider exceptions, source paths or credentials.\n"
        assert source.count(marker) == 1
        source = source.replace(
            marker,
            "        except Exception as exc:\n"
            "            if name == 'canvas_get':\n"
            "                _codex_canvas_probe('caught_exception_class', type(exc).__name__)\n"
            "            # Do not expose provider exceptions, source paths or credentials.\n",
        )
        marker = "            reply = await self.port.call(caller, name, inputs)\n"
        assert source.count(marker) == 1
        source = source.replace(
            marker,
            marker
            + "            if name == 'canvas_get':\n"
            "                _codex_canvas_probe('canvas_port_returned', True)\n",
        )
    elif fullname.endswith(".authoring"):
        marker = (
            '        if name == "canvas_get":\n'
            '            application_id = _application_id(inputs.get("appId"))\n'
        )
        assert source.count(marker) == 1
        source = source.replace(
            marker,
            marker + "            _codex_canvas_probe('app_id_parsed', True)\n",
        )
        marker = (
            "                application_id=application_id,\n"
            "            )\n"
            "            selected_revision: AuthoringRevision | None\n"
        )
        assert source.count(marker) == 1
        source = source.replace(
            marker,
            "                application_id=application_id,\n"
            "            )\n"
            "            _codex_canvas_probe('read_application_passed', True)\n"
            "            selected_revision: AuthoringRevision | None\n",
        )
        marker = (
            "            if selected_revision is None:\n"
            "                raise AuthoringAccessDenied(\"Canvas application is unavailable\")\n"
        )
        assert source.count(marker) == 1
        source = source.replace(
            marker,
            "            _codex_canvas_probe('latest_revision_found', selected_revision is not None)\n"
            + marker,
        )
        marker = "            _require_revision_owner(selected_revision, application_id, workspace_id)\n"
        assert source.count(marker) == 1
        source = source.replace(
            marker,
            marker + "            _codex_canvas_probe('revision_owner_passed', True)\n",
        )
    else:
        return source
    future = "from __future__ import annotations\n"
    assert source.count(future) == 1
    return source.replace(future, future + helper, 1)


class _Loader:
    def __init__(self, wrapped, fullname):
        self.wrapped = wrapped
        self.fullname = fullname

    def create_module(self, spec):
        creator = getattr(self.wrapped, "create_module", None)
        return creator(spec) if creator else None

    def exec_module(self, module):
        source = self.wrapped.get_data(self.wrapped.path).decode("utf-8")
        exec(compile(patch(self.fullname, source), self.wrapped.path, "exec"), module.__dict__)


class _Finder(importlib.abc.MetaPathFinder):
    targets = {"actions.server.foundry.mcp", "actions.server.foundry.authoring"}

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.targets:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is not None and isinstance(spec.loader, importlib.machinery.SourceFileLoader):
            spec.loader = _Loader(spec.loader, fullname)
        return spec


if os.environ.get("ACTIONS_CANVAS_PROBE_ENABLE") == "1":
    import sys

    sys.meta_path.insert(0, _Finder())
