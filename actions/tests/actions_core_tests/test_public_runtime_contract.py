import base64
import json
import subprocess
import sys


def test_runtime_contract_types_are_public_root_exports_and_keep_private_aliases():
    import actions
    from actions import ActionContext, ActionsListActionTypedDict
    from actions._action_context import ActionContext as PrivateActionContext
    from actions._protocols import (
        ActionsListActionTypedDict as PrivateActionsListActionTypedDict,
    )

    assert ActionContext is PrivateActionContext
    assert ActionsListActionTypedDict is PrivateActionsListActionTypedDict
    assert {"ActionContext", "ActionsListActionTypedDict"} <= set(actions.__all__)
    assert ActionsListActionTypedDict.__required_keys__ == {
        "name",
        "line",
        "file",
        "docs",
        "input_schema",
        "output_schema",
        "managed_params_schema",
        "options",
    }

    encoded_context = base64.b64encode(
        json.dumps({"secrets": {"token": "kept"}}).encode("utf-8")
    ).decode("ascii")
    assert ActionContext(encoded_context).value == {"secrets": {"token": "kept"}}


def test_action_context_public_export_does_not_eagerly_import_context_module():
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, actions; "
            "assert 'actions._action_context' not in sys.modules; "
            "from actions import ActionContext; "
            "assert 'actions._action_context' in sys.modules",
        ],
        check=True,
    )
