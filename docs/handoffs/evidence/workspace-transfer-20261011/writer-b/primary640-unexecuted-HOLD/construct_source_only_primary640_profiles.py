"""Stdlib construction only. Never loads a product/runner or executes a gate."""
import ast
import hashlib
import json
import os
import pathlib
import textwrap


B = pathlib.Path(__file__).resolve().parent
PROFILES = {
    '305': pathlib.Path('/workspace/engineering/pr305-currentf75-private-bounded-LIGHT-guard-env-successor-SOURCE-NOTRUN'),
    '313': pathlib.Path('/workspace/engineering/pr313-current2d86-config-captured-buffer-SOURCE-successor-NOTRUN'),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path):
    path = pathlib.Path(path)
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': sha(path.read_bytes()), 'mode': oct(path.stat().st_mode & 0o7777)}


def put(path, raw, mode):
    raw = raw.encode() if isinstance(raw, str) else raw
    with pathlib.Path(path).open('xb') as stream:
        os.chmod(path, mode)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return row(path)


def dump(path, value):
    return put(path, json.dumps(value, indent=2, sort_keys=True)+'\n', 0o400)


def function(text, name):
    tree = ast.parse(text)
    return ast.get_source_segment(text, next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name))


def main():
    profiles = []
    for profile, old in PROFILES.items():
        config_old = next(old.glob('FROZEN*.json'))
        old_cfg = json.loads(config_old.read_bytes())
        launch_old = next(old.glob('launch*.py'))
        old_launch = launch_old.read_text()
        guard_old = pathlib.Path(old_cfg['guard']['path'])
        old_guard = guard_old.read_text()
        attempt_old = old_cfg['outputs']['attempt']
        attempt = '/workspace/engineering/'+('pr305-currentf75-primary640-LIGHT-once3-owned' if profile == '305' else 'pr313-current2d86-primary640-cached-LIGHT-once2-owned')
        cfg = json.loads(json.dumps(old_cfg))
        cfg['outputs']['attempt'] = attempt
        # Only executable destination fields change. Historical input bindings
        # retain their original paths and bytes, including all failed packets.
        for phase in cfg['phases']:
            phase['code'] = phase['code'].replace(attempt_old, attempt)
        cfg['native_inner_cleanup_scope'] = 'POOL_TCP_PROVIDER_READERS_AND_ACTION_LEASE_NOT_MEASURED_HOLD'
        cfg['bounds'] = {'primary_cooperative_seconds': 600, 'original_helper_command_seconds': 600,
                         'original_helper_cleanup_grace_seconds': 10,
                         'independent_GNU_primary_TERM_seconds': 630, 'independent_GNU_KILL_grace_seconds': 10,
                         'external_primary_fallback_starts_seconds': 620,
                         'absolute_primary_including_owner_cleanup_seconds': 640,
                         'external_before_command_seconds': 60, 'external_before_owner_enclosure_seconds': 80,
                         'external_post_command_seconds': 60, 'external_post_owner_enclosure_seconds': 80,
                         'ROOT_whole_TERM_seconds': 900, 'ROOT_whole_KILL_grace_seconds': 10,
                         'ROOT_parent_seconds': 930}
        # Captured config/source-data parsing; existing source/native/input
        # semantics remain unchanged. Authority moves to the external parent.
        guard = old_guard
        if profile == '313':
            guard = guard.replace('len(sys.argv)==12', 'len(sys.argv)==4')
            start = guard.index(' # Full authority closure revalidated')
            end = guard.index(' assert Path(sys.prefix)', start)
            guard = guard[:start]+guard[end:]
        else:
            buffer_source = json.loads(next(PROFILES['313'].glob('FROZEN*.json')).read_bytes())['guard']['path']
            buffer_helper = function(pathlib.Path(buffer_source).read_text(), 'verified_buffer')
            guard = guard.replace('def main():', buffer_helper+'\n\ndef main():', 1)
            guard = guard.replace("assert digest(p)==sys.argv[2];c=json.loads(p.read_bytes());root=Path(c['source_root'])", "c=json.loads(verified_buffer(p,sys.argv[2],0o400));root=Path(c['source_root'])")
            guard = guard.replace("rows=json.loads(Path(c['source_inventory']['path']).read_bytes());", "r=c['source_inventory'];rows=json.loads(verified_buffer(r['path'],r['sha256'],int(r['mode'],8),expected_bytes=r['bytes']));")
            guard = guard.replace("baseline=json.loads(Path(c['native_baseline']['path']).read_bytes());", "r=c['native_baseline'];baseline=json.loads(verified_buffer(r['path'],r['sha256'],int(r['mode'],8),expected_bytes=r['bytes']));")
        guard_path = B/('current_'+profile+'_read_only_source_guard_NOTRUN.py')
        cfg['guard'] = put(guard_path, guard, 0o444)
        # Preserve every original phase, pytest census rule, environment copy,
        # CLI selector and helper-function AST. Only admission/guard ownership
        # moves outside this primary-only child.
        helper_names = ['digest', 'write', 'dump', 'exact', 'run_phase', 'package_env', 'gateway', 'pytest_env']
        helpers = '\n\n'.join(function(old_launch, name) for name in helper_names)
        loop_start = old_launch.index("  for phase in cfg['phases']:")
        loop_end = old_launch.index("  status=", loop_start)
        loop = textwrap.dedent(old_launch[loop_start:loop_end])
        primary = '''"""Prepared primary-only source phase loop; ROOT parent admission required."""
import hashlib,json,os,signal,stat,subprocess,sys,time
from pathlib import Path
ROOT=Path(SOURCE_ROOT_LITERAL)
CACHED=Path(CACHED_LITERAL)
ATTEMPT=None
PRIMARY_STARTED=None
SOURCE=SOURCE_LITERAL
TREE=TREE_LITERAL
HELPERS

def main():
 global ATTEMPT,PRIMARY_STARTED
 assert len(sys.argv)==4 and sys.flags.optimize==0
 p=Path(sys.argv[1]);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink() and stat.S_IMODE(m.st_mode)==0o400
 raw=p.read_bytes();assert len(raw)==m.st_size and digest(raw)==sys.argv[2];cfg=json.loads(raw)
 assert cfg['source']==SOURCE and cfg['tree']==TREE
 ATTEMPT=Path(sys.argv[3]);assert str(ATTEMPT)==cfg['outputs']['attempt']
 assert ATTEMPT.is_dir() and not ATTEMPT.is_symlink() and stat.S_IMODE(ATTEMPT.stat().st_mode)==0o700
 assert Path(sys.prefix).resolve()==CACHED.resolve()
 for row in cfg['bindings']:exact(row)
 parent_lease=json.loads((ATTEMPT/'original-parent-lease.json').read_bytes())
 assert parent_lease['source']==SOURCE and parent_lease['tree']==TREE and parent_lease['config_sha256']==sys.argv[2]
 env=os.environ.copy();primary_env=env.copy();primary_env['ACTIONS_RUNTIME_TEST_PYTHON']=str(ROOT/'action_server/.venv/bin/python')
 PRIMARY_STARTED=time.monotonic();error=None
 try:
LOOP
 except BaseException as caught:error=caught
 finally:
  dump(ATTEMPT/'primary-original-terminal.json',{'status':'FAIL' if error else 'PASS_SOURCE_PHASES_ONLY','source':SOURCE,'tree':TREE,'primary_exception_type':type(error).__name__ if error else None,'native_Action_lease_pool_provider_reader_scope':'NOT_RUN_HOLD'})
 if error is not None:raise error
if __name__=='__main__':main()
'''
        replacements = {'SOURCE_ROOT_LITERAL': repr(cfg['source_root']), 'CACHED_LITERAL': repr(cfg['cached_prefix']),
                        'SOURCE_LITERAL': repr(cfg['source']), 'TREE_LITERAL': repr(cfg['tree']), 'HELPERS': helpers,
                        'LOOP': textwrap.indent(loop.rstrip(), '  ')}
        for key, value in replacements.items():
            primary = primary.replace(key, value)
        ast.parse(primary)
        cfg['primary_child'] = put(B/('current_'+profile+'_primary_only_phase_child_NOTRUN.py'), primary, 0o444)
        cfg['owner_boundary'] = row(B/'owned_primary_boundary_NOTRUN.py')
        cfg['supervisor_entry'] = row(B/'original_supervisor_observation_entry_NOTRUN.py')
        originals = [row(config_old), row(launch_old), row(guard_old), row(next(old.glob('OWNERFINAL*.json')))]
        helper_row = row('/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers/verify_dakota_rcc_acceptance.py')
        rows = [*cfg['bindings'], *originals, cfg['guard'], cfg['primary_child'], cfg['owner_boundary'], cfg['supervisor_entry'], helper_row]
        by_path = {}
        for item in rows:
            if item['path'] in by_path:
                assert by_path[item['path']] == item
            by_path[item['path']] = item
        cfg['bindings'] = list(by_path.values())
        cfgrow = dump(B/('FROZEN-'+profile+'-primary640-inputs-NOTRUN.json'), cfg)
        old_tree = ast.parse(old_launch)
        new_tree = ast.parse(primary)
        for name in helper_names:
            old_def = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            new_def = next(n for n in new_tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            assert ast.dump(old_def, include_attributes=False) == ast.dump(new_def, include_attributes=False)
        phases_inverse = json.loads(json.dumps(cfg['phases']))
        for phase in phases_inverse:
            phase['code'] = phase['code'].replace(attempt, attempt_old)
        assert phases_inverse == old_cfg['phases']
        profiles.append({'profile': profile, 'source': cfg['source'], 'tree': cfg['tree'], 'source_count': 1441,
                         'config': cfgrow, 'guard': cfg['guard'], 'primary_child': cfg['primary_child'],
                         'originals': originals, 'immutable_input_count': len(cfg['bindings']),
                         'eight_actual_helper_ASTs_exact': True, 'phases_inverse_exact': True,
                         'actual_controls_and_SOURCE_LIGHT': 'NOT_RUN_HOLD',
                         'hard_primary': 'GNU630TERM10_PLUS_EXCLUSIVE_PARENT_ABSOLUTE640_RESERVED_FALLBACK',
                         'whole': 'ROOT900TERM10_PARENT930_REQUIRED_NOT_RUN'})
    dump(B/'exact-source-profile-and-original-phase-preservation-proof-NOTRUN.json', {'schema': 1, 'profiles': profiles})
    print(json.dumps({'profiles': [{'profile': p['profile'], 'config': p['config'], 'rows': p['immutable_input_count']} for p in profiles]}))


if __name__ == '__main__':
    main()
