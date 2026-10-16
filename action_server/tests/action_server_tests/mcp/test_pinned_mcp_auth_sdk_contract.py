"""Contract probes for the locked MCP SDK; these do not exercise Runtime auth."""

from importlib.metadata import version

import pytest
from mcp.client.auth.utils import (
    is_valid_client_metadata_url,
    should_use_client_metadata_url,
)
from mcp.server.auth.routes import (
    build_metadata,
    build_resource_metadata_url,
    validate_issuer_url,
)
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.shared.auth import AnyHttpUrl


def test_probe_is_bound_to_the_locked_sdk_version():
    assert version("mcp") == "2.0.0"


@pytest.mark.parametrize(
    "issuer",
    [
        "https://auth.example.test/issuer",
        "http://localhost:9000/issuer",
        "http://127.0.0.1:9000/issuer",
        "http://[::1]:9000/issuer",
    ],
)
def test_sdk_accepts_https_and_loopback_http_issuer_urls(issuer):
    validate_issuer_url(AnyHttpUrl(issuer))


@pytest.mark.parametrize(
    "issuer",
    [
        "http://auth.example.test/issuer",
        "https://auth.example.test/issuer?tenant=one",
        "https://auth.example.test/issuer#fragment",
    ],
)
def test_sdk_rejects_non_loopback_http_and_issuer_query_or_fragment(issuer):
    with pytest.raises(ValueError):
        validate_issuer_url(AnyHttpUrl(issuer))


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://client.example.test/metadata.json", True),
        ("https://client.example.test/", False),
        ("https://client.example.test", False),
        ("http://client.example.test/metadata.json", False),
        (None, False),
    ],
)
def test_sdk_cimd_url_helper_requires_https_and_non_root_path(url, expected):
    assert is_valid_client_metadata_url(url) is expected


def test_locked_server_metadata_does_not_advertise_cimd_support():
    metadata = build_metadata(
        issuer_url=AnyHttpUrl("https://auth.example.test"),
        service_documentation_url=None,
        client_registration_options=ClientRegistrationOptions(),
        revocation_options=RevocationOptions(),
    )

    assert metadata.client_id_metadata_document_supported is None
    assert (
        should_use_client_metadata_url(metadata, "https://client.example.test/id")
        is False
    )


@pytest.mark.parametrize(
    ("resource_url", "metadata_url"),
    [
        (
            "https://runtime.example.test/mcp",
            "https://runtime.example.test/.well-known/oauth-protected-resource/mcp",
        ),
        (
            "https://runtime.example.test/",
            "https://runtime.example.test/.well-known/oauth-protected-resource",
        ),
    ],
)
def test_sdk_maps_resource_path_to_rfc9728_metadata_url(resource_url, metadata_url):
    assert str(build_resource_metadata_url(AnyHttpUrl(resource_url))) == metadata_url
