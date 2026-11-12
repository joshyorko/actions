"""Root-only Data controller: existing TLS fixture, then bounded installed harness."""
import argparse
import hashlib
import importlib
import json
import os
import re
from uuid import uuid4
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


def exception_diagnostic(exc, depth=0):
    """Bounded classes and frame locations only; never exception messages or locals."""
    result = {'type': type(exc).__module__ + '.' + type(exc).__qualname__}
    frames = []
    tb = exc.__traceback__
    while tb is not None and len(frames) < 24:
        frames.append({'file': Path(tb.tb_frame.f_code.co_filename).name,
                       'function': tb.tb_frame.f_code.co_name, 'line': tb.tb_lineno})
        tb = tb.tb_next
    result['frames'] = frames
    if depth < 4:
        cause = exc.__cause__ or (None if exc.__suppress_context__ else exc.__context__)
        if cause is not None:
            result['cause'] = exception_diagnostic(cause, depth + 1)
        if isinstance(exc, BaseExceptionGroup):
            result['children'] = [exception_diagnostic(child, depth + 1)
                                  for child in exc.exceptions[:8]]
    return result


class OwnedFixtureContainer:
    """Track one exact pinned docker run even when the fixture never yields."""
    IMAGE = 'postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'

    def __init__(self, root, run):
        self.run_command = run
        self.cidfile = root / 'owned-container.cid'
        self.name = 'actions-data-' + uuid4().hex
        self.attempted = False
        self.uncertain = False
        self.container_id = None
        self.cleanup_steps = []

    def run(self, command, *args, **kwargs):
        kwargs.setdefault('timeout', 60)
        if list(command[:2]) != ['docker', 'run']:
            return self.run_command(command, *args, **kwargs)
        if self.attempted or self.IMAGE not in command or '--cidfile' in command or '--name' in command:
            raise RuntimeError('Unexpected container launch')
        self.attempted = True
        scoped = [*command[:2], '--cidfile', str(self.cidfile), '--name', self.name, *command[2:]]
        try:
            result = self.run_command(scoped, *args, **kwargs)
            self.capture_id()
            return result
        except BaseException as exc:
            self.uncertain = not isinstance(exc, subprocess.CalledProcessError)
            self.capture_id()
            raise

    def capture_id(self):
        if self.cidfile.exists():
            value = self.cidfile.read_text().strip()
            if not re.fullmatch('[0-9a-f]{64}', value):
                raise RuntimeError('Invalid owned container identity')
            self.container_id = value

    def inspect(self, target, timeout=10):
        deadline = time.monotonic() + timeout
        result = self.run_command(['docker', 'inspect', '--type', 'container', target],
                                  capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            # Confirm absence through a separate scoped daemon query. This also
            # handles Docker CLI stderr variants without retaining raw output.
            selector = 'id=' + self.container_id if self.container_id else 'name=^/' + self.name + '$'
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Owned inspection deadline expired')
            listing = self.run_command(
                ['docker', 'container', 'ls', '-a', '--no-trunc', '--filter', selector, '--format', '{{.ID}}'],
                capture_output=True, text=True, timeout=remaining)
            if listing.returncode == 0 and not listing.stdout.strip():
                return None
            raise RuntimeError('Owned container inspection failed')
        rows = json.loads(result.stdout)
        if len(rows) != 1 or rows[0]['Name'] != '/' + self.name:
            raise RuntimeError('Owned container name mismatch')
        value = rows[0]['Id']
        if not re.fullmatch('[0-9a-f]{64}', value):
            raise RuntimeError('Invalid inspected container identity')
        if self.container_id is not None and value != self.container_id:
            raise RuntimeError('Owned container identity mismatch')
        self.container_id = value
        return value

    def cleanup(self):
        if not self.attempted:
            return {'status': 'NOT_STARTED'}
        self.capture_id()
        target = self.container_id or self.name
        found = self.inspect(target)
        if found is None:
            if self.uncertain and self.container_id is None:
                # A daemon request may still complete after a CLI timeout.
                # Do not certify absence or claim successful cleanup.
                raise RuntimeError('Container launch outcome remains uncertain')
            return {'status': 'ALREADY_REMOVED', 'container_id': self.container_id}
        errors = []
        warnings = []
        for phase, command in (
            ('stop', ['docker', 'stop', '--time', '5', found]),
            ('remove', ['docker', 'rm', '-f', found]),
        ):
            step = {'phase': phase}
            self.cleanup_steps.append(step)
            try:
                result = self.run_command(command, capture_output=True, text=True, timeout=15)
                step['exit_code'] = result.returncode
                classification = 'success'
                if result.returncode:
                    # Retain only a fixed classification, never daemon output.
                    stderr = result.stderr.casefold()
                    if 'no such container' in stderr or 'no such object' in stderr:
                        classification = 'already-absent'
                    elif 'removal of container' in stderr and 'is already in progress' in stderr:
                        classification = 'removal-in-progress'
                    else:
                        classification = 'unknown-command-error'
                        errors.append(classification)
                    if classification != 'unknown-command-error':
                        warnings.append({'phase': phase, 'classification': classification})
                step['classification'] = classification
            except BaseException as exc:
                step.update(classification='exception', exception=exception_diagnostic(exc))
                errors.append('command-exception')
        final = {'phase': 'final-exact-identity-inspection'}
        self.cleanup_steps.append(final)
        try:
            deadline = time.monotonic() + 15
            absent = False
            final['polls'] = 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                final['polls'] += 1
                absent = self.inspect(found, timeout=min(3, remaining)) is None
                if absent:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(0.25, remaining))
            final['classification'] = 'confirmed-absent' if absent else 'container-remains'
            if not absent:
                errors.append('container-remains')
        except BaseException as exc:
            final.update(classification='exception', exception=exception_diagnostic(exc))
            raise
        if errors:
            # Even confirmed absence cannot erase unknown command failures.
            raise RuntimeError('Owned container cleanup did not finish cleanly')
        return {'status': 'REMOVED', 'container_id': found, 'warnings': warnings}



def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--controller-root',type=Path,required=True)
    parser.add_argument('--supervisor',type=Path,required=True)
    args=parser.parse_args()
    if sys.flags.optimize:
        raise RuntimeError('Optimized Python disables qualification checks')
    config=json.loads(args.config.read_text())
    assert Path(config['fixture_root']).is_absolute()
    assert not Path(config['fixture_root']).exists()
    assert config['execution_authorized'] is True
    assert config['runtime_version']=='1.1.0a48' and config['source_sha']=='45e8c2c1f1e6e9b72c5e48e01d735243185e015b'
    root=args.controller_root.absolute()
    assert root.parent.is_dir() and shutil.disk_usage(root.parent).free>=10*1024**3
    assert not root.exists() and not root.is_symlink()
    root.mkdir(mode=0o700)
    candidate=Path(config['installed_base'])
    tests=candidate/'source/action_server/tests'
    source=tests/'action_server_tests/test_sealed_postgres.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==config['tls_fixture_sha256']
    assert hashlib.sha256(args.supervisor.read_bytes()).hexdigest()==config['supervisor_sha256']
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(tests))
    fixture_module=importlib.import_module('action_server_tests.test_sealed_postgres')
    assert Path(fixture_module.__file__).resolve()==source.resolve()
    original_run=subprocess.run
    owner=OwnedFixtureContainer(root,original_run)
    subprocess.run=owner.run
    class Factory:
        def mktemp(self,name):
            path=root/name;path.mkdir(mode=0o700);return path
    fixture=fixture_module.tls_postgres.__wrapped__(Factory())
    process=None
    receipt={'status':'RUNNING','scope':'owned existing verify-full TLS fixture and installed Data child','cleanup_errors':[]}
    def interrupt(signum,frame):raise KeyboardInterrupt()
    old={sig:signal.signal(sig,interrupt) for sig in (signal.SIGTERM,signal.SIGINT)}
    try:
        tls=next(fixture)
        password=root/'reader-password';password.write_text(tls.password);password.chmod(0o600)
        ca=root/'reader-ca';ca.write_bytes(tls.ca);ca.chmod(0o600)
        private=root/'private-tls.json'
        private.write_text(json.dumps({'port':tls.port,'password_path':str(password),'ca_path':str(ca)}));private.chmod(0o600)
        config['private_tls']=str(private)
        local=root/'candidate-private.json';local.write_text(json.dumps(config));local.chmod(0o600)
        command=[sys.executable,str(args.supervisor.absolute()),'--candidate-python',str(candidate/'consumer/bin/python'),
                 '--script',str(Path(__file__).with_name('qualify.py')),'--config',str(local),
                 '--config-env','ACTIONS_V2_CANDIDATE','--evidence-root',str(root/'supervisor'),
                 '--budget-root',str(root)]
        process=subprocess.Popen(command,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        process.wait(timeout=1900)
        receipt['child_exit_code']=process.returncode
        assert process.returncode==0,'Installed Data supervisor failed'
        receipt['status']='PASS'
    except BaseException as exc:
        receipt.update(status='FAILED',failure_type=type(exc).__name__,failure=exception_diagnostic(exc))
    finally:
        # Repeated interrupts must not interrupt independent cleanup phases.
        for sig in old:
            signal.signal(sig,signal.SIG_IGN)
        # Stop supervisor first, allowing it to reap its own Runtime descendants.
        try:
            if process and process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
                    receipt['cleanup_errors'].append({'phase':'supervisor-stop','type':'ForcedKill'})
        except BaseException as exc:receipt['cleanup_errors'].append({'phase':'supervisor-stop','type':type(exc).__name__,'exception':exception_diagnostic(exc)})
        try:fixture.close()
        except BaseException as exc:receipt['cleanup_errors'].append({'phase':'tls-fixture-stop','type':type(exc).__name__,'exception':exception_diagnostic(exc)})
        try:receipt['owned_container_cleanup']=owner.cleanup()
        except BaseException as exc:receipt['cleanup_errors'].append({'phase':'owned-container-cleanup','type':type(exc).__name__,'exception':exception_diagnostic(exc)})
        receipt['owned_container_cleanup_steps']=owner.cleanup_steps
        receipt['owned_container_identity']={'name':owner.name,'id':owner.container_id,'launch_attempted':owner.attempted,'launch_uncertain':owner.uncertain}
        subprocess.run=original_run
        if receipt['cleanup_errors']:receipt['status']='FAILED'
        try:
            (root/'controller-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        finally:
            for sig,handler in old.items():signal.signal(sig,handler)
    return 0 if receipt['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
