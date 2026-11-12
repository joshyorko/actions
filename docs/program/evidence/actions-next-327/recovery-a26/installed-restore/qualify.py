"""Installed legacy SQLite queue subgate. No full Runtime restore claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PAYLOAD = {"synthetic": True, "purpose": "installed-restore-327"}
ATTACHMENT = b"synthetic retained attachment\n"


def inventory(root):
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError('symlink in fixture')
        if p.is_file():
            result[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def worker(args):
    import importlib.metadata as md
    import actions.server
    version = md.version('actions-runtime')
    assert version == args.version, (version, args.version)
    origin = Path(actions.server.__file__).resolve()
    assert origin.is_relative_to(Path(sys.prefix).resolve()), origin
    info = {'version': version, 'module': str(origin), 'python': sys.executable}
    if args.operation == 'inspect':
        print(json.dumps(info)); return
    root = Path(args.datadir)
    if args.operation in ('capture', 'restore'):
        from dataclasses import asdict
        from actions.server._datadir_restore import (
            capture_offline_manifest, restore_offline, OfflineManifest, Member,
        )
        if args.operation == 'capture':
            manifest = capture_offline_manifest(root, offline=True,
                                                original_datadir=Path(args.original))
            print(json.dumps({'manifest': asdict(manifest), 'sha256': manifest.sha256}))
        else:
            pinned = json.loads(Path(args.manifest).read_text())
            raw = pinned['manifest']
            manifest = OfflineManifest(raw['source'], raw['original_datadir'],
                tuple(Member(m['path'], tuple(m['identity']), m['sha256']) for m in raw['members']))
            assert manifest.sha256 == pinned['sha256']
            print(json.dumps(asdict(restore_offline(manifest, root, offline=True))))
        return
    from actions.server._work_items_import import load_work_items_types
    adapter_type, _ = load_work_items_types()
    if args.operation == 'refuse-schema-6':
        import sqlite3
        with sqlite3.connect((root / 'workitems.db').as_uri() + '?mode=ro', uri=True) as db:
            assert db.execute('SELECT MAX(version) FROM schema_version').fetchone() == (6,)
        assert version == '1.0.4' and md.version('actions-work-items') == '0.4.4'
        try:
            adapter_type(db_path=str(root / 'workitems.db'), files_dir=str(root / 'work_item_files'))
        except ValueError as exc:
            assert str(exc) == 'Database schema version 6 is newer than supported version 5'
            print(json.dumps(dict(info, status='EXPECTED_REFUSAL', schema=6, supported_schema=5)))
            return
        raise AssertionError('schema6 was unexpectedly admitted by schema5 consumer')
    adapter = adapter_type(db_path=str(root / 'workitems.db'),
                           files_dir=str(root / 'work_item_files'))
    if args.operation == 'seed':
        item = adapter.seed_input(PAYLOAD)
        adapter.add_file(item, 'report.txt', 'report.txt', ATTACHMENT)
        print(json.dumps(dict(info, item=item)))
    else:
        assert adapter.load_payload(args.item) == PAYLOAD
        assert adapter.get_file(args.item, 'report.txt') == ATTACHMENT
        print(json.dumps(dict(info, item=args.item, attachment_sha256=hashlib.sha256(ATTACHMENT).hexdigest())))


def main(args):
    out = Path(args.output).absolute()
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('PYTHON', 'ACTIONS_', 'RC_', 'ROBOCORP_')):
            env.pop(key)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    def run(name, python, version, op, datadir, *extra, allow_failure=False):
        command = [python, '-I', '-B', str(Path(__file__).resolve()), '--operation', op,
                   '--version', version, '--datadir', str(datadir), *extra]
        p = subprocess.run(command, cwd=out, env=env, capture_output=True, text=True, timeout=120)
        (out / (name + '.json')).write_text(json.dumps({'command': command, 'returncode': p.returncode,
                                                     'stdout': p.stdout, 'stderr': p.stderr}, indent=2))
        if not allow_failure:
            assert p.returncode == 0, name
        return p
    legacy, candidate = args.legacy_python, args.candidate_python
    live = out / 'legacy'; live.mkdir()
    item = json.loads(run('01-seed', legacy, args.legacy_version, 'seed', live).stdout)['item']
    run('02-restart', legacy, args.legacy_version, 'read', live, '--item', item)
    # Every process exited: snapshot is detached and exclusively owned.
    backup = out / 'backup'; shutil.copytree(live, backup)
    pinned = run('03-pin', candidate, args.candidate_version, 'capture', backup, '--original', str(live))
    manifest = out / 'manifest.json'; manifest.write_text(pinned.stdout)
    before = inventory(backup)
    run('04-upgrade', candidate, args.candidate_version, 'read', live, '--item', item)
    run('05-upgrade-restart', candidate, args.candidate_version, 'read', live, '--item', item)
    restored = out / 'restored'
    run('06-restore', candidate, args.candidate_version, 'restore', restored, '--manifest', str(manifest))
    run('07-restored-read', candidate, args.candidate_version, 'read', restored, '--item', item)
    run('08-restored-restart', candidate, args.candidate_version, 'read', restored, '--item', item)
    assert inventory(backup) == before
    # Downgrade only a disposable copy; never the retained snapshot or upgraded fixture.
    down = out / 'downgrade'; shutil.copytree(live, down)
    # Absolute legacy attachment path still points into live: downgrade proves payload/schema
    # readback only unless relocation is performed first.
    down_manifest = run('09-downgrade-pin', candidate, args.candidate_version, 'capture', down, '--original', str(live))
    down_pin = out / 'downgrade-manifest.json'; down_pin.write_text(down_manifest.stdout)
    down_target = out / 'downgrade-relocated'
    run('10-downgrade-relocate', candidate, args.candidate_version, 'restore', down_target, '--manifest', str(down_pin))
    down_before = inventory(down_target)
    p = run('11-downgrade', legacy, args.legacy_version, 'read', down_target, '--item', item, allow_failure=True)
    classification = 'legacy-queue-readback-supported' if p.returncode == 0 else 'UNQUALIFIED_FAILURE'
    if p.returncode != 0:
        assert args.legacy_version == '1.0.4'
        run('11b-exact-schema-refusal', legacy, args.legacy_version, 'refuse-schema-6', down_target)
        assert inventory(down_target) == down_before, 'refusal mutated candidate fixture'
        classification = 'EXACT_SCHEMA_6_REFUSAL_BY_SCHEMA_5_CONSUMER'
    rollback = out / 'pre-upgrade-rollback'
    run('12-preupgrade-restore', candidate, args.candidate_version, 'restore', rollback, '--manifest', str(manifest))
    run('13-old-rollback-read', legacy, args.legacy_version, 'read', rollback, '--item', item)
    run('14-old-rollback-restart', legacy, args.legacy_version, 'read', rollback, '--item', item)
    assert inventory(backup) == before
    (out / 'summary.json').write_text(json.dumps({'status':'PASS', 'scope': 'installed legacy local queue and attachment subset',
        'downgrade': classification, 'refusal_fixture_unchanged': inventory(down_target) == down_before,
        'old_consumer_preupgrade_backup_rollback':'PASS', 'snapshot_unchanged': inventory(backup) == before,
        'full_runtime_restore': 'NOT_QUALIFIED', 'safe_refusal': 'exact Runtime1.0.4/SDK0.4.4 schema6-versus5 ValueError assertion; no general failure waiver'}, indent=2))



if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('operation', 'version', 'datadir', 'original', 'manifest', 'item',
                 'legacy-python', 'candidate-python', 'output'):
        p.add_argument('--' + name)
    p.add_argument('--legacy-version', default='1.0.4')
    p.add_argument('--candidate-version', default='1.1.0a26')
    args = p.parse_args()
    if args.operation:
        worker(args)
    else:
        if not all((args.legacy_python, args.candidate_python, args.output)):
            p.error('supply installed legacy/candidate interpreters and absent output directory')
        main(args)
