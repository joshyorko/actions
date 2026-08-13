from devutils.invoke_utils import owned_distribution_directory


def test_owned_distribution_mapping_covers_clean_break_packages():
    assert owned_distribution_directory("actions-core") == "actions"
    assert owned_distribution_directory("actions-runtime") == "action_server"
    assert owned_distribution_directory("actions-http-helper") == "actions-http-helper"
    assert owned_distribution_directory("actions-work-items") == "work-items"
    assert owned_distribution_directory("actions-local-devutils") == "devutils"
