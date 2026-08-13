import os

from actions import action


@action
def main_task():
    from tempfile import gettempdir

    os.chdir(gettempdir())
