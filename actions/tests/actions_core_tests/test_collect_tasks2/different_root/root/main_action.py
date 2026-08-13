from actions import action

from . import module  # noqa


@action
def something():
    print("worked")
