"""Source preparation only. Preserve original constructors and cleanup outcomes."""
import contextlib
import inspect
import time
import types


class _ModuleProxy:
    def __init__(self, original, replacements):
        self._original = original
        self._replacements = replacements

    def __getattr__(self, name):
        if name in self._replacements:
            return self._replacements[name]
        return getattr(self._original, name)


def _closure(target):
    if not isinstance(target, types.FunctionType):
        return {}
    return dict(zip(target.__code__.co_freevars,
                    (cell.cell_contents for cell in (target.__closure__ or ()))))


class RetainedOriginalReaders:
    """Private fixture observer, never a replacement output consumer or killer."""
    def __init__(self, pool_module, provider_module, identity):
        self.pool = pool_module
        self.provider = provider_module
        self.identity = identity
        self.rows = []
        self.providers = []
        self.reports = []
        self.errors = []
        self.pool_threading = pool_module.threading
        self.provider_threading = provider_module.threading
        self.provider_subprocess = provider_module.subprocess
        self.retire = pool_module.ProcessHandle._retire_locked
        self.terminate = provider_module.terminate_process_tree
        self.provider_read_code = {
            c for c in provider_module._readline_with_timeout.__code__.co_consts
            if isinstance(c, types.CodeType)
        }

    def _retain(self, owner, role, thread):
        if any(row['owner'] is owner and row['role'] == role for row in self.rows):
            self.errors.append('DUPLICATE_READER_ROLE')
        try:
            measured_identity = self.identity(getattr(owner, '_process', owner))
        except BaseException:
            measured_identity = None
            self.errors.append('READER_OWNER_IDENTITY_UNAVAILABLE')
        self.rows.append({'owner': owner, 'role': role, 'thread': thread,
                          'owner_identity_at_retention': measured_identity})

    def _pool_thread(self, *args, **kwargs):
        thread = self.pool_threading.Thread(*args, **kwargs)
        try:
            target = kwargs.get('target', args[1] if len(args) > 1 else None)
            arguments = kwargs.get('args', args[3] if len(args) > 3 else ())
            closure = _closure(target)
            owner = closure.get('self')
            if (isinstance(owner, self.pool.ProcessHandle)
                    and target.__name__ == '_process_stream_reader'
                    and target.__code__.co_filename == self.retire.__code__.co_filename):
                stream = arguments[0] if len(arguments) == 1 else None
                if stream is owner._process.stdout:
                    role = 'stdout'
                elif stream is owner._process.stderr:
                    role = 'stderr'
                else:
                    self.errors.append('UNKNOWN_POOL_STREAM')
                    return thread
                self._retain(owner, role, thread)
        except BaseException:
            self.errors.append('POOL_RETENTION_UNAVAILABLE')
        return thread

    def _provider_popen(self, *args, **kwargs):
        process = self.provider_subprocess.Popen(*args, **kwargs)
        try:
            measured_identity = self.identity(process)
            self.providers.append((process, measured_identity))
        except BaseException:
            self.providers.append((process, None))
            self.errors.append('PROVIDER_IDENTITY_UNAVAILABLE')
        return process

    def _provider_thread(self, *args, **kwargs):
        thread = self.provider_threading.Thread(*args, **kwargs)
        try:
            target = kwargs.get('target', args[1] if len(args) > 1 else None)
            if isinstance(target, types.FunctionType) and target.__code__ in self.provider_read_code:
                stream = _closure(target).get('stream')
                matches = [p for p, _ in self.providers if p.stdout is stream]
                if len(matches) != 1:
                    self.errors.append('PROVIDER_STREAM_OWNER_UNAVAILABLE')
                else:
                    self._retain(matches[0], 'provider-startup', thread)
        except BaseException:
            self.errors.append('PROVIDER_RETENTION_UNAVAILABLE')
        return thread

    def _observe_join(self, owner, roles, deadline, production_result):
        report = {'roles': list(roles), 'readers': [], 'errors': [],
                  'production_result_identity_preserved': True,
                  'production_return_type': type(production_result).__name__,
                  'join_scope': 'observer_join_within_original_deadline',
                  'deadline': deadline, 'status': 'HOLD'}
        identities = [r['owner_identity_at_retention'] for r in self.rows
                      if r['owner'] is owner and r['role'] != 'tcp']
        report['owner_identity'] = identities[0] if identities else None
        if not identities or any(x is None or x != identities[0] for x in identities):
            report['errors'].append('OWNER_IDENTITY_UNAVAILABLE')
        for role in roles:
            matches = [r for r in self.rows if r['owner'] is owner and r['role'] == role]
            if len(matches) != 1:
                report['errors'].append('READER_ROLE_UNAVAILABLE')
                continue
            thread = matches[0]['thread']
            fact = {'role': role, 'before_alive': None, 'after_alive': None,
                    'observer_join_called': False, 'errors': []}
            try:
                fact['before_alive'] = thread.is_alive()
                remaining = max(0.0, deadline - time.monotonic())
                fact['remaining_at_join'] = remaining
                thread.join(timeout=remaining)
                fact['observer_join_called'] = True
                fact['after_alive'] = thread.is_alive()
                if fact['after_alive']:
                    report['errors'].append('READER_REMAINS_ALIVE')
            except BaseException:
                fact['errors'].append('READER_OBSERVATION_UNAVAILABLE')
                report['errors'].append('READER_OBSERVATION_UNAVAILABLE')
            report['readers'].append(fact)
        if self.errors:
            report['errors'].append('RETENTION_ERRORS_PRESENT')
        if not report['errors'] and len(report['readers']) == len(roles):
            report['status'] = 'PASS_OBSERVER_READER_SCOPE_ONLY'
        self.reports.append(report)

    @contextlib.contextmanager
    def installed(self):
        observer = self
        pool_proxy = _ModuleProxy(self.pool_threading, {'Thread': self._pool_thread})
        provider_proxy = _ModuleProxy(self.provider_threading, {'Thread': self._provider_thread})
        subprocess_proxy = _ModuleProxy(self.provider_subprocess, {'Popen': self._provider_popen})

        def retire(handle, deadline):
            result = None
            try:
                result = observer.retire(handle, deadline)
                return result
            finally:
                tcp = getattr(handle, '_reader', None)
                if tcp is not None and not any(r['owner'] is handle and r['role'] == 'tcp' for r in observer.rows):
                    observer._retain(handle, 'tcp', tcp)
                try:
                    observer._observe_join(handle, ('stdout', 'stderr', 'tcp'), deadline, result)
                except BaseException:
                    observer.errors.append('RETIREMENT_OBSERVER_UNAVAILABLE')

        def terminate(process, **kwargs):
            bound = inspect.signature(observer.terminate).bind(process, **kwargs)
            bound.apply_defaults()
            deadline = time.monotonic() + bound.arguments['grace_seconds']
            result = None
            try:
                result = observer.terminate(process, **kwargs)
                return result
            finally:
                try:
                    observer._observe_join(process, ('provider-startup',), deadline, result)
                except BaseException:
                    observer.errors.append('PROVIDER_OBSERVER_UNAVAILABLE')

        assignments = ((self.pool, 'threading', pool_proxy, self.pool_threading),
                       (self.provider, 'threading', provider_proxy, self.provider_threading),
                       (self.provider, 'subprocess', subprocess_proxy, self.provider_subprocess),
                       (self.pool.ProcessHandle, '_retire_locked', retire, self.retire),
                       (self.provider, 'terminate_process_tree', terminate, self.terminate))
        try:
            for owner, name, replacement, original in assignments:
                if getattr(owner, name) is not original:
                    raise RuntimeError('OBSERVER_INSTALL_IDENTITY_MISMATCH')
                setattr(owner, name, replacement)
            yield self
        finally:
            for owner, name, replacement, original in reversed(assignments):
                if getattr(owner, name) is replacement:
                    setattr(owner, name, original)
                else:
                    self.errors.append('OBSERVER_RESTORE_IDENTITY_MISMATCH')
