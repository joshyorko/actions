"""Owned service-free ordering witness; no native Runtime or filesystem watcher."""
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, '/workspace/engineering/pr306/action_server/tests')
from action_server_tests.mcp.test_alias_history import _action
from action_server_tests.test_cli_mcp_resource_history import (
    _TRANSITIONS, _assert_mcp_error, _old_owner_value, _old_template,
    _read_text, _resource_surface, _route_is_listed, _write_a_routes, _write_b_routes,
)


def full_handoff(client):
    surface = _resource_surface(client)
    assert all('result' in response for response in surface.values())
    resources = surface['resources/list']['result'].get('resources')
    templates = surface['resources/templates/list']['result'].get('resourceTemplates')
    assert resources is not None and templates is not None
    direct = {item['uri'] for item in resources}
    templated = {item['uriTemplate'] for item in templates}
    return all(
        (transition['old_uri'] if transition['old_kind'] == 'direct' else _old_template(index))
        not in (direct if transition['old_kind'] == 'direct' else templated)
        and transition['candidate_uri'] in
        (templated if transition['candidate_kind'] == 'template' else direct)
        for index, transition in enumerate(_TRANSITIONS)
    )


def test_b_publication_does_not_prove_a_removal(monkeypatch):
    from actions.server import _actions_run, _app
    from actions.server._api_action_routes import _ActionRoutes
    from actions.server._models import Action, ActionPackage, create_db

    app = _app._CustomFastAPI()
    monkeypatch.setattr(_app, 'get_app', lambda: app)
    invoked = []
    values = {}

    def generate(action_package, action, display_name, **kwargs):
        async def execute(**kwargs):
            invoked.append(action.id)
            return values[action.id]
        return execute, execute, {}

    monkeypatch.setattr(_actions_run, 'generate_func_from_action', generate)
    routes = _ActionRoutes(whitelist=None, endpoint_dependencies=[])
    routes.setup_mcp_server(None)
    with create_db(':memory:') as db, TestClient(app, base_url='http://localhost:8080') as client:
        def insert(package, route_set):
            db.insert(ActionPackage(package, package, '.', 'hash', '{}'))
            for name, uri, value, parameter in route_set:
                action = _action(package, name, options={'kind': 'resource', 'uri': uri})
                db.insert(action)
                if package == 'package_a' and name.startswith('owner_a_claim_'):
                    values[action.id] = _old_owner_value(_TRANSITIONS[int(name.rsplit('_',1)[1])], 'v2')
                else:
                    values[action.id] = value

        with db.transaction():
            insert('package_a', _write_a_routes(revision='v2', include_claims=True))
            routes.register_actions()
        assert all(_read_text(client, t['old_uri']) == _old_owner_value(t, 'v2') for t in _TRANSITIONS)
        # Deliberately publish B while all A declarations remain active.
        with db.transaction():
            insert('package_b', _write_b_routes(phase='candidate'))
            routes.register_actions()
        listed = [_route_is_listed(client, t['candidate_uri'], template=t['candidate_kind']=='template') for t in _TRANSITIONS]
        assert all(listed)
        assert _read_text(client, _TRANSITIONS[0]['old_uri']) == _old_owner_value(_TRANSITIONS[0], 'v2')
        barrier = all(listed) if os.environ.get('HANDOFF_PROBE_MODE') == 'legacy' else full_handoff(client)
        assert barrier is False, 'B-only presence incorrectly admits an incomplete handoff'
        with db.transaction():
            for action in db.all(Action):
                if action.action_package_id == 'package_a' and action.name.startswith('owner_a_claim_'):
                    db.update_by_id(Action, action.id, {'enabled':False})
            routes.register_actions()
        assert full_handoff(client) is True
        before = list(invoked)
        for transition in _TRANSITIONS:
            _assert_mcp_error(client, transition['old_uri'], 'conflicting historical owner')
            assert invoked == before
        for transition in _TRANSITIONS:
            if transition['other_candidate_uri']:
                assert _read_text(client, transition['other_candidate_uri']).startswith('owner-b:candidate:')
        assert _read_text(client, 'safe://owner-b/value') == 'owner-b:safe'
        assert _read_text(client, 'control://same/value') == 'owner-a:control-direct'
        for package, prefix, present in [('package_a', 'owner_a_claim_', True), ('package_b', 'owner_b_claim_', False)]:
            actions = [a for a in db.all(Action) if a.action_package_id == package and a.name.startswith(prefix)]
            assert len(actions) == 3
            for action in actions:
                with db.transaction():
                    db.update_by_id(Action, action.id, {'enabled':present})
                    routes.register_actions()
                assert full_handoff(client) is False
                with db.transaction():
                    db.update_by_id(Action, action.id, {'enabled':not present})
                    routes.register_actions()
                assert full_handoff(client) is True
