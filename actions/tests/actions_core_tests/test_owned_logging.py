"""Exercise the owned logging boundary in a fresh interpreter, without upstream imports."""

import subprocess
import sys
from pathlib import Path


def test_owned_logging_redaction_and_cached_instrumentation(tmp_path):
    fixture = Path(__file__).with_name("owned_logging_probe.py")
    # The second process must use the owned rewritten cache successfully too.
    cached = None
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, str(fixture), str(tmp_path)],
            capture_output=True,
            timeout=30,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        current = {
            p: p.stat().st_mtime_ns
            for p in tmp_path.rglob("owned_action-*.cpython-*-actions-log-*.pyc")
        }
        assert current
        if cached is not None:
            assert current == cached
        cached = current
        assert "OWNED_LOGGING_PASS" in result.stdout
        assert "canary-" not in result.stdout + result.stderr


def test_owned_viewer_template_matches_encoder_asset():
    from actions._logging import get_log_viewer_html
    from actions._logging._index_v3 import FILE_CONTENTS

    assert get_log_viewer_html() == FILE_CONTENTS["index.html"]


def test_secret_internals_cannot_be_enabled_by_user_filters():
    from actions._logging import DefaultAutoLogConfig, Filter, FilterKind

    config = DefaultAutoLogConfig(filters=[Filter("actions", FilterKind.full_log)])
    for name in (
        "actions._logging",
        "actions._secret",
        "actions._secret._secret",
        "actions._secret._oauth2_secret",
        "actions._action_context",
    ):
        assert config.get_filter_kind_by_module_name(name) == FilterKind.exclude
