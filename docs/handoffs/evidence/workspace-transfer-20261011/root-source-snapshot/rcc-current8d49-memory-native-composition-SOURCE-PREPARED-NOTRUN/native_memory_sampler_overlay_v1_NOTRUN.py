"""Prepared memory composition around the unchanged ONE legacy disk sampler.

No source fixture/policy/binary mutation. Factory injection is for pure composition
controls; the separately ROOT-adopted entry must pass the pinned legacy factories.
"""
from cgroup_memory_reader_observer_v1_NOTRUN import CgroupMemoryObserver, CgroupReader


class CompositionError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise CompositionError(code)


class MemoryComposedSampler:
    """Expose unchanged disk marker/state; retain separate strict memory marker."""
    def __init__(self, disk_factory, reader, state, observation, current_identity,
                 signal_child, *, observer_factory=CgroupMemoryObserver):
        self.state = state
        self.memory = observer_factory(reader, argv_sha256=state.pytest_argv_sha256,
                                       cwd=state.pytest_cwd)
        self.memory_final = None
        self.disk_final = None
        self.current_identity = current_identity
        self.signal_child = signal_child
        self.observation = observation
        self.stop_coalescing = []
        self.disk = disk_factory(_ObservedState(self), observation, current_identity,
                                 self.disk_stop, cadence=0.2, lifetime=640)

    def disk_stop(self, identity):
        if self.memory.signal_record is not None:
            self.stop_coalescing.append('DISK_SECOND_SIGNAL_SUPPRESSED_PRIOR_MEMORY_ATTEMPT')
            raise CompositionError('OWNED_STOP_ALREADY_ATTEMPTED_NO_SECOND_SIGNAL')
        return self.signal_child(identity)

    def start(self):
        return self.disk.start()  # Exactly one original FiniteSampler thread.

    def finish(self):
        try:
            self.disk_final = self.disk.finish(join_timeout=2)
        except BaseException:
            self.memory_final = self.memory.marker(cancellation_requested=None, sampler_alive=None)
            raise
        if type(self.disk_final) is not dict:
            self.memory_final = self.memory.marker(cancellation_requested=None, sampler_alive=None)
            raise CompositionError('MEMORY_ORIGINAL_DISK_FINAL_SCHEMA')
        self.memory_final = self.memory.after_join(
            cancellation_requested=self.disk_final.get('sampler_cancelled'),
            sampler_alive=self.disk_final.get('sampler_alive'))
        return self.disk_final  # No change to original disk marker schema/bytes.


class _ObservedState:
    def __init__(self, composed):
        self.composed = composed

    def __getattr__(self, name):
        return getattr(self.composed.state, name)

    def observe(self, owned_bytes, workspace_free_bytes, captures, current_identity, signal_child):
        c = self.composed
        # Preserve old disk observation first and its exact ownership checks.
        c.state.observe(owned_bytes, workspace_free_bytes, captures, current_identity, signal_child)
        memory_captures = captures
        if c.state.signal_record is not None:
            c.stop_coalescing.append('MEMORY_SECOND_SIGNAL_SUPPRESSED_PRIOR_DISK_ATTEMPT')
            memory_captures = []
        c.memory.sample(memory_captures, c.state.supervisor_identity,
                        c.current_identity, c.signal_child)

    def observation_failure(self):
        self.composed.state.observation_failure()
        self.composed.memory.observation_failure()


def composed_execute(original_execute, *args, **kwargs):
    """Delegate exactly once, retain original primary+cleanup, demote on memory FAIL."""
    require(len(args) >= 3 and isinstance(args[2], MemoryComposedSampler), 'MEMORY_COMPOSED_SAMPLER_REQUIRED')
    sampler = args[2]
    result = original_execute(*args, **kwargs)
    require(type(result) is dict and type(result.get('outcome')) is dict,
            'MEMORY_ORIGINAL_TRANSPORT_RESULT')
    require(sampler.memory_final is not None, 'MEMORY_FINAL_UNAVAILABLE')
    require(sampler.disk_final is result.get('sampler_final'), 'MEMORY_DISK_FINAL_RETURN_IDENTITY')
    require('cgroup_memory_final' not in result and 'original_outcome_before_memory' not in result,
            'MEMORY_NO_RESULT_KEY_COLLISION')
    original_outcome = result['outcome']
    require(type(original_outcome.get('primary')) is dict and type(original_outcome.get('cleanup')) is dict,
            'MEMORY_ORIGINAL_OUTCOME_SCHEMA')
    result['original_outcome_before_memory'] = {
        'status': original_outcome['status'], 'primary': dict(original_outcome['primary']),
        'cleanup': dict(original_outcome['cleanup'])}
    result['cgroup_memory_final'] = sampler.memory_final
    result['owned_stop_coalescing'] = list(sampler.stop_coalescing)
    result['memory_scope'] = ('shared self-cgroup observations/interval pressure only; '
                              'no child kill attribution, kernelquota, reader/reap or universal peak proof')
    if sampler.memory_final.get('status') != 'PASS':
        # Existing command/disk primary failures retain their original category.
        # A new memory failure demotes only a previously passing primary.
        primary = dict(original_outcome['primary'])
        if primary['status'] == 'PASS':
            primary = {'code': 'ADMISSION_FAILED', 'status': 'FAIL'}
        result['outcome'] = {'status': 'FAIL', 'primary': primary,
                             'cleanup': dict(original_outcome['cleanup'])}
    return result


def install_composition(legacy, expected_identity, *, reader_factory=CgroupReader,
                        observer_factory=CgroupMemoryObserver):
    """One process-local factory seam; old module functions/bodies stay on disk."""
    original_factory = legacy.FiniteSampler
    original_execute = legacy.execute_one
    require(not getattr(legacy, '_prepared_memory_composition_installed', False), 'MEMORY_NO_DOUBLE_INSTALL')
    def factory(state, observation, current_identity, signal_child):
        return MemoryComposedSampler(original_factory, reader_factory(expected_identity),
                                     state, observation, current_identity, signal_child,
                                     observer_factory=observer_factory)
    def execute(*args, **kwargs):
        return composed_execute(original_execute, *args, **kwargs)
    legacy.FiniteSampler = factory
    legacy.execute_one = execute
    legacy._prepared_memory_composition_installed = True
    return {'original_FiniteSampler': original_factory, 'original_execute_one': original_execute}
