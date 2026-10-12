"""Outer ownership observer and capacity state; no transport implementation.

Callers supply the existing pinned helper and actual observations. This module
never waits/reaps a wrapper and never signals the supervisor. Final record
admission still requires original measured case/lease/cleanup bytes.
"""
import threading
from runner_contracts_v3 import (
    AdmissionFailure, HARD_ADMISSION_BYTES, OPERATIONAL_STOP_BYTES,
    WORKSPACE_FREE_BYTES, authorize_signal, exact_int, need, select_owned_pytest,
)


class SupervisorPopenObserver:
    def __init__(self, original_subprocess, supervisor_argv):
        self.original = original_subprocess
        self.supervisor_argv = list(supervisor_argv)
        self.wrapper = None
        self.ready = threading.Event()

    def __getattr__(self, name):
        return getattr(self.original, name)

    def Popen(self, command, *args, **kwargs):
        need(list(command) == self.supervisor_argv, 'UNREVIEWED_SUPERVISOR_ARGV')
        need(self.wrapper is None, 'DUPLICATE_SUPERVISOR_WRAPPER')
        # Pass the original objects unchanged and return the real Popen object.
        wrapper = self.original.Popen(command, *args, **kwargs)
        self.wrapper = wrapper
        self.ready.set()
        return wrapper


class CapacityState:
    def __init__(self, *, owned_root, supervisor_identity, pytest_argv_sha256, pytest_cwd):
        self.owned_root = owned_root
        self.supervisor_identity = supervisor_identity
        self.pytest_argv_sha256 = pytest_argv_sha256
        self.pytest_cwd = pytest_cwd
        self.samples = 0
        self.maximum = 0
        self.minimum_workspace = None
        self.primary = None
        self.signal_record = None
        self.inspection_error = False

    def observe(self, owned_bytes, workspace_free_bytes, captures, current_identity, signal_child):
        need(exact_int(owned_bytes) and owned_bytes >= 0, 'OWNED_BYTES_OBSERVATION')
        need(exact_int(workspace_free_bytes) and workspace_free_bytes >= 0, 'WORKSPACE_BYTES_OBSERVATION')
        self.samples += 1
        self.maximum = max(self.maximum, owned_bytes)
        self.minimum_workspace = workspace_free_bytes if self.minimum_workspace is None else min(self.minimum_workspace, workspace_free_bytes)
        tripped = owned_bytes >= OPERATIONAL_STOP_BYTES or workspace_free_bytes < WORKSPACE_FREE_BYTES
        if not tripped or self.primary is not None:
            return
        self.primary = {'status': 'FAIL', 'code': 'CAPACITY_THRESHOLD'}
        try:
            owner = select_owned_pytest(captures, self.supervisor_identity, self.pytest_argv_sha256, self.pytest_cwd)
            live_identity = current_identity(owner[0])
            authorize_signal(owner, live_identity)
            need(owner != self.supervisor_identity, 'NO_SUPERVISOR_SIGNAL')
            signal_child(owner)
            self.signal_record = {'pid': owner[0], 'create_time': owner[1], 'action': 'SIGNAL_PYTEST_CHILD_ONLY_NO_WAIT'}
        except Exception as error:
            self.inspection_error = True
            self.signal_record = {'action': 'UNAVAILABLE_NO_UNOWNED_SIGNAL', 'error_class': type(error).__name__}
            # Threshold remains primary; signal/inspection error is secondary.

    def observation_failure(self):
        self.inspection_error = True
        if self.primary is None:
            self.primary = {'status': 'FAIL', 'code': 'CAPTURE_INSPECTION_FAILED'}

    def final_marker(self, *, cancellation_requested, sampler_alive):
        need(type(cancellation_requested) is bool and type(sampler_alive) is bool, 'FINAL_SAMPLER_STATE_TYPE')
        return {
            'stage': 'final', 'sample_count': self.samples,
            'maximum_observed_bytes': self.maximum,
            'workspace_minimum_observed_bytes': self.minimum_workspace if self.minimum_workspace is not None else 0,
            'threshold_triggered': self.primary is not None and self.primary['code'] == 'CAPACITY_THRESHOLD',
            'inspection_error': self.inspection_error,
            'sampler_cancelled': cancellation_requested, 'sampler_alive': sampler_alive,
            'peak_is_universal': False, 'kernel_quota': False,
        }

    def scope(self):
        return {
            'sampling_seconds': 0.2, 'operational_stop_bytes': OPERATIONAL_STOP_BYTES,
            'hard_admission_bytes': HARD_ADMISSION_BYTES,
            'maximum_is_sampled_only': True, 'intervening_overshoot_unknown': True,
            'kernel_quota': False, 'exclusive_wrapper_owner': 'existing_pinned_helper',
            'signal_record': self.signal_record, 'primary': self.primary,
        }
