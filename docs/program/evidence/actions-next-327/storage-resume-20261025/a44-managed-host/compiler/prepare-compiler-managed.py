"""Measured low-capacity managed-UI preparation; original strict recipe unchanged."""
import argparse
import ctypes
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

SOURCE = 'd0c87a38a937cc339e8e661ac453c7a62ed41fa6'
CORE = '718ea63637f096d26c4de5f82ca736eec1358b197d0a63883c063ad205e0860e'
RCC = '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
YAML = 'f7b4173c11a7eef06cf2ecc526d15a7f069efdd4d465f65cb0fb6258d258b4a8'
PACKAGE = b'name: generated-v2-report\ndescription: Synthetic bounded v2 report\ndependencies:\n  conda-forge:\n    - python=3.12\n  pypi:\n    - actions-core=1.1.0a6\n'
LIMIT = 12 * 1024**2

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def used(root):
    seen, total = set(), 0
    for directory, _, names in os.walk(root):
        for name in names:
            try:
                st = os.lstat(Path(directory) / name)
            except FileNotFoundError:
                continue
            identity = (st.st_dev, st.st_ino)
            if identity not in seen:
                total += st.st_blocks * 512
                seen.add(identity)
    return total

def sanitize(raw):
    text = raw.decode('utf-8', 'replace')
    text = re.sub(r'(https?://)[^/\s@]+@', r'\1<redacted>@', text)
    text = re.sub(r'(?i)(authorization:\s*(?:bearer|basic)\s+)\S+', r'\1<redacted>', text)
    return text.encode()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate-base', type=Path, required=True)
    parser.add_argument('--compiler-root', type=Path, required=True)
    args = parser.parse_args()
    candidate, root = args.candidate_base.resolve(), args.compiler_root.absolute()
    assert sys.platform == 'linux' and sys.flags.isolated, 'Linux isolated consumer interpreter required'
    assert Path(sys.prefix).resolve() == (candidate / 'consumer').resolve(), 'Use candidate consumer Python'
    assert (candidate / 'source-sha.txt').read_text().strip() == SOURCE
    import actions.server
    import importlib.metadata
    assert importlib.metadata.version("actions-runtime") == "1.1.0a44"
    assert importlib.metadata.version("actions-core") == "1.1.0a6"
    runtime_wheels = list((candidate / "wheels").rglob("actions_runtime-1.1.0a44-*.whl"))
    assert len(runtime_wheels) == 1 and sha(runtime_wheels[0]) == "1502214a6a6319521984d554244aca502659fc919d5a31bac94727d3e534104c"
    from actions.server.deployments.package_revision_compiler import PreparedRccEnvironment, RccBuildIdentity, load_prepared_rcc_environment
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor, build_exec_command, read_receipt
    package_dir = Path(actions.server.__file__).resolve().parent
    assert package_dir.is_relative_to(candidate / 'consumer'), 'Installed candidate Runtime required'
    rcc = package_dir / 'bin/rcc-18.19.3'
    assert sha(rcc) == RCC and os.access(rcc, os.X_OK), 'Bundled RCC bytes/executable mismatch'
    wheels = list((candidate / 'wheels').rglob('actions_core-1.1.0a6-py3-none-any.whl'))
    assert len(wheels) == 1 and sha(wheels[0]) == CORE, 'Exact Core wheel required'
    assert hashlib.sha256(PACKAGE).hexdigest() == YAML
    assert not root.exists() and not root.is_symlink(), 'Compiler root must be fresh'
    assert root.parent.is_dir() and shutil.disk_usage(root.parent).free >= 17 * 1024**3 // 4
    root.mkdir(mode=0o700)
    for part in ('home', 'tmp', 'actions-home', 'robocorp/wheels'):
        (root / part).mkdir(parents=True, mode=0o700)
    (root / 'package.yaml').write_bytes(PACKAGE)
    shutil.copyfile(wheels[0], root / 'robocorp/wheels' / wheels[0].name)
    shutil.copyfile(Path(__file__).with_name('verify-core.py'), root / 'verify-core.py')
    env = {'HOME':str(root/'home'), 'PATH':'/usr/local/bin:/usr/sbin:/sbin:/usr/bin:/bin', 'ROBOCORP_HOME':str(root/'robocorp'), 'ACTIONS_HOME':str(root/'actions-home'), 'PIP_FIND_LINKS':str(root/'robocorp/wheels'), 'TMPDIR':str(root/'tmp'), 'LANG':'C.UTF-8','LC_ALL':'C.UTF-8'}
    for key, value in os.environ.items():
        if key.lower() in ('http_proxy','https_proxy','all_proxy','no_proxy') or key in ('SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE'):
            if key.lower() != 'no_proxy' and key.lower().endswith('_proxy'):
                assert not urlsplit(value).username and not urlsplit(value).password, 'Authenticated proxy cannot be copied'
            env[key] = value
    libc = ctypes.CDLL(None)
    previous = ctypes.c_int()
    assert libc.prctl(37, ctypes.byref(previous), 0, 0, 0) == 0
    assert libc.prctl(36, 1, 0, 0, 0) == 0
    log_bytes = 0
    sampled_peak = 0
    minimum_free = shutil.disk_usage(root).free
    phases = []
    def budget():
        nonlocal sampled_peak, minimum_free
        allocation = used(root)
        free = shutil.disk_usage(root).free
        sampled_peak = max(sampled_peak, allocation)
        minimum_free = min(minimum_free, free)
        assert free >= 1024**3, 'Consumer disk floor'
        assert allocation < 2*1024**3, 'Compiler lane disk cap'
        return allocation
    def run(command, label, timeout):
        nonlocal log_bytes
        deadline = time.monotonic() + timeout
        proc = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        output = bytearray()
        selector = selectors.DefaultSelector()
        streams = {}
        try:
            for name, stream in (('stdout', proc.stdout), ('stderr', proc.stderr)):
                streams[name] = (root / f'{label}.{name}.log').open('wb')
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or proc.poll() is None:
                assert time.monotonic() < deadline, f'{label} timeout'
                budget()
                for key, _ in selector.select(0.2):
                    raw = os.read(key.fd, 65536)
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    log_bytes += len(raw)
                    assert log_bytes <= LIMIT, 'Combined log cap'
                    streams[key.data].write(sanitize(raw))
                    if key.data == 'stdout':
                        output.extend(raw)
            assert proc.returncode == 0, f'{label} nonzero exit; inspect bounded sanitized logs'
            return bytes(output)
        finally:
            cleanup_errors=[]
            try:
                try:os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:pass
            except BaseException as exc:cleanup_errors.append(('group-stop',type(exc).__name__))
            try:proc.wait(timeout=10)
            except BaseException as exc:cleanup_errors.append(('wait',type(exc).__name__))
            try:
                import psutil
                owned = psutil.Process().children(recursive=True)
                for child in owned:
                    try:child.kill()
                    except psutil.NoSuchProcess:pass
                _, alive = psutil.wait_procs(owned, timeout=10)
                assert not alive, 'Owned descendants not reaped'
                while True:
                    try:
                        if not os.waitpid(-1, os.WNOHANG)[0]:break
                    except ChildProcessError:break
            except BaseException as exc:cleanup_errors.append(('descendants',type(exc).__name__))
            try:selector.close()
            except BaseException as exc:cleanup_errors.append(('selector-close',type(exc).__name__))
            for stream in [*streams.values(),proc.stdout,proc.stderr]:
                try:stream.close()
                except BaseException as exc:cleanup_errors.append(('stream-close',type(exc).__name__))
            try:allocation=budget()
            except BaseException as exc:
                cleanup_errors.append(('final-budget',type(exc).__name__))
                allocation=used(root)
            phases.append({'phase':label,'returncode':proc.returncode,'retained_allocated_bytes':allocation,'sampled_peak_allocated_bytes':sampled_peak,'minimum_free_bytes':minimum_free,'cleanup_errors':cleanup_errors})
            (root/'capacity.json').write_text(json.dumps({'scope':'a44-managed-ui-only-v1; sampled allocations; not proof of an unsampled peak','sample_interval_seconds':0.2,'phases':phases},indent=2)+'\n')
            if cleanup_errors:raise RuntimeError('Compiler cleanup/budget failure; inspect sanitized capacity receipt')
    try:
        assert run([str(rcc),'--version'], 'version', 30).strip() == b'v18.19.3'
        raw = run([str(rcc),'env','publish','--environment',str(root/'package.yaml'),'--json','--provider','local'], 'publish', 600)
        rows = []
        for line in raw.splitlines():
            try: value = json.loads(line)
            except (ValueError, UnicodeError): continue
            if isinstance(value,dict) and {'specificationDigest','artifactDigest'} <= value.keys(): rows.append(value)
        assert len(rows) == 1, 'Exactly one observed local publish result required'
        row = rows[0]
        for key in ('specificationDigest','artifactDigest'):
            assert re.fullmatch(r'sha256:[0-9a-f]{64}', row[key])
        prepared = PreparedRccEnvironment(root/'robocorp','sha256:'+YAML,RccBuildIdentity(row['specificationDigest'],row['artifactDigest']))
        (root/'prepared.json').write_bytes(prepared.to_receipt_bytes())
        (root/'prepared.json').chmod(0o600)
        assert load_prepared_rcc_environment(root/'prepared.json') == prepared
        descriptor = RccRuntimeDescriptor(artifact_digest=row['artifactDigest'], source_generation='core-wheel-verification', source_hash='sha256:'+YAML, environment_fingerprint=row['specificationDigest'].removeprefix('sha256:'), preparation_class='warm-reuse', provider_reference='local')
        command = build_exec_command(rcc, descriptor, ['python','-I',str(root/'verify-core.py'),str(root)], receipt_file=root/'core-exec-qualified.json', local_trust_carrier=root/'robocorp/artifacts/v1/trust')
        command.insert(command.index('--'), '--no-build')
        env['RCC_NO_BUILD'] = '1'
        run(command, 'proof', 180)
        read_receipt(root/'core-exec-qualified.json', row['artifactDigest'])
        proof = json.loads((root/'core-proof.json').read_text())
        assert proof['status']=='PASS' and proof['python_members_verified']==82 and proof['payload_members_verified']==87 and proof['isolated']
        result = {'candidate_source':SOURCE,'core_wheel_sha256':CORE,'rcc':str(rcc),'rcc_sha256':RCC,'rcc_version':'v18.19.3','prepared_receipt':str(root/'prepared.json'),'robocorp_home':str(root/'robocorp'),'package_yaml_digest':'sha256:'+YAML,'specificationDigest':row['specificationDigest'],'artifactDigest':row['artifactDigest'],'core_proof_sha256':sha(root/'core-proof.json'),'prepared_receipt_sha256':sha(root/'prepared.json')}
        result.update(capacity_profile='a44-managed-ui-only-v1', source_sha=SOURCE, runtime_version='1.1.0a44', core_version='1.1.0a6', compiler_artifact_digest=row['artifactDigest'], compiler_core_wheel_sha256=CORE, compiler_core_bytes_verified=True, compiler_core_receipt=str(root/'core-proof.json'), compiler_core_receipt_sha256=sha(root/'core-proof.json'))
        (root/'target-config-fragment.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
        print(json.dumps(result,sort_keys=True))
    finally:
        assert libc.prctl(36,previous.value,0,0,0)==0

if __name__ == '__main__':
    main()
