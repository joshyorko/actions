import argparse
import ast
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tarfile
import tempfile
import types
import unittest

HERE = Path(__file__).parent
PARENT = Path('/tmp/actions-capacity-recovery-batch19.py')
ADDITION = HERE / 'caps_and_prestage.py'
FIXTURE_ROOT = Path('/tmp/actions-B28-pure-controls-owned-20261011-1')
MODE = 'green'
CAP_LIMIT = 50331648


def load_case(case):
    root = FIXTURE_ROOT / case
    assert not root.exists()
    root.mkdir(mode=0o700)
    base = root / 'base'
    base.mkdir(mode=0o700)
    for name in ['r0', 'r1']:
        r = base / name
        r.mkdir(mode=0o700)
        (r / 'recycle.now').write_text('True')
        (r / 'data').write_bytes((b'owned-fixture-' + name.encode()) * 128)
        os.chmod(r / 'data', 0o600)
    tree = ast.parse(PARENT.read_text())
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            key = n.targets[0].id
            if key in ('BASE', 'DEST', 'STAGE'):
                value = base if key == 'BASE' else root / key.lower()
                n.value = ast.Call(func=ast.Name(id='Path', ctx=ast.Load()), args=[ast.Constant(str(value))], keywords=[])
            elif key == 'NAMES':
                n.value = ast.parse("['r0','r1']", mode='eval').body
    ast.fix_missing_locations(tree)
    loop = next(n for n in tree.body if isinstance(n, ast.For))
    prefix = tree.body[:tree.body.index(loop)]
    ns = {'__name__': 'controlled_owned_fixture', '__file__': str(PARENT)}
    exec(compile(ast.Module(body=prefix, type_ignores=[]), str(PARENT), 'exec'), ns)
    addition = ast.parse(ADDITION.read_text())
    declarations = addition.body[:-4]
    exec(compile(ast.Module(body=declarations, type_ignores=[]), str(ADDITION), 'exec'), ns)
    events = []
    actual_fsync = os.fsync
    def fsync(fd):
        events.append(('fsync', os.readlink('/proc/self/fd/' + str(fd))))
        return actual_fsync(fd)
    def volume(path):
        return types.SimpleNamespace(f_bavail=8 * 1024**3, f_frsize=1)
    # Fixture volume accounting is a pure boundary seam, not capacity evidence.
    ns['os'] = types.SimpleNamespace(**{k: getattr(os, k) for k in dir(os) if not k.startswith('__')})
    ns['os'].fsync = fsync
    ns['os'].statvfs = volume
    return root, ns, loop, events


def run_loop(ns, loop):
    exec(compile(ast.Module(body=[loop], type_ignores=[]), str(PARENT), 'exec'), ns)


def install_new(ns):
    ns['_prestage_all']()
    ns['DEST'] = ns['_IndexBudgetPath'](str(ns['DEST']))
    ns['shutil'] = ns['_GuardedShutil']()
    ns['tarfile'] = ns['_ReadOnlyTar']()


def rewrite(archive, mutate):
    records = []
    with tarfile.open(archive, 'r:gz') as h:
        for m in h.getmembers():
            body = h.extractfile(m).read() if m.isfile() else None
            records.append((copy.deepcopy(m), body))
    with tarfile.open(archive, 'w:gz', dereference=False) as h:
        for m, body in records:
            m, body = mutate(m, body)
            h.addfile(m, io.BytesIO(body) if body is not None else None)


class BaselineContract(unittest.TestCase):
    def test_all_originals_remain_on_later_archive_error(self):
        root, ns, loop, events = load_case('all_originals_' + MODE)
        real = tarfile.open
        def opened(*args, **kwargs):
            if len(args) > 1 and args[1] == 'w:gz' and Path(args[0]).name == 'r1.tar.gz':
                raise RuntimeError('OWNED_SECOND_ARCHIVE_FAILURE')
            return real(*args, **kwargs)
        if MODE == 'red':
            ns['tarfile'] = types.SimpleNamespace(open=opened)
            with self.assertRaises(RuntimeError):
                run_loop(ns, loop)
        else:
            ns['_CAP'] = 1
            with self.assertRaisesRegex(RuntimeError, 'CAP_EXCEEDED'):
                install_new(ns)
        self.assertTrue((ns['BASE'] / 'r0').exists())
        self.assertTrue((ns['BASE'] / 'r1').exists())

    def test_original_verifier_refuses_poisoned_mtime(self):
        root, ns, loop, events = load_case('mtime_' + MODE)
        r = ns['BASE'] / 'r0'
        snapshot = ns['_snapshot'](r)
        archive = root / 'poison.tar.gz'
        with tarfile.open(archive, 'w:gz') as h:
            def wrong(m):
                m.pax_headers['mtime'] = ns['_ns_text'](snapshot['root']['mtime_ns'] + 1)
                return m
            h.add(r, arcname='r0', filter=wrong)
        with self.assertRaises(AssertionError):
            if MODE == 'red':
                ns['verify'](archive, 'r0', snapshot['entries'])
            else:
                ns['_strict_verify'](archive, 'r0', snapshot)

    def test_durable_index_before_removal(self):
        root, ns, loop, events = load_case('durability_' + MODE)
        if MODE == 'red':
            real = shutil.rmtree
            def remove(r):
                events.append(('remove', str(r)))
                return real(r)
            ns['shutil'] = types.SimpleNamespace(copyfile=shutil.copyfile, rmtree=remove)
            run_loop(ns, loop)
            before = events[:next(i for i, e in enumerate(events) if e[0] == 'remove')]
            self.assertTrue(any(e[0] == 'fsync' and 'inventory' in e[1] for e in before))
        else:
            install_new(ns)
            self.assertTrue(any(e[0] == 'fsync' and 'prestage' in e[1] for e in events))
            run_loop(ns, loop)
            self.assertFalse((ns['BASE'] / 'r0').exists())
            self.assertFalse((ns['BASE'] / 'r1').exists())


class GreenBoundaries(unittest.TestCase):
    def case(self, name):
        return load_case(name)
    def test_cap_below_equal_above(self):
        root, ns, loop, events = self.case('direct_cap')
        target = io.BytesIO(); counter = [0]
        w = ns['_CappedWriter'](target, counter, 4)
        self.assertEqual(w.write(b'ab'), 2)
        self.assertEqual(w.write(b'cd'), 2)
        with self.assertRaisesRegex(RuntimeError, 'CAP_EXCEEDED'):
            w.write(b'e')
        self.assertEqual(target.getvalue(), b'abcd'); self.assertEqual(counter, [4])
    def test_aggregate_second_writer(self):
        root, ns, loop, events = self.case('aggregate_counter')
        counter = [0]; first = io.BytesIO(); second = io.BytesIO()
        ns['_CappedWriter'](first, counter, 3).write(b'ab')
        with self.assertRaisesRegex(RuntimeError, 'CAP_EXCEEDED'):
            ns['_CappedWriter'](second, counter, 3).write(b'cd')
        self.assertEqual(first.getvalue(), b'ab'); self.assertEqual(second.getvalue(), b'')
    def test_short_write_refused(self):
        root, ns, loop, events = self.case('short_write')
        class Short:
            def write(self, data): return len(data) - 1
        with self.assertRaisesRegex(RuntimeError, 'SHORT_ARCHIVE_WRITE'):
            ns['_CappedWriter'](Short(), [0], 100).write(b'ab')
    def test_gzip_footer_overflow_keeps_partial(self):
        root, ns, loop, events = self.case('footer_overflow')
        target = io.BytesIO(); counter = [0]
        with self.assertRaisesRegex(RuntimeError, 'CAP_EXCEEDED'):
            with gzip.GzipFile(fileobj=ns['_CappedWriter'](target, counter, 15), mode='wb') as h:
                h.write(b'payload')
        self.assertGreater(len(target.getvalue()), 0); self.assertLessEqual(len(target.getvalue()), 15)
    def test_aggregate_failure_keeps_all_roots_and_partials(self):
        root, ns, loop, events = self.case('aggregate_phase_failure')
        # Pin a real first-archive bound; second cannot fit this aggregate cap.
        install_new(ns)
        first = (ns['STAGE'] / 'r0.tar.gz').stat().st_size
        other, fresh, loop2, events2 = self.case('aggregate_phase_failure_fresh')
        fresh['_CAP'] = first + 64
        with self.assertRaisesRegex(RuntimeError, 'CAP_EXCEEDED'):
            install_new(fresh)
        self.assertTrue((fresh['BASE'] / 'r0').exists()); self.assertTrue((fresh['BASE'] / 'r1').exists())
        self.assertTrue((fresh['STAGE'] / 'r0.tar.gz').exists()); self.assertTrue((fresh['STAGE'] / 'r1.tar.gz').exists())
        self.assertFalse(fresh['_FULL_INDEX'].exists())
    def test_index_cap_before_any_removal(self):
        root, ns, loop, events = self.case('index_cap')
        ns['_INDEX_CAP'] = 1
        with self.assertRaisesRegex(RuntimeError, 'CAP_EXCEEDED'):
            install_new(ns)
        self.assertTrue((ns['BASE'] / 'r0').exists()); self.assertTrue((ns['BASE'] / 'r1').exists())
        self.assertTrue(ns['_FULL_INDEX'].exists())
    def test_index_fsync_failure_before_removal(self):
        root, ns, loop, events = self.case('index_fsync_failure')
        real = ns['os'].fsync
        sentinel = RuntimeError('OWNED_INDEX_FSYNC_FAILURE')
        def fsync(fd):
            if 'private-complete-prestage' in os.readlink('/proc/self/fd/' + str(fd)): raise sentinel
            return real(fd)
        ns['os'].fsync = fsync
        try: install_new(ns)
        except RuntimeError as got: self.assertIs(got, sentinel)
        else: self.fail('Missing index failure')
        self.assertTrue((ns['BASE'] / 'r0').exists()); self.assertTrue((ns['BASE'] / 'r1').exists())
    def test_progress_cap_retains_complete_index_and_original(self):
        root, ns, loop, events = self.case('progress_cap')
        install_new(ns)
        ns['_INDEX_CAP'] = ns['_FULL_INDEX'].stat().st_size
        with self.assertRaisesRegex(AssertionError, 'INDEX_CAP'):
            run_loop(ns, loop)
        self.assertTrue((ns['BASE'] / 'r0').exists()); self.assertTrue(ns['_FULL_INDEX'].exists())
        self.assertFalse((ns['DEST'] / 'private-complete-inventory-and-recovery.json').exists())
    def test_source_change_refuses_copy_removal(self):
        root, ns, loop, events = self.case('changed_original')
        install_new(ns); (ns['BASE'] / 'r0' / 'data').write_bytes(b'changed')
        with self.assertRaises(AssertionError): run_loop(ns, loop)
        self.assertTrue((ns['BASE'] / 'r0').exists())
    def test_missing_stage_cannot_create_uncapped_archive(self):
        root, ns, loop, events = self.case('missing_stage')
        install_new(ns); (ns['STAGE'] / 'r0.tar.gz').unlink()
        with self.assertRaisesRegex(AssertionError, 'UNSTAGED_ARCHIVE'): run_loop(ns, loop)
        self.assertTrue((ns['BASE'] / 'r0').exists())
    def test_unknown_root_removal_refused(self):
        root, ns, loop, events = self.case('wrong_root')
        install_new(ns)
        with self.assertRaisesRegex(AssertionError, 'UNOWNED_REMOVAL'): ns['shutil'].rmtree(root)
        self.assertTrue(root.exists())
    def test_marker_false_refuses_prestage(self):
        root, ns, loop, events = self.case('marker_false')
        (ns['BASE'] / 'r0' / 'recycle.now').write_text('False')
        with self.assertRaises(AssertionError): install_new(ns)
        self.assertTrue((ns['BASE'] / 'r0').exists())
    def test_external_hardlink_refused(self):
        root, ns, loop, events = self.case('external_hardlink')
        os.link(ns['BASE'] / 'r0' / 'data', root / 'external')
        with self.assertRaisesRegex(AssertionError, 'EXTERNAL_HARDLINK'): install_new(ns)
        self.assertTrue((ns['BASE'] / 'r0').exists())
    def test_all_types_internal_hardlink_exact_ns(self):
        root, ns, loop, events = self.case('all_types')
        r = ns['BASE'] / 'r0'; (r / 'nested').mkdir(); os.symlink('data', r / 'link'); os.link(r / 'data', r / 'linked'); os.mkfifo(r / 'fifo')
        os.utime(r / 'data', ns=(1700000000123456789, 1700000000123456789))
        install_new(ns); run_loop(ns, loop)
        self.assertFalse(r.exists())
    def test_ns_text_negative_and_fractional(self):
        root, ns, loop, events = self.case('ns_text')
        self.assertEqual(ns['_ns_text'](-1), '-0.000000001')
        self.assertEqual(ns['_ns_text'](1700000000123456789), '1700000000.123456789')
    def test_floor_refusal_keeps_originals(self):
        root, ns, loop, events = self.case('floor_refusal')
        ns['os'].statvfs = lambda p: types.SimpleNamespace(f_bavail=1, f_frsize=1)
        with self.assertRaises(AssertionError): install_new(ns)
        self.assertTrue((ns['BASE'] / 'r0').exists()); self.assertFalse(ns['STAGE'].exists())
    def test_partial_progress_failure_keeps_full_index_and_original(self):
        root, ns, loop, events = self.case('partial_progress_failure')
        install_new(ns); real = ns['os'].fsync; sentinel = OSError('OWNED_PROGRESS_FSYNC_FAILURE')
        def fsync(fd):
            if 'private-complete-inventory-and-recovery.json' in os.readlink('/proc/self/fd/' + str(fd)): raise sentinel
            return real(fd)
        ns['os'].fsync = fsync
        try: run_loop(ns, loop)
        except OSError as got: self.assertIs(got, sentinel)
        else: self.fail('Missing progress failure')
        self.assertTrue((ns['BASE'] / 'r0').exists()); self.assertTrue(ns['_FULL_INDEX'].exists())
    def test_bad_archive_cases(self):
        mutations = ['body', 'type', 'mode', 'uid', 'gid', 'mtime', 'link', 'duplicate', 'escape', 'CRC']
        for kind in mutations:
            with self.subTest(kind=kind):
                root, ns, loop, events = self.case('poison_' + kind)
                os.symlink('data', ns['BASE'] / 'r0' / 'link'); install_new(ns)
                p = ns['STAGE'] / 'r0.tar.gz'
                if kind == 'CRC':
                    b = bytearray(p.read_bytes()); b[-8] ^= 1; p.write_bytes(b)
                else:
                    def change(m, body):
                        if m.name.endswith('/data'):
                            if kind == 'body': body = b'Z' * len(body)
                            elif kind == 'type': m.type = tarfile.FIFOTYPE; m.size = 0; body = None
                            elif kind == 'mode': m.mode ^= 0o100
                            elif kind == 'uid': m.uid += 1
                            elif kind == 'gid': m.gid += 1
                            elif kind == 'mtime': m.pax_headers['mtime'] = str(float(m.pax_headers['mtime']) + 1)
                            elif kind == 'escape': m.name = 'r0/../escape'
                        if kind == 'link' and m.issym(): m.linkname = 'wrong'
                        return m, body
                    rewrite(p, change)
                    if kind == 'duplicate':
                        # Append a duplicate by rebuilding an admitted root/member stream.
                        with tarfile.open(p, 'r:gz') as h: rec = [(copy.deepcopy(m), h.extractfile(m).read() if m.isfile() else None) for m in h]
                        with tarfile.open(p, 'w:gz') as h:
                            for m, body in rec + [rec[-1]]: h.addfile(m, io.BytesIO(body) if body is not None else None)
                with self.assertRaises((AssertionError, OSError, tarfile.TarError)):
                    ns['_strict_verify'](p, 'r0', ns['_ROOT_SNAPSHOTS']['r0'])
                self.assertTrue((ns['BASE'] / 'r0').exists())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--baseline-red', action='store_true'); args = parser.parse_args()
    MODE = 'red' if args.baseline_red else 'green'
    if not FIXTURE_ROOT.exists(): FIXTURE_ROOT.mkdir(mode=0o700)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BaselineContract)
    if not args.baseline_red: suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(GreenBoundaries))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
