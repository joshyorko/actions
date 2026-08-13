from devutils.invoke_utils import owned_distribution_directory


def test_owned_distribution_mapping_preserves_split_compatibility():
    assert owned_distribution_directory("actions-core") == "actions"
    assert owned_distribution_directory("actions-runtime") == "action_server"
    assert owned_distribution_directory("actions-http-helper") == "actions-http-helper"
    assert owned_distribution_directory("actions-work-items") == "work-items"

    # The community Runtime still consumes the published legacy Core until #80 lands.
    assert owned_distribution_directory("sema4ai-actions") is None
    assert owned_distribution_directory("sema4ai-mcp") == "mcp"