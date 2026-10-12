"""Prepared real primary-only enclosure and independent all-outcome closure.

No SOURCE/control/PREEXEC decision is granted by this module. A distinct ROOT
release and both exact independent reviews are required before any package work.
"""
import hashlib
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parent
PROFILES = {
    '305': {
        'source': 'f75dcae52fcd78c5c382d3903b012e5b049ca48b',
        'tree': '851834ae6cc87f42abfcf3c963542191e2815599',
        'attempt': '/workspace/engineering/pr305-currentf75-primary640-LIGHT-once3-owned',
    },
    '313': {
        'source': '2d86c5cf92d3acb274a8ceb5d57bfb8b12c779b6',
        'tree': '653a9e73e4d27641ec86de94b90f35d41e0f24f8',
        'attempt': '/workspace/engineering/pr313-current2d86-primary640-cached-LIGHT-once2-owned',
    },
}


def verified(row, mode, *, uidgid=True):
    p = Path(row['path'])
    m = p.lstat()
    assert stat.S_ISREG(m.st_mode) and not p.is_symlink()
    assert stat.S_IMODE(m.st_mode) == mode == int(row['mode'], 8)
    if uidgid:
        assert (m.st_uid, m.st_gid) == (os.getuid(), os.getgid())
    raw = p.read_bytes()
    assert len(raw) == m.st_size == row['bytes']
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
    return raw


def file_row(path, sha, mode):
    p = Path(path)
    return {'path': str(p), 'sha256': sha, 'bytes': p.lstat().st_size, 'mode': oct(mode)}


def authority(argv):
    assert len(argv) == 7 and argv[1] in PROFILES
    assert sys.flags.optimize == 0 and 'PYTHONOPTIMIZE' not in os.environ
    assert 'PYTEST_ADDOPTS' not in os.environ
    profile = PROFILES[argv[1]]
    cfgrow = file_row(argv[2], argv[3], 0o400)
    assert Path(cfgrow['path']) == BASE/('FROZEN-'+argv[1]+'-primary640-inputs-NOTRUN.json')
    cfg = json.loads(verified(cfgrow, 0o400))
    grantrow = file_row(argv[4], argv[5], 0o600)
    assert Path(grantrow['path']) == BASE/('root-one-'+argv[1]+'-primary640-release.json')
    grant = json.loads(verified(grantrow, 0o600))
    assert set(grant) == {'schema', 'decision', 'profile', 'source', 'tree',
                         'config_binding', 'parent_binding', 'independent_source_review',
                         'independent_preexecution_review', 'serialized_no_other_heavy_or_installer'}
    assert type(grant['schema']) is int and grant['schema'] == 1
    assert grant['serialized_no_other_heavy_or_installer'] is True
    assert grant['decision'] == 'ROOT_RELEASE_ONE_CURRENT_'+argv[1]+'_PRIMARY640_SOURCE_LIGHT_ONLY'
    assert grant['profile'] == argv[1]
    assert grant['source'] == cfg['source'] == profile['source']
    assert grant['tree'] == cfg['tree'] == profile['tree']
    assert grant['config_binding'] == cfgrow
    parentrow = grant['parent_binding']
    assert Path(parentrow['path']) == Path(__file__).absolute()
    verified(parentrow, 0o444)
    assert argv[6] == grant['independent_preexecution_review']['path']
    for key, decision in (
        ('independent_source_review', 'GO_CURRENT_'+argv[1]+'_PRIMARY640_OWNED_LIGHT_SOURCE_ONLY'),
        ('independent_preexecution_review', 'GO_CURRENT_'+argv[1]+'_PRIMARY640_OWNED_LIGHT_PREEXECUTION'),
    ):
        review = json.loads(verified(grant[key], 0o400))
        assert review['decision'] == decision
        assert review['source'] == cfg['source'] and review['tree'] == cfg['tree']
        assert review['config_sha256'] == cfgrow['sha256']
        assert review['parent_sha256'] == parentrow['sha256']
        assert review['controls_actual_status'] == 'PASS_WITH_EXACT_BASELINE_AND_NEGATIVE_CENSUS'
    assert cfg['outputs']['attempt'] == profile['attempt']
    assert cfg['source_leaf_count'] == 1441 and cfg['workspace_floor_bytes'] == 1288490189
    assert Path(sys.prefix).resolve() == Path(cfg['cached_prefix']).resolve()
    for row in cfg['bindings']:
        verified(row, int(row['mode'], 8), uidgid=False)
    for name, value in cfg['expected_activation'].items():
        assert os.environ[name] == value
    assert os.environ['PATH'].split(os.pathsep)[0] == '/workspace/actions-cloud/bin'
    for name in cfg['forbidden_actual_operator_exports']:
        assert name not in os.environ
    return cfg, cfgrow, grant


def module_from_verified(row, name):
    raw = verified(row, 0o444)
    spec = importlib.util.spec_from_file_location(name, row['path'])
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, row['path'], 'exec'), module.__dict__)
    return module


def primary_completed(cfg, attempt, outer):
    """A clean outer process cannot supply absent/failed inner supervisor facts."""
    raw = (attempt/'primary-enclosure'/'stdout.bin').read_bytes()
    result = json.loads(raw)
    observation = json.loads((attempt/'original-supervisor-observation.json').read_bytes())
    assert observation['original_supervisor_returncode'] == 0 and observation['errors'] == []
    assert isinstance(observation['owner'], dict) and isinstance(observation['command_owner'], dict)
    assert observation['drains'] and all(x['echild_observed'] is True for x in observation['drains'])
    assert observation['final_census'] == {'snapshot_complete': True, 'processes': []}
    assert observation['reader_backend'] == 'REGULAR_FILES_NO_OUTPUT_READER_THREADS'
    assert observation['output_reader_threads_created'] == 0
    assert observation['inner_pool_provider_readers'] == 'NOT_MEASURED'
    assert result['returncode'] == 0 and result['timed_out'] is False
    assert result['unexpected_live_descendants'] is False
    assert result['cleanup_disposition'] in ('clean_no_descendants', 'reaped_exited_descendants')
    assert outer['primary'] == 'COMMAND_PASS' and outer['cleanup'] == 'PASS'
    # This child's terminal is original source-test census and status, never
    # a generated natural-Action/provider/lease success claim.
    terminal = json.loads((attempt/'primary-original-terminal.json').read_bytes())
    assert terminal['status'] == 'PASS_SOURCE_PHASES_ONLY'
    assert terminal['source'] == cfg['source'] and terminal['tree'] == cfg['tree']
    return {'original_supervisor_result': result, 'observation': observation,
            'original_primary_terminal': terminal}


def main():
    cfg = cfgrow = grant = owner = attempt = None
    before = primary = post = None
    primary_error = authority_post_error = post_error = capture_error = None
    result = {'status': 'FAIL', 'native_pool_TCP_provider_readers': 'NOT_MEASURED_HOLD',
              'actual_native_Action_lease': 'NOT_RUN_HOLD', 'full': 'NOT_RUN_HOLD'}
    try:
        cfg, cfgrow, grant = authority(sys.argv)
        owner = module_from_verified(cfg['owner_boundary'], 'owned_source_boundary')
        import psutil
        owner.enable_exclusive_subreaper(psutil)
        attempt = Path(cfg['outputs']['attempt'])
        assert not attempt.exists() and not attempt.is_symlink()
        attempt.mkdir(mode=0o700)
        os.umask(0o077)
        parent = psutil.Process(os.getpid())
        owner.durable_json(attempt/'original-parent-lease.json', {
            'schema': 1, 'owner': {'pid': parent.pid, 'create_time': parent.create_time()},
            'source': cfg['source'], 'tree': cfg['tree'], 'config_sha256': cfgrow['sha256'],
            'root_release_sha256': sys.argv[5], 'argv': sys.argv,
        })
        env = os.environ.copy()
        guard = [sys.executable, cfg['guard']['path'], cfgrow['path'], cfgrow['sha256']]
        before = owner.run_exclusive(
            ['timeout', '--signal=TERM', '--kill-after=10s', '60s', *guard, 'before'],
            cwd=cfg['source_root'], env=env, directory=attempt/'before-source-guard',
            psutil_module=psutil, execution_seconds=60, total_seconds=80)
        assert before['primary'] == 'COMMAND_PASS' and before['cleanup'] == 'PASS'
        payload = {'command': [sys.executable, cfg['primary_child']['path'], cfgrow['path'],
                               cfgrow['sha256'], str(attempt)],
                   'cwd': cfg['source_root'], 'env': env, 'timeout_seconds': 600,
                   'cleanup_grace_seconds': 10,
                   'observation_path': str(attempt/'original-supervisor-observation.json')}
        owner.durable_json(attempt/'original-supervisor-input.json', payload)
        payload_path = attempt/'original-supervisor-input.json'
        payload_sha = hashlib.sha256(payload_path.read_bytes()).hexdigest()
        # The independently scheduled GNU timeout sends TERM at630 and KILL
        # at640 even if the phase child's cooperative clock stalls. The parent
        # starts identity-safe fallback at620 and shares the final640 deadline.
        primary = owner.run_exclusive(
            ['timeout', '--signal=TERM', '--kill-after=10s', '630s', sys.executable,
             cfg['supervisor_entry']['path'], str(payload_path), payload_sha],
            cwd=cfg['source_root'], env=env, directory=attempt/'primary-enclosure',
            psutil_module=psutil, execution_seconds=620, total_seconds=640)
        result['inner_original_proof'] = primary_completed(cfg, attempt, primary)
        result['status'] = 'PASS_SOURCE_LIGHT_ONLY'
    except BaseException as error:
        primary_error = type(error).__name__
    finally:
        # This is the external parent, independent of the killed primary child.
        # Full root/reviews/self/config/input closure is attempted on EVERY
        # outcome including initial rejection. Its failure never erases primary.
        try:
            authority(sys.argv)
            result['all_outcome_authority_post'] = 'PASS'
        except BaseException as error:
            authority_post_error = type(error).__name__
            result['all_outcome_authority_post'] = 'FAIL'
        if cfg is not None and owner is not None and attempt is not None:
            try:
                guard = [sys.executable, cfg['guard']['path'], cfgrow['path'], cfgrow['sha256'], 'after']
                post = owner.run_exclusive(
                    ['timeout', '--signal=TERM', '--kill-after=10s', '60s', *guard],
                    cwd=cfg['source_root'], env=os.environ.copy(), directory=attempt/'always-post-source-guard',
                    psutil_module=psutil, execution_seconds=60, total_seconds=80)
                assert post['primary'] == 'COMMAND_PASS' and post['cleanup'] == 'PASS'
            except BaseException as error:
                post_error = type(error).__name__
        else:
            post_error = 'SOURCE_POST_NOT_ADMITTED'
        result.update(before=before, primary=primary, post=post,
                      primary_exception_type=primary_error,
                      authority_post_exception_type=authority_post_error,
                      source_post_exception_type=post_error)
        if primary_error or authority_post_error or post_error:
            result['status'] = 'FAIL'
        if owner is not None and attempt is not None:
            try:
                owner.durable_json(attempt/'original-external-parent-terminal.json', result)
            except BaseException as error:
                capture_error = type(error).__name__
                result['status'] = 'FAIL'
        result['capture_exception_type'] = capture_error
        # ROOT outer raw capture retains this even when no attempt was admitted.
        print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result['status'] == 'PASS_SOURCE_LIGHT_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
