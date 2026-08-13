from actions import action


@action
def main():
    pass


@action  # type: ignore # noqa
def main():  # type: ignore # noqa
    pass
