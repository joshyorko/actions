"""The numeric public version tuple excludes candidate prerelease metadata."""

from packaging.version import Version

import actions


def test_public_version_tuple_matches_pep440_release():
    assert tuple(actions.version_info) == Version(actions.__version__).release
