"""Report bounded failure locations without exposing pytest messages or paths.

This advisory output is never an acceptance result. The caller must retain its
pytest, JUnit and source-bound receipt admission checks.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024
MAX_LOCATIONS = 16
TEST_CLASS = "tests.action_server_tests.mcp.test_canvas_query_template"
TEST_NAME = (
    "test_canvas_template_candidate_source_runs_through_runtime_and_real_browser"
)
PROFILE_TEST_NAMES = {
    "candidate": TEST_NAME,
    "published": "test_canvas_template_runs_through_runtime_and_real_browser",
}
EXCEPTIONS = frozenset(
    {
        "AssertionError",
        "RuntimeError",
        "CalledProcessError",
        "TimeoutExpired",
        "FileNotFoundError",
        "TypeError",
        "ValueError",
        "StopIteration",
        "Failed",
        "OSError",
    }
)
SHORT_LOCATION = re.compile(
    r"(?:^|[/\\])test_canvas_query_template\.py:([1-9][0-9]{0,5}):"
    r"[ \t]*([A-Za-z_][A-Za-z_0-9]{0,63})(?=[: \t\r\n]|$)",
    re.MULTILINE,
)
TRACE_LOCATION = re.compile(
    r"""(?m)^[ \t]*File ["'][^"'\r\n]*[/\\]test_canvas_query_template\.py["'], """
    r"line ([1-9][0-9]{0,5}), in [^\r\n]*$"
)
EXCEPTION_LINE = re.compile(r"(?m)^([A-Za-z_][A-Za-z_0-9]{0,63}):")


def _unavailable(reason: str) -> dict[str, object]:
    return {"availability": "UNAVAILABLE", "locations": [], "reason": reason}


def _exception(name: str) -> str:
    return name if name in EXCEPTIONS else "OTHER"


def summarize(path: Path, *, profile: str = "candidate") -> dict[str, object]:
    """Return fixed enums and known test line numbers, never input text."""
    test_name = PROFILE_TEST_NAMES.get(profile)
    if test_name is None:
        return _unavailable("UNKNOWN_PROFILE")
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError:
        return _unavailable("IO_ERROR")
    if len(raw) > MAX_BYTES:
        return _unavailable("SIZE_LIMIT")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return _unavailable("INVALID_XML")
    if root.tag not in {"testsuite", "testsuites"}:
        return _unavailable("INVALID_JUNIT")
    cases = [
        case
        for case in root.iter("testcase")
        if case.get("classname") == TEST_CLASS and case.get("name") == test_name
    ]
    if not cases:
        return _unavailable("NO_CANDIDATE_CASE")
    failures = [
        failure
        for case in cases
        for failure in (*case.findall("failure"), *case.findall("error"))
    ]
    if not failures:
        return {"availability": "NOT_NEEDED", "locations": []}
    locations: set[tuple[int, str]] = set()
    for failure in failures:
        text = failure.text or ""
        for match in SHORT_LOCATION.finditer(text):
            locations.add((int(match[1]), _exception(match[2])))
        exception_names = EXCEPTION_LINE.findall(text)
        exception = _exception(exception_names[-1]) if exception_names else "OTHER"
        for match in TRACE_LOCATION.finditer(text):
            locations.add((int(match[1]), exception))
    if not locations:
        return _unavailable("NO_MATCHING_LOCATION")
    return {
        "availability": "AVAILABLE",
        "locations": [
            {"line": line, "exception_class": exception}
            for line, exception in sorted(locations)[:MAX_LOCATIONS]
        ],
    }


def main() -> None:
    result = (
        summarize(
            Path(sys.argv[1]),
            profile=sys.argv[2] if len(sys.argv) == 3 else "candidate",
        )
        if len(sys.argv) in (2, 3)
        else _unavailable("ARGUMENT_COUNT")
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
