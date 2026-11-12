import pytest
from pydantic import ValidationError

from actions.agent import ReductoPlatformParameters


@pytest.mark.parametrize(
    "values", [{}, {"reducto_api_url": ""}, {"reducto_api_url": "  "}]
)
def test_reducto_requires_explicit_endpoint(values):
    with pytest.raises(ValidationError):
        ReductoPlatformParameters(**values)


@pytest.mark.parametrize(
    "url", ["https://owned.example/reducto", "https://backend.sema4ai.dev/reducto"]
)
def test_reducto_explicit_compatibility_payload(url):
    params = ReductoPlatformParameters(
        reducto_api_url=url, delegate_kind="openai", delegate_api_key="synthetic"
    )
    assert params.model_dump() == {
        "kind": "reducto",
        "reducto_api_url": url,
        "reducto_api_key": None,
        "delegate_kind": "openai",
        "delegate_api_key": "synthetic",
    }
