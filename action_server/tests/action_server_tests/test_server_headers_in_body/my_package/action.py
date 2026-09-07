from actions._secret import Secret

from actions import Request, action


@action
def my_action(arg: str, private_info: Secret, request: Request) -> str:
    """
    Does something
    """
    assert "x-action-context" in request.headers
    return "Ok"
