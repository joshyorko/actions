import inspect


def test_server_integration_symbols_preserve_existing_core_objects():
    import actions.server_integration as integration
    from actions._collect_actions import DEFAULT_EXCLUSION_PATTERNS as private_patterns
    from actions._customization._extension_points import (
        EPManagedParameters as PrivateEPManagedParameters,
    )
    from actions._customization._plugin_manager import (
        PluginManager as PrivatePluginManager,
    )
    from actions._lint_action import format_lint_results as private_format_lint_results
    from actions._managed_parameters import (
        ManagedParameters as PrivateManagedParameters,
    )
    from actions.server_integration import (
        DEFAULT_EXCLUSION_PATTERNS,
        EPManagedParameters,
        ManagedParameters,
        PluginManager,
        format_lint_results,
    )

    assert DEFAULT_EXCLUSION_PATTERNS is private_patterns
    assert EPManagedParameters is PrivateEPManagedParameters
    assert ManagedParameters is PrivateManagedParameters
    assert PluginManager is PrivatePluginManager
    assert format_lint_results is private_format_lint_results
    expected_exports = {
        "DEFAULT_EXCLUSION_PATTERNS",
        "EPManagedParameters",
        "ManagedParameters",
        "PluginManager",
        "format_lint_results",
    }
    assert set(integration.__all__) == expected_exports
    assert len(integration.__all__) == len(expected_exports)


def test_server_integration_managed_request_can_be_registered_and_injected():
    from actions import Request
    from actions.server_integration import (
        EPManagedParameters,
        ManagedParameters,
        PluginManager,
    )

    request = Request.model_validate(
        {"headers": {"X-Request-ID": "request-1"}, "cookies": {"session": "s"}}
    )
    managed_parameters = ManagedParameters({"request": request})
    plugin_manager = PluginManager()
    plugin_manager.set_instance(EPManagedParameters, managed_parameters)

    request_parameter = inspect.signature(lambda request: None).parameters["request"]
    assert plugin_manager.get_instance(EPManagedParameters) is managed_parameters
    assert managed_parameters.is_managed_param("request", param=request_parameter)
    assert (
        managed_parameters.get_managed_param_type("request", param=request_parameter)
        is Request
    )
    assert managed_parameters.inject_managed_params(
        inspect.signature(lambda request: None), None, {}, {}
    ) == {"request": request}
    assert managed_parameters.get_request_contexts({}, {}).request is request


def test_server_integration_formats_core_lint_errors():
    from actions.server_integration import format_lint_results

    formatted = format_lint_results(
        {
            "file": "actions.py",
            "errors": [
                {
                    "range": {"start": {"line": 7}},
                    "severity": 1,
                    "message": "missing description",
                }
            ],
        }
    )

    assert formatted is not None
    assert formatted.found_critical
    assert "Action lint error(s) found at file: actions.py" in formatted.message
    assert "Error (line 7): missing description" in formatted.message
    assert format_lint_results({"file": "actions.py", "errors": None}) is None
