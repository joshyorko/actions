"""One root-adopted gateway call, enclosed by the declared 900s outer timeout.

This launcher records primary return/raw before the separate post guard. Root
must supply current independent config review and once-version authorization.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from actual_transport_v7 import content_sha, require_release
from runner_contracts_v3 import need, parse_json_object, validate_fresh_capacity


CACHED = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'


def write_private(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)


def commands(forwarded):
    base = Path(__file__).parent
    guard = ['timeout', '--signal=TERM', '--kill-after=10s', '120s', CACHED,
             str(base/'readonly_current_input_guard_v1.py'), *forwarded]
    gateway = ['timeout', '--signal=TERM', '--kill-after=10s', '660s',
               '/workspace/actions-cloud/bin/rcc', 'task', 'script', '-r', 'developer/toolkit.yaml',
               '--', 'python', str(base/'gateway_entry_v2.py'), *forwarded]
    return guard, gateway, list(guard)


def main():
    parser = argparse.ArgumentParser()
    for key in ('config', 'config-sha256', 'release', 'release-sha256', 'label', 'log-root'):
        parser.add_argument('--' + key, required=True)
    args = parser.parse_args()
    need(Path(sys.executable).resolve() == Path(CACHED).resolve(), 'LAUNCHER_CACHED_TOOLKIT_PYTHON')
    need('ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG' not in os.environ
         and 'ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY' not in os.environ, 'LAUNCHER_NO_INHERITED_OPERATOR_SELECTION')
    raw = Path(args.config).read_bytes(); need(content_sha(raw) == args.config_sha256, 'LAUNCHER_CONFIG_HASH')
    release_raw = Path(args.release).read_bytes(); need(content_sha(release_raw) == args.release_sha256, 'LAUNCHER_ROOT_RELEASE_HASH')
    config = parse_json_object(raw)
    require_release(config, parse_json_object(release_raw), args.config_sha256, args.label)
    free_shm = os.statvfs('/dev/shm'); free_workspace = os.statvfs('/workspace')
    validate_fresh_capacity(free_shm.f_bavail * free_shm.f_frsize, free_workspace.f_bavail * free_workspace.f_frsize)
    need(free_workspace.f_bavail * free_workspace.f_frsize >= 1288490189, 'ROOT_STRICT_WORKSPACE_FLOOR')
    os.umask(0o077)
    logs = Path(args.log_root)
    need(logs.parent == Path('/workspace/engineering') and logs.name.startswith('root-rcc-owned-cache-one-')
         and not logs.exists() and not logs.is_symlink(), 'ROOT_ONCE_PRIVATE_LOG_ROOT')
    logs.mkdir(mode=0o700)
    forwarded = []
    for key in ('config', 'config_sha256', 'release', 'release_sha256', 'label'):
        forwarded += ['--' + key.replace('_', '-'), getattr(args, key)]
    pre, gateway, post = commands(forwarded)
    outcomes = {}
    try:
        completed = subprocess.run(pre, cwd=config['source_root'], capture_output=True)
        outcomes['preflight_returncode'] = completed.returncode
        write_private(logs/'preflight.stdout', completed.stdout); write_private(logs/'preflight.stderr', completed.stderr)
        if completed.returncode == 0:
            completed = subprocess.run(gateway, cwd=config['source_root'], capture_output=True)
            outcomes['primary_returncode'] = completed.returncode
            write_private(logs/'primary-returncode.json', (json.dumps({'returncode': completed.returncode})+'\n').encode())
            write_private(logs/'primary.stdout', completed.stdout); write_private(logs/'primary.stderr', completed.stderr)
        else:
            outcomes['gateway'] = 'NOT_RUN_PREFLIGHT_FAILED'
    except Exception as error:
        outcomes['primary_exception_class'] = type(error).__name__
        # Exception bodies remain in this private file; never replace completed raw.
        write_private(logs/'launcher-exception.private.txt', str(error).encode())
    finally:
        try:
            completed = subprocess.run(post, cwd=config['source_root'], capture_output=True)
            outcomes['post_returncode'] = completed.returncode
            write_private(logs/'post.stdout', completed.stdout); write_private(logs/'post.stderr', completed.stderr)
        except Exception as error:
            outcomes['post_exception_class'] = type(error).__name__
        write_private(logs/'launcher-terminal.json', (json.dumps(outcomes, sort_keys=True, indent=2)+'\n').encode())
    admitted = outcomes.get('preflight_returncode') == outcomes.get('primary_returncode') == outcomes.get('post_returncode') == 0
    return 0 if admitted and not any(key.endswith('exception_class') for key in outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
