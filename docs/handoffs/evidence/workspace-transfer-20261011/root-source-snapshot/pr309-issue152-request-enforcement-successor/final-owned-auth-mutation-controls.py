"""Owned in-memory bypass controls only; all production bytes stay unchanged."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.authentication import AuthCredentials, SimpleUser

ROOT = Path('/workspace/engineering/pr309')
OUT = Path('/workspace/engineering/pr309-issue152-request-enforcement-successor')
TEST = 'tests/action_server_tests/test_auth_route_enforcement.py'
ROWS = ('secrets-write', 'work-item-create', 'mounted-artifact')
test_source_before = hashlib.sha256((ROOT / 'action_server' / TEST).read_bytes()).hexdigest()
from actions.server._api_action_routes import APIKeyAuthBackend
from actions.server._browser_session import BrowserSessions
authenticate_before, authorized_before = APIKeyAuthBackend.authenticate, BrowserSessions.authorized
records = []
failures = []
production_before = {}
for path in subprocess.check_output(['git', 'ls-files', 'action_server/src'], cwd=ROOT, text=True).splitlines():
    production_before[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


class OwnedMutation:
    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_call(self, item):
        from actions.server._api_action_routes import APIKeyAuthBackend
        from actions.server._browser_session import BrowserSessions

        assert item.callspec.params['credential'] == 'wrong'
        row = item.callspec.params['row']
        assert row in ROWS
        runtime = item.funcargs['assembled_runtime']
        original_request = TestClient.request
        with pytest.MonkeyPatch.context() as patch:
            if row == 'mounted-artifact':
                async def bypass_backend(self, conn):
                    return AuthCredentials([]), SimpleUser('owned-control')
                patch.setattr(APIKeyAuthBackend, 'authenticate', bypass_backend)
            else:
                patch.setattr(BrowserSessions, 'authorized', lambda self, scope: True)

            def recorded_request(client, *args, **kwargs):
                before = item.module._snapshot(runtime)
                response = original_request(client, *args, **kwargs)
                after = item.module._snapshot(runtime)
                records.append({
                    'row': row,
                    'actual_status': response.status_code,
                    'changed_categories': [name for name in before if before[name] != after[name]],
                    'owned_artifact_exact_bytes_returned': response.content == item.module.PAYLOAD,
                    'response_bytes_sha256': hashlib.sha256(response.content).hexdigest(),
                    'only_synthetic_owned_data': True,
                })
                return response

            patch.setattr(TestClient, 'request', recorded_request)
            try:
                return (yield)
            finally:
                pass

    def pytest_runtest_logreport(self, report):
        if report.when == 'call' and report.failed:
            assert 'AssertionError' in str(report.longrepr)
            failures.append(report.nodeid)


result = pytest.main(['-n', '0', '-q', *[TEST + '::test_real_assembled_credential_matrix[wrong-' + row + ']' for row in ROWS]], plugins=[OwnedMutation()])
assert result == 1 and len(failures) == 3 and len(records) == 3, (result, failures, records)
by_row = {record['row']: record for record in records}
assert by_row['secrets-write']['actual_status'] == 200
assert by_row['secrets-write']['changed_categories'] == ['secrets']
assert by_row['work-item-create']['actual_status'] == 200
assert set(by_row['work-item-create']['changed_categories']) == {'logical_sql', 'directories'}
assert by_row['mounted-artifact']['actual_status'] == 200
assert by_row['mounted-artifact']['owned_artifact_exact_bytes_returned'] is True
for path, expected in production_before.items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
from actions.server._api_action_routes import APIKeyAuthBackend
from actions.server._browser_session import BrowserSessions
assert APIKeyAuthBackend.authenticate is authenticate_before
assert BrowserSessions.authorized is authorized_before
assert hashlib.sha256((ROOT / 'action_server' / TEST).read_bytes()).hexdigest() == test_source_before
(OUT / 'final-owned-auth-mutation-RED-receipt.json').write_text(json.dumps({'status': 'EXPECTED_THREE_RED_ASSERTIONS_WITH_REAL_OWNED_MUTATION_AND_EXACT_LEAK', 'records': records, 'test_source_before_after_sha256': test_source_before, 'failed_case_ids': failures, 'all_production_files_unchanged_count': len(production_before), 'auth_methods_restored': True, 'native_provider_or_external_data': 'NONE'}, indent=2) + '\n')
print('EXPECTED_RED_AND_RESTORATION_PROVED')
