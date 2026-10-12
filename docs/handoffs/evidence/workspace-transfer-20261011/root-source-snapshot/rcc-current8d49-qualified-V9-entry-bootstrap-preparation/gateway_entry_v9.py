import v9_entry_bootstrap
import sys
sys.path[:0] = ['/workspace/engineering/rcc-current8d49-private-V8-real-fixture-mode-successor', '/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation']
"""Actual launch entry only; pure planning function is exercised without gateway."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from actual_transport_v8 import SOURCE, TREE, need, parse_json_object, require_release, read_bound

RUNNER = '/workspace/engineering/rcc-current8d49-qualified-V9-entry-bootstrap-preparation/owned_native_entry_v9.py'
PACKAGES = ('actions', 'actions-http-helper', 'devutils', 'work-items', 'action_server')
MODULES = ('actions', 'actions_http', 'devutils.invoke_utils', 'actions.work_items', 'actions.server._rcc_runtime_adapter')


def gateway_plan(config, forwarded):
    rows = config['concrete_own_origins']
    need(type(rows) is list and len(rows) == 5, 'GATEWAY_OWN_ORIGIN_COUNT')
    calls = []
    for package, module, row in zip(PACKAGES, MODULES, rows):
        root = Path('/workspace/engineering/pr308') / package
        need(row['module'] == module and Path(row['prefix']) == root / '.venv'
             and Path(row['origin']).is_relative_to(root / 'src'), 'GATEWAY_OWN_ORIGIN')
        # All subprocess snippets carry literals; no free ROOT/root variables.
        code = ('import importlib,pathlib,sys; m=importlib.import_module(' + repr(module)
                + '); assert pathlib.Path(sys.prefix).resolve()==pathlib.Path(' + repr(row['prefix'])
                + ').resolve(); assert pathlib.Path(m.__file__).resolve()==pathlib.Path(' + repr(row['origin']) + ').resolve()')
        calls.append((package, 'run', 'python', '-c', code))
    calls.append(('action_server', 'run', 'python', RUNNER, *forwarded))
    return calls


def main():
    import toolkit
    need(Path(toolkit.REPOSITORY_ROOT).resolve() == Path('/workspace/engineering/pr308'), 'GATEWAY_REPOSITORY')
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--config-sha256', required=True)
    p.add_argument('--release', required=True)
    p.add_argument('--release-sha256', required=True)
    p.add_argument('--label', required=True)
    args = p.parse_args()
    raw = Path(args.config).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == args.config_sha256, 'GATEWAY_CONFIG_HASH')
    config = parse_json_object(raw)
    raw_release = Path(args.release).read_bytes()
    need(hashlib.sha256(raw_release).hexdigest() == args.release_sha256, 'GATEWAY_RELEASE_HASH')
    require_release(config, parse_json_object(raw_release), args.config_sha256, args.label)
    for row in config['bindings']:
        read_bound(row)
    # The fixed managed-activation metadata checker runs BEFORE this gateway.
    # These own-five concrete origins run before the one qualification child.
    for call in gateway_plan(config, sys.argv[1:]):
        toolkit.poetry(*call)


if __name__ == '__main__':
    main()
