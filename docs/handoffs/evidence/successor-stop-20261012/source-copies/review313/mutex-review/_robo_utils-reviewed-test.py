import logging


def test_system_mutex(monkeypatch):
    import os
    import subprocess
    import sys
    import textwrap
    import threading
    import uuid
    import weakref

    import pytest
    from _pytest.outcomes import Failed

    from actions.server._robo_utils import system_mutex as mutex_module
    from actions.server._robo_utils.system_mutex import (
        SystemMutex,
        _mutex_name_to_info,
        timed_acquire_mutex,
    )

    mutex_name = f"test_system_mutex_{os.getpid()}_{uuid.uuid4().hex}"

    system_mutex = SystemMutex(mutex_name)
    assert system_mutex.get_mutex_aquired()

    class Check2Thread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.worked = False

        def run(self):
            mutex2 = SystemMutex(mutex_name)
            assert not mutex2.get_mutex_aquired()
            self.worked = True

    t = Check2Thread()
    t.start()
    t.join()
    assert t.worked

    assert not system_mutex.disposed
    system_mutex.release_mutex()
    assert system_mutex.disposed

    mutex3 = SystemMutex(mutex_name)
    assert not mutex3.disposed
    assert mutex3.get_mutex_aquired()
    mutex3 = weakref.ref(mutex3)  # Garbage-collected

    # Calling release more times should not be an error
    system_mutex.release_mutex()

    mutex4 = SystemMutex(mutex_name)
    assert mutex4.get_mutex_aquired()

    with pytest.raises(AssertionError):
        SystemMutex("mutex/")  # Invalid name

    failed_attempt = threading.Event()
    released = threading.Event()
    abort_release = threading.Event()
    release_errors = []

    def observe_acquisition(*args, **kwargs):
        candidate = SystemMutex(*args, **kwargs)
        if not candidate.get_mutex_aquired():
            # The owner is still holding the real OS mutex at this boundary.
            failed_attempt.set()
        return candidate

    def release_mutex():
        try:
            assert failed_attempt.wait(5), "No failed real acquisition observed"
            if not abort_release.is_set():
                mutex4.release_mutex()
                released.set()
        except BaseException as error:
            release_errors.append(error)

    t = threading.Thread(target=release_mutex, daemon=True)
    t.start()

    def raise_assertion_info_if_prev_acquired_not_detected(mutex_name):
        prev_system_mutex = _mutex_name_to_info.get(mutex_name)
        if prev_system_mutex is None:
            found = []
            for e in _mutex_name_to_info.items():
                found.append((f"{e[0]}: {e[1]}"))

            raise AssertionError(f"Did not find mutex name: {mutex_name} in {found}")

        raise AssertionError(
            f"Mutex info found:\n"
            f"  acquired: {system_mutex.get_mutex_aquired()}\n"
            f"  system_mutex.disposed: {system_mutex.disposed}\n"
            f"  system_mutex.thread_id: {system_mutex.thread_id}\n"
            f"  get_tid(): {threading.get_ident()}\n"
        )

    try:
        with monkeypatch.context() as patch:
            patch.setattr(mutex_module, "SystemMutex", observe_acquisition)
            handle = timed_acquire_mutex(
                mutex_name,
                timeout=5,
                check_reentrant=False,
                raise_error_on_timeout=True,
            )
        with handle:
            t.join(5)
            assert failed_attempt.is_set(), "Mutex must reject acquisition while held"
            assert released.is_set(), "Owner release must complete before entry"
            assert mutex4.disposed
            assert not release_errors
            assert not t.is_alive()

            # At this point the lock is acquired (and it was done in this thread).
            # So, check that we get the error saying that it's not possible to get
            # a reentrant lock.
            try:
                with pytest.raises(RuntimeError) as exc:
                    with timed_acquire_mutex(
                        mutex_name, timeout=1, raise_error_on_timeout=True
                    ):
                        pass
            except Failed:
                raise_assertion_info_if_prev_acquired_not_detected(mutex_name)
            else:
                assert "not a reentrant mutex" in str(exc)

            # Must also fail from another process.
            code = f"""
    from actions.server._robo_utils.system_mutex import timed_acquire_mutex
    mutex_name = {mutex_name!r}
    with timed_acquire_mutex(mutex_name, timeout=1, raise_error_on_timeout=True):
        pass
    """
            with pytest.raises(subprocess.CalledProcessError) as child_error:
                subprocess.run(
                    [sys.executable, "-c", textwrap.dedent(code)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=5,
                )
            assert b"Could not get mutex" in child_error.value.stderr

    finally:
        abort_release.set()
        failed_attempt.set()
        t.join(5)
        mutex4.release_mutex()
        assert not t.is_alive(), "Owned release thread did not stop"


def test_gen_mutex_name_from_path():
    from actions.server._robo_utils.system_mutex import generate_mutex_name

    mutex_name = "my/snth\\nsth"
    mutex_name = generate_mutex_name(mutex_name, prefix="my_")
    assert mutex_name == "my_f9c932bf450ef164"


def test_system_mutex_error_on_timeout():
    import os
    import threading
    import uuid

    from actions.server._robo_utils.system_mutex import SystemMutex

    mutex_name = f"test_system_mutex_error_on_timeout_{os.getpid()}_{uuid.uuid4().hex}"
    mutex = SystemMutex(mutex_name)
    assert mutex.get_mutex_aquired()
    mutex_creation_info = [""]

    def thread():
        mutex2 = SystemMutex(mutex_name)
        assert not mutex2.get_mutex_aquired()
        mutex_creation_info[0] = mutex2.mutex_creation_info

    t = threading.Thread(target=thread)
    t.start()
    t.join()
    info = mutex_creation_info[0]
    assert str(os.getpid()) in info
    assert "mutex = SystemMutex(mutex_name)" in info


def test_system_mutex_timed_acquire_no_error_on_timeout():
    import threading

    from actions.server._robo_utils import log_custom_handler, system_mutex
    from actions.server._robo_utils.system_mutex import SystemMutex, timed_acquire_mutex

    event_mutex_acquired = threading.Event()
    event_terminate_thread = threading.Event()

    def thread():
        mutex2 = SystemMutex("test_system_mutex_timed_acquire_no_error_on_timeout")
        assert mutex2.get_mutex_aquired()
        event_mutex_acquired.set()
        event_terminate_thread.wait()

    t = threading.Thread(target=thread)
    t.start()
    event_mutex_acquired.wait()

    mutex = SystemMutex("test_system_mutex_timed_acquire_no_error_on_timeout")
    assert not mutex.get_mutex_aquired()

    # Here we check that a message is logged instead of raising
    # an error on timeout.

    def on_log_emit(msg):
        if "acquired after 1 seconds" in f"{msg.msg % msg.args}":
            event_terminate_thread.set()

    with log_custom_handler.add_handler_callback(
        system_mutex.log, on_log_emit, level=logging.DEBUG
    ):
        with timed_acquire_mutex(
            "test_system_mutex_timed_acquire_no_error_on_timeout", timeout=1
        ):
            pass


def test_system_mutex_locked_on_subprocess():
    import os
    import subprocess
    import sys

    from devutils.fixtures import wait_for_condition

    from actions.server._robo_utils.process import kill_process_and_subprocesses
    from actions.server._robo_utils.system_mutex import SystemMutex

    mutex_name = f"test_system_mutex_locked_on_subprocess_robo_{os.getpid()}"
    code = f"""
import sys
import time
print('initialized')
from actions.server._robo_utils.system_mutex import SystemMutex
mutex = SystemMutex('{mutex_name}')
assert mutex.get_mutex_aquired()
print('acquired mutex')
sys.stdout.flush()
time.sleep(30)
"""
    p = subprocess.Popen(
        [sys.executable, "-c", code], stdout=subprocess.PIPE, stdin=subprocess.PIPE
    )
    wait_for_condition(lambda: p.stdout.readline().strip() == b"acquired mutex")
    mutex = SystemMutex(mutex_name)
    assert not mutex.get_mutex_aquired()

    # i.e.: check that we can acquire the mutex if the related process dies.
    kill_process_and_subprocesses(p.pid)

    def acquire_mutex():
        mutex = SystemMutex(mutex_name)
        return mutex.get_mutex_aquired()

    wait_for_condition(acquire_mutex, timeout=5)
