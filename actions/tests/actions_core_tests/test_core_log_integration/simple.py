import difflib

from actions import action


@action
def check_difflib_log():
    diff = difflib.ndiff("aaaa bbb ccc ddd".split(), "aaaa bbb eee ddd".split())
    print("".join(diff))
