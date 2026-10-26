"""Platform and external-fixture admission boundaries for shared CI fixtures."""

from types import SimpleNamespace

import pytest
from action_server_tests import test_knowledge_execution, test_sealed_postgres
from action_server_tests.run_outputs import test_service


def test_shared_output_store_skips_when_platform_is_not_linux(monkeypatch, tmp_path):
    monkeypatch.setattr(test_service, "sys", SimpleNamespace(platform="darwin"))

    with pytest.raises(pytest.skip.Exception, match="Linux private output-provider"):
        next(test_service.store.__wrapped__(tmp_path))


@pytest.mark.parametrize(
    ("strict", "outcome"),
    [
        (False, pytest.skip.Exception),
        (True, pytest.fail.Exception),
    ],
)
def test_tls_postgres_distinguishes_missing_docker_from_strict_requirement(
    monkeypatch, tmp_path_factory, strict, outcome
):
    monkeypatch.setattr(test_sealed_postgres.shutil, "which", lambda _: None)
    if strict:
        monkeypatch.setenv("ACTIONS_REQUIRE_INVOICE_PROVIDERS", "1")
    else:
        monkeypatch.delenv("ACTIONS_REQUIRE_INVOICE_PROVIDERS", raising=False)

    with pytest.raises(outcome, match="Docker CLI required"):
        next(test_sealed_postgres.tls_postgres.__wrapped__(tmp_path_factory))


@pytest.mark.parametrize(
    ("strict", "outcome"),
    [
        (False, pytest.skip.Exception),
        (True, pytest.fail.Exception),
    ],
)
def test_knowledge_postgres_distinguishes_missing_dsn_from_strict_requirement(
    monkeypatch, tmp_path, strict, outcome
):
    monkeypatch.delenv("ACTIONS_INVOICE_TEST_POSTGRES", raising=False)
    if strict:
        monkeypatch.setenv("ACTIONS_REQUIRE_INVOICE_PROVIDERS", "1")
    else:
        monkeypatch.delenv("ACTIONS_REQUIRE_INVOICE_PROVIDERS", raising=False)
    request = SimpleNamespace(param="postgresql")

    with pytest.raises(outcome, match="owned PostgreSQL fixture"):
        next(test_knowledge_execution.versions.__wrapped__(request, tmp_path))
