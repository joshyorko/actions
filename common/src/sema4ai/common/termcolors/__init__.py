try:
    from termcolor import colored  # type: ignore
except ImportError:

    def _noop(msg):
        return msg

    bold_yellow = _noop
    bold_red = _noop
    bold = _noop
else:

    def bold_yellow(msg):
        return colored(msg, color="yellow", attrs=["bold"])

    def bold_red(msg):
        return colored(msg, color="red", attrs=["bold"])

    def bold(msg):
        return colored(msg, attrs=["bold"])
