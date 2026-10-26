"""Platform and external-fixture admission boundaries for shared CI fixtures."""

from types import SimpleNamespace

import pytest
from action_server_tests import (
    test_invoice_review,
    test_knowledge_execution,
    test_local_provider_setup,
    test_provider_catalog,
    test_sealed_postgres,
)
from action_server_tests.run_outputs import test_service


def test_shared_output_store_skips_when_platform_is_not_linux(monkeypatch, tmp_path):
    monkeypatch.setattr(test_service, "sys", SimpleNamespace(platform="darwin"))

    with pytest.raises(pytest.skip.Exception, match="Linux private output-provider"):
        next(test_service.store.__wrapped__(tmp_path))


@pytest.mark.parametrize("fixture_name", ["provider", "reviewed", "local"])
def test_imported_private_provider_fixtures_skip_before_setup(
    monkeypatch, tmp_path, fixture_name
):
    module = {
        "provider": test_local_provider_setup,
        "reviewed": test_invoice_review,
        "local": test_provider_catalog,
    }[fixture_name]
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="darwin"))
    if fixture_name == "provider":
        with pytest.raises(pytest.skip.Exception, match="Linux private provider"):
            module.provider.__wrapped__(None)
        return
    arguments = (
        (SimpleNamespace(param="sqlite"), tmp_path, None)
        if fixture_name == "reviewed"
        else (tmp_path,)
    )
    generator = getattr(module, fixture_name).__wrapped__(*arguments)
    try:
        with pytest.raises(pytest.skip.Exception, match="Linux private provider"):
            next(generator)
    finally:
        generator.close()


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_native_canvas_is_unavailable_before_state_access_on_unsupported_platform(
    monkeypatch, tmp_path, platform
):
    from actions.server.foundry import bootstrap

    monkeypatch.setattr(bootstrap, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setenv("ACTIONS_FOUNDRY_TASK_POLICY", str(tmp_path / "missing-policy"))
    assert (
        bootstrap.create_runtime_canvas(
            object(),
            tmp_path / "native",
            "owned-key",
            html="unused on unsupported platform",
        )
        is None
    )
    assert not (tmp_path / "native").exists()


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
