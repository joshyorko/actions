"""Subprocess fixture: no actual credentials; only synthetic canaries."""
# The import blocker must be installed before importing the implementation.
# ruff: noqa: E402

import base64
import importlib.abc
import json
import sys
from pathlib import Path


class RejectUpstream(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "robocorp" or fullname.startswith("robocorp."):
            raise AssertionError("Unexpected upstream import: " + fullname)


sys.meta_path.insert(0, RejectUpstream())
sys.dont_write_bytecode = False
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from actions import _logging as log
from actions._logging._rewrite_importhook import NAME_WITH_TAG, get_cache_dir

assert "-actions-log-1-" in NAME_WITH_TAG
root = Path(sys.argv[1])
sys.pycache_prefix = str(root / "cache")
sys.path.insert(0, str(root))
module = root / "owned_action.py"
if not module.exists():
    module.write_text(
        "def consume(raw, oauth, context_secret, context_oauth):\n"
        "    from actions import _logging as log\n"
        "    values = [raw.value, oauth.access_token, context_secret.value, context_oauth.access_token]\n"
        "    for value in values:\n"
        "        log.info(value, repr(value))\n"
        "    return 'visible-owned-result'\n"
        "def suppressed(value):\n"
        "    return value\n"
    )
    # A stale upstream-cache file must be ignored entirely by the owned hook.
    cache = get_cache_dir(module)
    cache.mkdir(parents=True, exist_ok=True)
    (
        cache / f"owned_action-full_log.{sys.implementation.cache_tag}-log-0.0.25.pyc"
    ).write_bytes(b"upstream-cache-must-not-be-consumed")
canaries = [f'canary-{i}-quote-"-newline-\n-end' for i in range(4)]
key = AESGCM.generate_key(256)
nonce = b"synthetic-iv!"
plaintext = json.dumps(
    {
        "secrets": {
            "password": canaries[2],
            "oauth": {"provider": "test", "scopes": [], "access_token": canaries[3]},
        }
    }
).encode()
encrypted = AESGCM(key).encrypt(nonce, plaintext, None)


def b64(value):
    return base64.b64encode(value).decode("ascii")


envelope = b64(
    json.dumps(
        {
            "algorithm": "aes256-gcm",
            "iv": b64(nonce),
            "cipher": b64(encrypted[:-16]),
            "auth-tag": b64(encrypted[-16:]),
        }
    ).encode()
)
output = root / "output"
with log.add_log_output(output, log_html=output / "log.html"):
    log.start_run("owned")
    log.start_task("owned", "owned_action", str(module), 1)
    with log.setup_auto_logging():
        import owned_action

        from actions import OAuth2Secret, Secret
        from actions._action_context import ActionContext

        raw = Secret.model_validate(canaries[0])
        oauth = OAuth2Secret.model_validate(
            {"provider": "test", "scopes": [], "access_token": canaries[1]}
        )
        context = ActionContext(
            envelope,
            env={
                "ACTION_SERVER_DECRYPT_KEYS": json.dumps([b64(key)]),
                "ACTION_SERVER_DECRYPT_INFORMATION": json.dumps(
                    ["header:x-action-context"]
                ),
            },
        )
        context_secret = Secret.from_action_context(context, "password")
        context_oauth = OAuth2Secret.from_action_context(context, "secrets/oauth")
        assert (
            owned_action.consume(raw, oauth, context_secret, context_oauth)
            == "visible-owned-result"
        )
        assert [
            raw.value,
            oauth.access_token,
            context_secret.value,
            context_oauth.access_token,
        ] == canaries
        with log.suppress():
            owned_action.suppressed("suppressed-canary-marker")
    log.end_task("owned", "owned_action", "PASS", "")
    log.end_run("owned", "PASS")
events = list(log.iter_decoded_log_format_from_log_html(output / "log.html"))
decoded = str(events)
assert "visible-owned-result" in decoded
assert "suppressed-canary-marker" not in decoded
raw_logs = "".join(p.read_text() for p in output.glob("*.robolog"))
for i, canary in enumerate(canaries):
    assert canary not in decoded and repr(canary) not in decoded
    assert f"canary-{i}" not in decoded + raw_logs
assert {"SR", "ER", "ST", "ET", "SE", "EE"}.issubset(
    {e["message_type"] for e in events}
)
assert any(get_cache_dir(module).glob(f"owned_action-*.{NAME_WITH_TAG}.pyc"))
assert not any(k == "robocorp" or k.startswith("robocorp.") for k in sys.modules)
print("OWNED_LOGGING_PASS")
