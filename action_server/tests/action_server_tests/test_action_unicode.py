import json
import os

import pytest

from sema4ai.action_server._selftest import ActionServerClient, ActionServerProcess


@pytest.mark.integration_test
def test_action_unicode(
    action_server_process: ActionServerProcess,
    client: ActionServerClient,
    datadir,
    str_regression,
) -> None:
    from action_server_tests.fixtures import (
        BUILD_ENV_IN_TESTS_TIMEOUT,
        fix_openapi_json,
    )

    dir_contents = [x for x in os.listdir(datadir) if not x.startswith("test")]
    assert len(dir_contents) == 1
    action_server_process.start(
        db_file="server.db",
        cwd=str(os.path.join(str(datadir), dir_contents[0])),
        actions_sync=True,
        timeout=BUILD_ENV_IN_TESTS_TIMEOUT,
        lint=False,
    )
    str_regression.check(
        json.dumps(fix_openapi_json(json.loads(client.get_openapi_json())), indent=4)
    )

    found = client.post_get_str(
        "api/actions/acao-pkg/unicode-acao/run",
        {"ação": "Foo"},
    )
    assert found == '"Foo"'


def test_slugify():
    from sema4ai.action_server._slugify import slugify

    assert slugify("ação", allow_unicode=True) == "ação"
    assert slugify("ação", allow_unicode=False) == "acao"
    assert slugify("ação /?*Σ 22", allow_unicode=False) == "acao-22"
