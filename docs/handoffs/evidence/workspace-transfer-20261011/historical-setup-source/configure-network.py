"""Refresh only the cloud-owned Actions HTTP profile from injected proxy settings."""
import json
import os
from pathlib import Path
import tempfile

path = Path.home() / '.actions/network-settings.yaml'
if path.exists():
    try:
        existing = json.loads(path.read_text())
    except (ValueError, OSError):
        print('Preserving existing user network profile.')
        raise SystemExit(0)
    if existing.get('current-profile') != 'codex-cloud' or len(existing.get('profiles', [])) != 1:
        print('Preserving existing user network profile.')
        raise SystemExit(0)
    profile = existing['profiles'][0]
    if profile.get('name') != 'codex-cloud' or set(profile) - {'name', 'proxy-settings'}:
        print('Preserving existing user network profile.')
        raise SystemExit(0)
proxy = {key: os.environ[name] for key, name in (
    ('http-proxy', 'HTTP_PROXY'), ('https-proxy', 'HTTPS_PROXY'), ('no-proxy', 'NO_PROXY')
) if os.environ.get(name)}
data = {'current-profile': 'codex-cloud', 'profiles': [{'name': 'codex-cloud', 'proxy-settings': proxy}]}
path.parent.mkdir(parents=True, exist_ok=True)
with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as stream:
    json.dump(data, stream, indent=2)
    stream.write('\n')
    temporary = Path(stream.name)
try:
    os.chmod(temporary, 0o600)
    temporary.replace(path)
finally:
    temporary.unlink(missing_ok=True)
print('Actions HTTP cloud proxy profile refreshed; TLS verification remains enabled.')
