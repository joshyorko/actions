from actions import Response, action


@action
def greet_fail_with_action_error() -> Response[str]:
    """
    Provides a greeting for a person.

    Returns:
        The greeting for the person.
    """
    from actions import ActionError

    raise ActionError("Sorry, this must fail.")
