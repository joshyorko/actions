from pathlib import Path
import hashlib
import json
import os
import re
import stat
import subprocess

ROOT = Path('/workspace/engineering/rcc-current-e4ff-control3-mode-source-diagnosis-owned')
rows = json.loads((ROOT / 'exact-source-snapshot-bindings.json').read_bytes())
source = {}
for row in rows:
    raw = (ROOT / row['snapshot']).read_bytes()
    assert len(raw) == row['bytes']
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_blob_sha']
    source[row['path']] = raw.decode()
assert '"github.com/joshyorko/rcc/cmd"' in source['cmd/rcc/main.go']
assert '"github.com/joshyorko/rcc/htfs"' in source['cmd/holotreeCatalogs.go']
assert 'func init()' in source['htfs/directory.go']
assert 'pathlib.MakeSharedDir(common.HololibCatalogLocation())' in source['htfs/directory.go']
assert 'return filepath.Join(Product.Home(), "hololib")' in source['common/variables.go']
assert 'return filepath.Join(HololibLocation(), "catalog")' in source['common/variables.go']
assert 'return makeModedDir(fullpath, 0750)' in source['pathlib/shared.go']
assert 'shared = privateSetup(1)' in source['pathlib/variables.go']
assert '_, err = shared.MakeSharedDir(filepath.Dir(fullpath))' in source['pathlib/functions.go']
assert 'return ensureCorrectMode(fullpath, stat, correct)' in source['pathlib/functions.go']
assert 'err := os.Chmod(fullpath, correct)' in source['pathlib/functions.go']
assert 'home := os.Getenv(it.HomeVariable())' in source['common/strategies.go']
assert 'ROBOCORP_HOME_VARIABLE = `ROBOCORP_HOME`' in source['common/strategies.go']
binary = Path('/workspace/actions-cloud/bin/rcc').read_bytes()
assert hashlib.sha256(binary).hexdigest() == '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
assert b'vcs.revision=4148c2b71705c9d2baf0e88b48d08a79cb7bda0f' in binary
assert b'vcs.modified=true' in binary
checkout = Path('/workspace/engineering/pr308')
fixture = checkout / 'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'
fixture_raw = fixture.read_bytes()
assert hashlib.sha256(fixture_raw).hexdigest() == 'af2f79ccd395c088076381f6681860cf8160f8fd0d9169e122634fe684c37c35'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout, text=True).strip() == 'e4ff080375a8422bb656e52d218f198521dda078'
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=checkout)
text = fixture_raw.decode()
for function in ('test_published_artifact_details_preserves_one_rcc_identity_pair', 'test_staged_package_executes_in_managed_rcc_runtime'):
    body = text.split('def ' + function + '(', 1)[1].split('\n\ndef ', 1)[0]
    assert body.index('_verify_selected_rcc_fixture(rcc_binary)') < body.index('_prepare_owned_rcc_test_package_cache(')
assert '[str(rcc_binary), "--version"]' in text.split('def _verify_selected_rcc_fixture(', 1)[1].split('\n\ndef ', 1)[0]
state = Path('/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-2')
observed = {}
for key, path in {'root': state, 'client': state/'actions-home', 'cache': state/'actions-home/pkgs', 'marker': state/'rcc-package-cache-owner.json'}.items():
    st = path.lstat()
    assert not path.is_symlink()
    observed[key] = {'mode': oct(stat.S_IMODE(st.st_mode)), 'uid': st.st_uid, 'gid': st.st_gid}
assert observed['root']['mode'] == '0o700'
assert observed['client']['mode'] == '0o750'
assert observed['cache']['mode'] == '0o700'
assert observed['marker']['mode'] == '0o600'
assert all(row['uid'] == os.getuid() and row['gid'] == os.getgid() for row in observed.values())
assert all((state/'actions-home/hololib'/name).is_dir() for name in ('catalog', 'library', 'used', 'pids'))
proof = {'schema': 1, 'status': 'SOURCE_SUPPORTED_NATIVE_HOME_MODE_BOUNDARY', 'source_blobs_verified': len(rows), 'approved_binary_sha256': hashlib.sha256(binary).hexdigest(), 'embedded_revision': '4148c2b71705c9d2baf0e88b48d08a79cb7bda0f', 'embedded_modified': True, 'exact_compiled_source_equivalence': 'UNKNOWN', 'fixture_sha256': hashlib.sha256(fixture_raw).hexdigest(), 'both_fixture_probes_precede_home_admission': True, 'observed_metadata': observed, 'native_execution_by_reviewer': False, 'runtime_syscall_attribution': 'UNKNOWN'}
out = ROOT/'independent-readonly-source-mode-proof.json'
assert not out.exists()
out.write_text(json.dumps(proof, indent=2, sort_keys=True)+'\n')
out.chmod(0o400)
print(json.dumps({'proof_bytes': out.stat().st_size, 'proof_sha256': hashlib.sha256(out.read_bytes()).hexdigest()}))
