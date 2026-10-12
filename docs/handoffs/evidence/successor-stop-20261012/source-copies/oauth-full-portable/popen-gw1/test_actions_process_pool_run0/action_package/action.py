
from actions import action

@action
def greet(name: str, title="Mr.") -> str:
    return f"Hello {title} {name}."
