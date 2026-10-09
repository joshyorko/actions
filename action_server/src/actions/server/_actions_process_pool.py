import itertools
import json
import logging
import socket as socket_module
import subprocess
import sys
import threading
from collections import namedtuple
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Set
from typing import Literal

from termcolor import colored

from actions import ActionContext
from actions.server._models import Action, ActionPackage, Run
from actions.server._protocols import JSONValue

from ._settings import Settings, is_frozen

if TYPE_CHECKING:
    from actions.server._runs_state_cache import RunRuntimeInfo

log = logging.getLogger(__name__)

AF_INET, SOCK_STREAM, SHUT_WR, SOL_SOCKET, SO_REUSEADDR, IPPROTO_TCP, socket = (
    socket_module.AF_INET,
    socket_module.SOCK_STREAM,
    socket_module.SHUT_WR,
    socket_module.SOL_SOCKET,
    socket_module.SO_REUSEADDR,
    socket_module.IPPROTO_TCP,
    socket_module.socket,
)

if sys.platform == "win32":
    SO_EXCLUSIVEADDRUSE = socket_module.SO_EXCLUSIVEADDRUSE  # noqa

_Key = namedtuple("_Key", "action_package_id, env, cwd")


@dataclass(frozen=True)
class WorkerRetirementResult:
    state: Literal["execution_stopped", "crash_unverified", "pending"]
    descendant_snapshot_complete: bool
    reason: str = ""
    cleanup: object | None = None

    @property
    def capacity_releasable(self) -> bool:
        return self.state != "pending"

    def __bool__(self) -> bool:
        return self.capacity_releasable


def _create_server_socket(host: str, port: int):
    try:
        server = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        if sys.platform == "win32":
            server.setsockopt(SOL_SOCKET, SO_EXCLUSIVEADDRUSE, 1)
        else:
            server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        server.bind((host, port))
        server.settimeout(None)
    except Exception:
        server.close()
        raise

    return server


def _connect_to_socket(host, port):
    """connects to a host/port"""

    s = socket(AF_INET, SOCK_STREAM)

    #  Set TCP keepalive on an open socket.
    #  It activates after 1 second (TCP_KEEPIDLE,) of idleness,
    #  then sends a keepalive ping once every 3 seconds (TCP_KEEPINTVL),
    #  and closes the connection after 5 failed ping (TCP_KEEPCNT), or 15 seconds
    try:
        s.setsockopt(SOL_SOCKET, socket_module.SO_KEEPALIVE, 1)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.
    try:
        s.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_KEEPIDLE, 1)  # noqa
    except (AttributeError, OSError):
        pass  # May not be available everywhere.
    try:
        s.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_KEEPINTVL, 3)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.
    try:
        s.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_KEEPCNT, 5)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.

    timeout = 20
    s.settimeout(timeout)
    s.connect((host, port))
    s.settimeout(None)  # no timeout after connected
    return s


class ProcessHandle:
    def __init__(
        self,
        settings: Settings,
        action_package: ActionPackage,
        post_run_args: Optional[tuple[str, ...]],
    ):
        from actions.server._preload_actions.preload_actions_streams import (
            JsonRpcStreamWriter,
        )
        from actions.server._robo_utils.callback import Callback
        from actions.server._robo_utils.run_in_thread import run_in_thread

        from ._actions_run_helpers import (
            _add_preload_actions_dir_to_env_pythonpath,
            get_action_package_cwd,
        )
        from ._preload_actions.preload_actions_streams import JsonRpcStreamReaderThread
        from ._rcc_runtime_adapter import (
            RccProcessHandle,
            build_exec_command,
            get_rcc_location,
            load_descriptor,
            new_receipt_path,
        )
        from ._robo_utils.process import build_python_launch_env

        self._post_run_args = post_run_args
        self._retirement_lock = threading.Lock()
        self._retirement_started = False
        self._crash_unverified = False
        self._exit_attempted = False
        self._retirement_complete = False
        self._retirement_result: WorkerRetirementResult | None = None
        self._retirement_descendants: list[object] | None = None
        self._retirement_snapshot_failed = False

        # If kill was internally called, we'll just check it instead of waiting for
        # the process to exit when is_alive() is called.
        self._kill_called = False

        self.key = _get_process_handle_key(settings, action_package)

        # The can_reuse flag is used to notify whether this process can be reused
        # (upon reloading all running processes are marked as non-reusable).
        self.can_reuse = True

        persisted_env = json.loads(action_package.env_json)
        runtime_descriptor = load_descriptor(action_package.env_json)
        env = {key: value for key, value in persisted_env.items() if key != "runtime"}
        _add_preload_actions_dir_to_env_pythonpath(env)
        env = build_python_launch_env(env)
        # Shouldn't be there, but just making sure... if it is it can
        # affect how the logs are generated and if wrong the logs would
        # also be wrong.
        env.pop("ROBOT_ROOT", None)

        # Pass datadir to actions so work-items use the shared database
        env["ACTIONS_RUNTIME_DATADIR"] = str(settings.datadir)
        # Also set RC_WORKITEM_DB_PATH directly for actions-work-items compatibility
        env["RC_WORKITEM_DB_PATH"] = str(settings.datadir / "workitems.db")

        if settings.reuse_processes:
            # When reusing processes we don't want to dump threads if
            # the process doesn't exit!
            env["RC_DUMP_THREADS_AFTER_RUN"] = "0"

        if runtime_descriptor is not None:
            python_exe = "python"
        elif "PYTHON_EXE" in env:
            python_exe = env["PYTHON_EXE"]
        else:
            if is_frozen():
                log.critical(
                    f"Unable to create process for action package: {action_package} "
                    "(environment does not contain PYTHON_EXE)."
                )
                return

            python_exe = sys.executable

        # stdin/stdout is no longer an option because numpy gets halted
        # if stdin is being read while importing numpy.
        # https://github.com/numpy/numpy/issues/24290
        # https://github.com/robocorp/robocorp/issues/271
        use_tcp = True

        cwd = get_action_package_cwd(settings, action_package)
        from ._robo_utils.process import build_subprocess_kwargs

        subprocess_kwargs = build_subprocess_kwargs(cwd=cwd, env=env)
        subprocess_kwargs.update(
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._cwd: str = str(cwd)

        def _process_stream_reader(stderr_or_stdout):
            while True:
                line_bytes = stderr_or_stdout.readline()
                if not line_bytes:
                    break
                line_as_str = line_bytes.decode("utf-8", "replace")
                print(
                    colored(f"output (pid: {pid}): ", attrs=["dark"])
                    + f"{line_as_str.strip()}\n",
                    end="",
                )
                self._on_output(line_bytes)

        self._read_queue: "Queue[dict]" = Queue()

        if use_tcp:
            server_socket = _create_server_socket("127.0.0.1", 0)
            connection_future = None
            startup_cancelled = threading.Event()

            def cleanup_startup():
                startup_cancelled.set()
                try:
                    try:
                        server_socket.shutdown(socket_module.SHUT_RDWR)
                    except (AttributeError, OSError):
                        pass
                finally:
                    try:
                        server_socket.close()
                    except (AttributeError, OSError):
                        pass

                if connection_future is not None:
                    try:
                        connection_future.cancel()
                    except BaseException:
                        log.debug(
                            "Unable to cancel the TCP accept future.", exc_info=True
                        )
                    try:
                        connection_future.result(timeout=1)
                    except BaseException:
                        log.debug(
                            "TCP accept future finished during startup cleanup.",
                            exc_info=True,
                        )

            def cleanup_process():
                try:
                    if getattr(self, "_rcc_wrapper", None) is not None:
                        self._rcc_wrapper.kill()
                    elif getattr(self, "_process", None) is not None:
                        from ._robo_utils.process import kill_process_and_subprocesses

                        kill_process_and_subprocesses(self._process.pid)
                except BaseException:
                    log.exception("Unable to clean up the failed TCP worker startup.")

            try:
                host, port = server_socket.getsockname()
                worker_command = [
                    "python" if runtime_descriptor is not None else python_exe,
                    "-m",
                    "preload_actions_server_main",
                    "--tcp",
                    f"--host={host}",
                    f"--port={port}",
                ]
                receipt_file = new_receipt_path(settings.datadir)
                if runtime_descriptor is not None:
                    cmdline = build_exec_command(
                        get_rcc_location(),
                        runtime_descriptor,
                        worker_command,
                        receipt_file=receipt_file,
                    )
                else:
                    cmdline = worker_command

                def accept_connection():
                    server_socket.listen(1)
                    server_socket.settimeout(0.2)
                    while not startup_cancelled.is_set():
                        try:
                            sock, _addr = server_socket.accept()
                        except socket_module.timeout:
                            continue
                        return sock
                    raise RuntimeError("TCP worker startup was cancelled")

                connection_future = run_in_thread(accept_connection)

                self._process = subprocess.Popen(cmdline, **subprocess_kwargs)
                self._rcc_wrapper = (
                    RccProcessHandle(self._process, receipt_file)
                    if runtime_descriptor is not None
                    else None
                )
                self._on_output = Callback()

                pid = self._process.pid

                stderr = self._process.stderr
                stdout = self._process.stdout

                t = threading.Thread(
                    target=_process_stream_reader, args=(stderr,), daemon=True
                )
                t.name = f"Stderr reader (pid: {pid})"
                t.start()

                t = threading.Thread(
                    target=_process_stream_reader, args=(stdout,), daemon=True
                )
                t.name = f"Stdout reader (pid: {pid})"
                t.start()
            except BaseException:
                cleanup_startup()
                cleanup_process()
                raise

            try:
                s = connection_future.result(10)
            except Exception:
                log.exception(
                    "Process that runs action did not connect back in the available timeout."
                )
                cleanup_startup()
                cleanup_process()
                raise
            finally:
                startup_cancelled.set()
                try:
                    server_socket.close()
                except (AttributeError, OSError):
                    pass
            read_from = s.makefile("rb")
            write_to = s.makefile("wb")
            self._socket = s

            self._writer = JsonRpcStreamWriter(write_to, sort_keys=True)
            self._reader = JsonRpcStreamReaderThread(
                read_from, self._read_queue, lambda *args, **kwargs: None
            )
        else:
            # Will start things using the stdin/stdout for communicating.
            worker_command = [
                "python" if runtime_descriptor is not None else python_exe,
                "-m",
                "preload_actions_server_main",
            ]
            receipt_file = new_receipt_path(settings.datadir)
            if runtime_descriptor is not None:
                cmdline = build_exec_command(
                    get_rcc_location(),
                    runtime_descriptor,
                    worker_command,
                    receipt_file=receipt_file,
                )
            else:
                cmdline = worker_command
            subprocess_kwargs["stdin"] = subprocess.PIPE

            self._process = subprocess.Popen(cmdline, **subprocess_kwargs)
            self._rcc_wrapper = (
                RccProcessHandle(self._process, receipt_file)
                if runtime_descriptor is not None
                else None
            )
            self._on_output = Callback()

            pid = self._process.pid

            stderr = self._process.stderr
            t = threading.Thread(target=_process_stream_reader, args=(stderr,))
            t.name = f"Stderr reader (pid: {pid})"
            t.start()

            write_to = self._process.stdin
            read_from = self._process.stdout
            self._writer = JsonRpcStreamWriter(write_to, sort_keys=True)
            self._reader = JsonRpcStreamReaderThread(
                read_from, self._read_queue, lambda *args, **kwargs: None
            )
        self._reader.start()

    @property
    def pid(self):
        return self._process.pid

    @property
    def cwd(self) -> str:
        return self._cwd

    def is_alive(self) -> bool:
        if self._kill_called:
            return False

        from ._robo_utils.process import is_process_alive

        if self._process.poll() is not None:
            return False

        return is_process_alive(self._process.pid)

    def kill(self) -> None:
        from ._robo_utils.process import kill_process_and_subprocesses

        if not self.is_alive():
            log.info(
                f"Process related to run {self._process.pid} is not running, cannot kill."
            )
            return

        self._kill_called = True

        try:
            from ._common.process import snapshot_process_descendants

            self._retirement_descendants = snapshot_process_descendants(
                self._process.pid
            )
        except Exception:
            self._retirement_descendants = []
            self._retirement_snapshot_failed = True
            log.warning(
                "Unable to snapshot descendants before active worker cancellation.",
                exc_info=True,
            )

        log.info("Subprocess kill [pid=%s]", self._process.pid)
        wrapper = getattr(self, "_rcc_wrapper", None)
        if wrapper is not None:
            wrapper.kill()
        else:
            kill_process_and_subprocesses(self._process.pid)

    def retire(self, deadline: Optional[float] = None) -> WorkerRetirementResult:
        """Retire a completed worker by one bounded exit/force/reap deadline."""
        import time

        deadline = deadline if deadline is not None else time.monotonic() + 10.0
        remaining = max(0.0, deadline - time.monotonic())
        if not self._retirement_lock.acquire(timeout=remaining):
            log.warning("Timed out waiting for another worker retirement attempt.")
            return WorkerRetirementResult(
                "pending", descendant_snapshot_complete=False,
                reason="retirement lock deadline expired",
            )
        try:
            return self._retire_locked(deadline)
        finally:
            self._retirement_lock.release()

    def _retire_locked(self, deadline: float) -> WorkerRetirementResult:
        import time

        from ._common.process import (
            force_kill_process_tree_until,
            snapshot_process_descendants,
        )

        force_reserve = 2.0
        if self._retirement_complete:
            assert self._retirement_result is not None
            return self._retirement_result

        if getattr(self, "_crash_unverified", False):
            return self._record_unverified_crash(deadline)

        if not getattr(self, "_retirement_started", False):
            self._retirement_started = True
            had_snapshot = self._retirement_descendants is not None
            if (
                not had_snapshot
                and self._process.poll() is not None
                and not self._kill_called
            ):
                self._crash_unverified = True
                return self._record_unverified_crash(deadline)

        wrapper = getattr(self, "_rcc_wrapper", None)
        if self._retirement_descendants is None:
            if self._process.poll() is not None:
                self._retirement_descendants = []
                self._retirement_snapshot_failed = True
                log.error(
                    "Cannot prove worker descendants after wrapper exited before retirement snapshot (pid=%s).",
                    self._process.pid,
                )
            else:
                try:
                    self._retirement_descendants = snapshot_process_descendants(
                        self._process.pid
                    )
                except Exception:
                    log.exception("Unable to snapshot worker descendants before exit.")
                    self._retirement_descendants = []
                    self._retirement_snapshot_failed = True
        snapshot_failed = self._retirement_snapshot_failed

        if wrapper is not None and wrapper._owned_processes is None:
            # The snapshot must precede the exit frame: a cleanly exiting
            # RCC wrapper can reparent descendants before force cleanup.
            wrapper._owned_processes = self._retirement_descendants
            wrapper._owned_snapshot_complete = not snapshot_failed

        exit_deadline = max(time.monotonic(), deadline - force_reserve)
        if not self._kill_called and not self._exit_attempted and not snapshot_failed:
            self._exit_attempted = True
            try:
                self._writer.write_with_deadline(
                    {"method": "exit"}, self._socket, exit_deadline
                )
            except Exception:
                log.warning("Worker exit frame failed; switching to bounded force cleanup.", exc_info=True)
        elif snapshot_failed or self._kill_called:
            self._exit_attempted = True

        if (
            not self._kill_called
            and not snapshot_failed
            and self._process.poll() is None
        ):
            try:
                self._process.wait(
                    timeout=max(0.0, exit_deadline - time.monotonic())
                )
            except subprocess.TimeoutExpired:
                pass

        if wrapper is not None:
            cleanup = wrapper.force_kill_until(deadline)
            complete = cleanup.execution_stopped
        else:
            cleanup = force_kill_process_tree_until(
                self._process,
                self._retirement_descendants,
                deadline,
                snapshot_complete_before_call=not snapshot_failed,
            )
            complete = cleanup.execution_stopped

        self._retirement_snapshot_failed = not cleanup.descendant_snapshot_complete
        if snapshot_failed:
            complete = False
        self._shutdown_retirement_socket()
        remaining = max(0.0, deadline - time.monotonic())
        self._reader.join(timeout=remaining)
        if self._reader.is_alive():
            complete = False
            log.warning("Worker reader thread remains alive after retirement deadline.")
        if complete:
            self._retirement_complete = True
            result = WorkerRetirementResult(
                "execution_stopped",
                descendant_snapshot_complete=cleanup.descendant_snapshot_complete,
                cleanup=cleanup,
            )
        else:
            log.warning("Worker retirement remains pending: %s", cleanup)
            result = WorkerRetirementResult(
                "pending",
                descendant_snapshot_complete=cleanup.descendant_snapshot_complete,
                reason="wrapper or descendant cleanup remains unconfirmed",
                cleanup=cleanup,
            )
        self._retirement_result = result
        return result

    def _record_unverified_crash(self, deadline: float) -> WorkerRetirementResult:
        import time

        try:
            self._process.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            return WorkerRetirementResult(
                "pending", False, "crashed wrapper wait timed out"
            )
        self._shutdown_retirement_socket()
        self._reader.join(timeout=max(0.0, deadline - time.monotonic()))
        if self._reader.is_alive():
            return WorkerRetirementResult(
                "pending", False, "crashed worker reader remains alive"
            )
        result = WorkerRetirementResult(
            "crash_unverified",
            descendant_snapshot_complete=False,
            reason="wrapper exited before descendant snapshot; coverage not proven",
        )
        log.error("Worker crashed before retirement snapshot: %s", result.reason)
        self._retirement_complete = True
        self._retirement_result = result
        return result

    def _shutdown_retirement_socket(self) -> None:
        sock = getattr(self, "_socket", None)
        if sock is None:
            return
        try:
            sock.shutdown(socket_module.SHUT_RDWR)
        except OSError:
            pass

    def _do_run_action(
        self,
        run: Run,
        action_package: ActionPackage,
        action: Action,
        input_json: Path,
        run_artifacts_dir: Path,
        result_json: Path,
        headers: dict,
        cookies: dict,
        reuse_process: bool,
    ) -> int:
        from actions.server._api_oauth2 import (
            get_resolved_provider_settings,
            refresh_tokens,
        )
        from actions.server._api_secrets import IN_MEMORY_SECRETS
        from actions.server._encryption import (
            decrypt_simple,
            get_encryption_keys,
            make_encrypted_data_envelope,
            make_unencrypted_data_envelope,
        )
        from actions.server._models import OAuth2UserData, get_db
        from actions.server._user_session import (
            COOKIE_SESSION_ID,
            get_user_session_from_id,
        )

        headers = IN_MEMORY_SECRETS.update_headers(action_package, action, headers)

        x_action_context_key = "x-action-context"
        x_action_context = headers.get(x_action_context_key)

        initial_action_context_value: Optional[JSONValue] = None
        if x_action_context:
            action_context = ActionContext(x_action_context)
            initial_action_context_value = action_context.value

        session_id = cookies.get(COOKIE_SESSION_ID)
        if session_id:
            db = get_db()
            with db.connect():
                user_session = get_user_session_from_id(session_id, db)
                if user_session:
                    # Verify whether we need to add OAuth2 secrets from the current
                    # user session.
                    where, values = db.where_from_dict({"user_session_id": session_id})

                    required_providers = set()

                    param_name_to_provider: dict[str, str] = {}
                    managed_params_schema = action.managed_params_schema
                    if managed_params_schema:
                        loaded = json.loads(managed_params_schema)
                        for param_name, param_info in loaded.items():
                            if param_info.get("type") == "OAuth2Secret":
                                provider = param_info.get("provider")
                                if provider:
                                    param_name_to_provider[param_name] = provider
                                    required_providers.add(provider)

                    # Note: if it's not there it's not a blocker (it may've
                    # been passed in the x-action-context header or in the
                    # input json).
                    provider_to_access_data: dict[str, OAuth2UserData] = {}
                    for user_data in db.all(OAuth2UserData, where=where, values=values):
                        if user_data.provider in required_providers:
                            provider_to_access_data[user_data.provider] = user_data

                    # Now that we have the information needed, refresh it.
                    if provider_to_access_data:
                        new_oauth2_data = refresh_tokens(
                            session_id, provider_to_access_data.values()
                        )
                        provider_to_access_data = dict(
                            (d.provider, d) for d in new_oauth2_data
                        )

                        data = {}

                        if initial_action_context_value and isinstance(
                            initial_action_context_value, dict
                        ):
                            data.update(initial_action_context_value)

                        for param_name, provider in param_name_to_provider.items():
                            access_data = provider_to_access_data.get(provider)
                            if access_data and access_data.access_token:
                                try:
                                    access_token = decrypt_simple(
                                        access_data.access_token
                                    )
                                except Exception:
                                    log.critical(
                                        "It was not possible to decrypt the access token, secrets won't be sent"
                                        "(the storage key has probably changed, so, a new login will be needed)."
                                    )
                                else:
                                    settings = get_resolved_provider_settings(provider)
                                    # i.e.: if it's not there, don't add it, let the
                                    # action itself fail and provide the needed info.
                                    metadata: dict[str, JSONValue] = {}
                                    if settings.server:
                                        # Always pass the server if it's available.
                                        metadata["server"] = settings.server
                                    ctx = data.setdefault("secrets", {})

                                    if not isinstance(ctx, dict):
                                        log.critical(
                                            "The value for 'secrets' is not a dictionary, overwriting!"
                                        )
                                        ctx = data["secrets"] = {}

                                    ctx[param_name] = {
                                        "provider": provider,
                                        "access_token": access_token,
                                        "metadata": metadata,
                                    }

                        # No context passed: create one now
                        keys = get_encryption_keys()
                        if keys:
                            # Data must be filled as:
                            # "my_oauth2_secret": {
                            #   "provider": "google",
                            #   "scopes": ["scope1", "scope2"],
                            #   "access_token": "<this-is-the-access-token>",
                            #   "metadata": { "any": "additional info" }
                            # }
                            header_value = make_encrypted_data_envelope(keys[0], data)
                        else:
                            header_value = make_unencrypted_data_envelope(data)

                        headers[x_action_context_key] = header_value

        msg = {
            "command": "run_action",
            "action_name": action.name,
            "action_file": f"{action.file}",
            "input_json": f"{input_json}",
            "robot_artifacts": f"{run_artifacts_dir}",
            "result_json": f"{result_json}",
            "headers": headers,
            "cookies": cookies,
            "reuse_process": reuse_process,
            "cwd": self._cwd,
        }
        self._writer.write(msg)

        queue = self._read_queue

        result_msg = queue.get(block=True)
        if result_msg is None:
            # This means that the process was actually killed (or crashed).
            result_msg = {"returncode": 77}

        if self._post_run_args:
            log.debug("Calling post run command.")
            try:
                self._call_post_run_script(
                    self._post_run_args,
                    initial_action_context_value,
                    msg,
                    run,
                )
            except Exception:
                log.exception("Error runnnig post run command.")
        else:
            log.debug("Not running post run command.")
        return result_msg["returncode"]

    def _call_post_run_script(
        self,
        post_run_args: tuple[str, ...],
        initial_action_context_value: Optional[JSONValue],
        msg: dict,
        run: Run,
    ) -> None:
        import shlex
        from string import Template

        from actions.server._artifact_storage import get_artifact_storage
        from actions.server._robo_utils import process, run_in_thread
        from actions.server._robo_utils.process import build_python_launch_env

        mapping = {
            "base_artifacts_dir": get_artifact_storage().root,
            "run_id": run.id,
            "run_artifacts_dir": msg["robot_artifacts"],
            "action_name": msg["action_name"],
        }
        if isinstance(initial_action_context_value, dict):
            invocation_context = initial_action_context_value.get("invocation_context")
            if isinstance(invocation_context, dict):
                for key, value in invocation_context.items():
                    if isinstance(value, str):
                        mapping[key] = value

        use_args = []
        for arg in post_run_args:
            try:
                use_args.append(Template(arg).substitute(mapping))
            except Exception:
                error_msg = f"Error substituting {arg!r} in post run command."
                log.exception(error_msg)
                raise RuntimeError(error_msg)  # We can't proceed!

        # Run but don't wait for it!
        try:
            cwd = None
            mapping_as_env_vars = {
                f"ACTIONS_RUNTIME_POST_RUN_{k.upper()}": f"{v}"
                for k, v in mapping.items()
            }
            env = build_python_launch_env(mapping_as_env_vars)

            def run_post_run_command_in_thread():
                import io

                try:
                    # Note: should log when starting automatically.
                    p = process.Process(use_args, cwd=cwd, env=env)
                    output = io.StringIO()
                    p.on_stderr.register(lambda line: output.write(line))
                    p.on_stdout.register(lambda line: output.write(line))
                    p.start()
                    p.join()
                    if p.returncode != 0:
                        log.error(
                            "Post run command failed. Return code is: %s (full command: %s)\nOutput:\n%s",
                            p.returncode,
                            shlex.join(use_args),
                            output.getvalue(),
                        )
                    else:
                        log.debug("Post run command finished successfuly.")
                except Exception:
                    log.exception("Error in post run command.")

            run_in_thread.run_in_thread(run_post_run_command_in_thread)

        except Exception:
            log.exception(f"Error running: {use_args!r}")

    def run_action(
        self,
        run: Run,
        action_package: ActionPackage,
        action: Action,
        input_json: Path,
        run_artifacts_dir: Path,
        output_file: Path,
        result_json: Path,
        headers: dict,
        cookies: dict,
        reuse_process: bool,
    ) -> int:
        """
        Runs the action and returns the returncode from running the action.

        (returncode=0 means everything is Ok).
        """
        with output_file.open("wb") as stream:

            def on_output(line_bytes: bytes):
                stream.write(line_bytes)

            with self._on_output.register(on_output):
                # stdout is now used for communicating, so, don't hear on it.
                returncode = self._do_run_action(
                    run,
                    action_package,
                    action,
                    input_json,
                    run_artifacts_dir,
                    result_json,
                    headers,
                    cookies,
                    reuse_process,
                )
                return returncode


def _get_process_handle_key(settings: Settings, action_package: ActionPackage) -> _Key:
    """
    Given an action provides a key where the key identifies whether a
    given action can be run at a given ProcessHandle.
    """
    from ._actions_run_helpers import get_action_package_cwd

    # Runtime descriptors namespace structured RCC evidence beneath ``runtime``;
    # canonical JSON keeps the legacy pool key hashable without making local
    # activation paths part of runtime identity.
    env = json.dumps(json.loads(action_package.env_json), sort_keys=True)
    cwd = get_action_package_cwd(settings, action_package)
    return _Key(action_package.id, env, cwd)


class ActionsProcessPool:
    def __init__(
        self,
        settings: Settings,
        action_package_id_to_action_package: Dict[str, ActionPackage],
        actions: List[Action],
    ):
        import os
        import shlex

        self._settings = settings
        # Route handlers capture this monotonically increasing token.  A
        # handler admitted before reload can therefore keep using its exact
        # package generation after this pool has switched to a new one.
        self._generation = 0
        self.action_package_id_to_action_package = action_package_id_to_action_package

        post_run_cmd = os.environ.get("ACTIONS_RUNTIME_POST_RUN_CMD")
        if not post_run_cmd:
            log.debug(
                "ACTIONS_RUNTIME_POST_RUN_CMD not set (post run will be skipped)."
            )
            self._post_run_cmd_args = None
        else:
            log.debug("ACTIONS_RUNTIME_POST_RUN_CMD set to: '%s'", post_run_cmd)
            try:
                post_run_cmd_args = shlex.split(post_run_cmd)
            except Exception:
                error_msg = f"Error. Unable to parse ACTIONS_RUNTIME_POST_RUN_CMD: '{post_run_cmd}' with shlex."
                log.exception(error_msg)
                raise RuntimeError(error_msg)

            self._post_run_cmd_args = tuple(post_run_cmd_args)

        # We just want the actions which are enabled.
        self.actions = [action for action in actions if action.enabled]

        # An iterator which keeps cycling over the actions.
        self._cycle_actions_iterator = itertools.cycle(self.actions)

        self._lock = threading.Lock()
        self._running_processes: Dict[_Key, Set[ProcessHandle]] = {}
        self._idle_processes: Dict[_Key, Set[ProcessHandle]] = {}
        self._pending_retirements: Dict[ProcessHandle, bool] = {}

        # Semaphore used to track running processes.
        self._processes_running_semaphore = threading.Semaphore(self.max_processes)

        self._warmup_processes()

    def on_reload(
        self,
        action_package_id_to_action_package: Dict[str, ActionPackage],
        actions: List[Action],
    ):
        """
        Prepare a new process generation before committing the routing switch.

        Running old-generation processes remain leased until their current
        call completes.  If preparation fails, newly-created idle workers are
        discarded and the old routing/idle generation is restored unchanged.
        """
        failure = None
        staged_to_retire = []
        old_to_retire = []
        with self._lock:
            old_action_packages = self.action_package_id_to_action_package
            old_actions = self.actions
            old_cycle_actions_iterator = self._cycle_actions_iterator
            old_idle_processes = self._idle_processes

            # Keep old idle workers out of the staged warmup, while retaining
            # them for rollback until the new generation is ready.
            self._idle_processes = {}
            self.action_package_id_to_action_package = (
                action_package_id_to_action_package
            )
            self.actions = [action for action in actions if action.enabled]
            self._cycle_actions_iterator = itertools.cycle(self.actions)

            try:
                self._warmup_processes_unlocked(include_running=False)
            except BaseException:
                new_idle_processes = self._idle_processes
                staged_to_retire = [
                    process
                    for processes in new_idle_processes.values()
                    for process in processes
                ]
                self._idle_processes = old_idle_processes
                self.action_package_id_to_action_package = old_action_packages
                self.actions = old_actions
                self._cycle_actions_iterator = old_cycle_actions_iterator
                import sys

                failure = sys.exc_info()

            if failure is None:
                # The routing switch is committed only after all new workers
                # started successfully. Old running workers drain naturally.
                old_to_retire = [
                    process
                    for processes in old_idle_processes.values()
                    for process in processes
                ]
                for running_processes in self._running_processes.values():
                    for process in running_processes:
                        process.can_reuse = False
                self._generation = getattr(self, "_generation", 0) + 1

        for process in staged_to_retire:
            self._retire_detached(process, retained_capacity=False)
        if failure is not None:
            _, error, traceback = failure
            assert error is not None
            raise error.with_traceback(traceback)
        for process in old_to_retire:
            self._retire_detached(process, retained_capacity=False)

    @property
    def generation(self) -> int:
        """Current process-generation token used by registered route handlers."""
        with self._lock:
            return getattr(self, "_generation", 0)

    def restore_generation(self, generation: int) -> None:
        """Restore the token when route registration rolls a reload back."""
        with self._lock:
            self._generation = generation

    @property
    def _reuse_processes(self) -> bool:
        """
        Returns:
            Whether processes can be reused.
        """
        return self._settings.reuse_processes

    @property
    def max_processes(self) -> int:
        """
        Returns:
            The maximum number of processes that may be created by the process
            pool.
        """
        return self._settings.max_processes

    @property
    def min_processes(self) -> int:
        return self._settings.min_processes

    def _create_process(
        self, action: Action, action_package: Optional[ActionPackage] = None
    ) -> ProcessHandle:
        if action_package is None:
            action_package = self.action_package_id_to_action_package[
                action.action_package_id
            ]

        process_handle = ProcessHandle(
            self._settings, action_package, self._post_run_cmd_args
        )
        assert self._lock.locked(), "Lock must be acquired at this point."
        self._add_to_idle_processes(process_handle)
        return process_handle

    def dispose(self):
        with self._lock:
            idle = [process for processes in self._idle_processes.values() for process in processes]
            running = [process for processes in self._running_processes.values() for process in processes]
            for process_handle in running:
                process_handle.can_reuse = False
            self._idle_processes.clear()
            self._running_processes.clear()
        for process_handle in idle:
            self._retire_detached(process_handle, retained_capacity=False)
        for process_handle in running:
            process_handle.kill()

    def get_idle_processes_count(self) -> int:
        with self._lock:
            return self._get_idle_processes_count_unlocked()

    def _get_idle_processes_count_unlocked(self) -> int:
        assert self._lock.locked(), "Lock must be acquired at this point."
        count = 0
        for v in self._idle_processes.values():
            count += len(v)
        return count

    def get_running_processes_count(self) -> int:
        with self._lock:
            return self._get_running_processes_count_unlocked()

    def _get_running_processes_count_unlocked(self) -> int:
        assert self._lock.locked(), "Lock must be acquired at this point."
        count = 0
        for v in self._running_processes.values():
            count += len(v)
        return count

    def _count_total_processes(self) -> int:
        assert self._lock.locked(), "Lock must be acquired at this point."
        count = 0
        for v in itertools.chain(
            self._running_processes.values(), self._idle_processes.values()
        ):
            count += len(v)
        count += len(getattr(self, "_pending_retirements", {}))
        return count

    def _retry_pending_retirements(self) -> None:
        with self._lock:
            pending = tuple(getattr(self, "_pending_retirements", {}))
        for process_handle in pending:
            try:
                complete = bool(process_handle.retire())
            except Exception:
                log.exception("Pending worker retirement retry failed.")
                complete = False
            if complete:
                removed = False
                with self._lock:
                    pending_retirements = getattr(self, "_pending_retirements", {})
                    if process_handle in pending_retirements:
                        retained_capacity = self._pending_retirements.pop(
                            process_handle
                        )
                        removed = True
                        if retained_capacity:
                            self._processes_running_semaphore.release()
                if removed:
                    try:
                        self._warmup_processes()
                    except Exception:
                        log.exception("Unable to warm up after pending retirement.")

    def _retire_detached(
        self, process_handle: ProcessHandle, *, retained_capacity: bool
    ) -> bool:
        try:
            complete = bool(process_handle.retire())
        except Exception:
            log.exception("Detached worker retirement failed.")
            complete = False
        if not complete:
            with self._lock:
                if not hasattr(self, "_pending_retirements"):
                    self._pending_retirements = {}
                self._pending_retirements[process_handle] = retained_capacity
        return complete

    def _add_to_idle_processes(self, process_handle: ProcessHandle):
        assert self._lock.locked(), "Lock must be acquired at this point."
        processes = self._idle_processes.get(process_handle.key)
        if processes is None:
            processes = self._idle_processes[process_handle.key] = set()
        processes.add(process_handle)

    def _add_to_running_processes(self, process_handle: ProcessHandle):
        assert self._lock.locked(), "Lock must be acquired at this point."
        processes = self._running_processes.get(process_handle.key)
        if processes is None:
            processes = self._running_processes[process_handle.key] = set()
        processes.add(process_handle)

    def _remove_from_running_processes(self, process_handle: ProcessHandle):
        assert self._lock.locked(), "Lock must be acquired at this point."
        processes = self._running_processes.get(process_handle.key)
        if not processes:
            return
        processes.discard(process_handle)

    def _warmup_processes_unlocked(self, *, include_running: bool = True):
        assert self._lock.locked(), "Lock must be acquired at this point."
        if not self.actions:
            return

        while True:
            current = (
                self._count_total_processes()
                if include_running
                else self._get_idle_processes_count_unlocked()
            )
            if current >= self._settings.min_processes:
                return
            one_action = next(self._cycle_actions_iterator)
            self._create_process(one_action)

    def _warmup_processes(self):
        with self._lock:
            self._warmup_processes_unlocked()

    @contextmanager
    def obtain_process_for_action(
        self,
        action: Action,
        runtime_info: Optional["RunRuntimeInfo"] = None,
        *,
        generation: Optional[int] = None,
        action_package: Optional[ActionPackage] = None,
    ) -> Iterator[ProcessHandle]:
        import time
        from concurrent.futures import CancelledError

        current_generation = self.generation
        request_generation = current_generation if generation is None else generation
        if action_package is None:
            action_package = self.action_package_id_to_action_package[
                action.action_package_id
            ]

        key = _get_process_handle_key(self._settings, action_package)
        process_handle: Optional[ProcessHandle] = None
        acquired_process_semaphore = False

        # Only print more info regarding delaying after 10 seconds elapse.
        print_delayed_at = time.monotonic() + 10

        try:
            while True:
                if acquired_process_semaphore:
                    # If we had previously acquired, release it now (for some reason we haven't
                    # been able to create a process after acquiring the semaphore).
                    self._processes_running_semaphore.release()
                    acquired_process_semaphore = False

                if runtime_info is not None and runtime_info.is_canceled():
                    raise CancelledError(
                        f"Action: {action.name} cancelled while waiting for process."
                    )

                # Each 2 seconds check again if we can acquire a process.
                # Important: do it without acquiring `self._lock` (as it could lead
                # to a deadlock if one depends on the other)
                acquired_process_semaphore = (
                    self._processes_running_semaphore.acquire(blocking=False)
                )
                if not acquired_process_semaphore:
                    self._retry_pending_retirements()
                    acquired_process_semaphore = (
                        self._processes_running_semaphore.acquire(timeout=2)
                    )
                if not acquired_process_semaphore:
                    if time.monotonic() > print_delayed_at:
                        log.info(
                            f"Delayed running action: {action.name} because "
                            f"{self.max_processes} actions are already running ("
                            f"waiting for another action to finish running)."
                        )
                        print_delayed_at = time.monotonic() + 10
                    continue

                with self._lock:
                    current_generation = getattr(self, "_generation", 0)
                    # Idle workers belong to the currently routed generation.
                    # A stale route may still run, but it must spawn against
                    # its captured package and never borrow a new-generation
                    # worker (or return its worker for reuse).
                    processes = (
                        self._idle_processes.get(key)
                        if request_generation == current_generation
                        else None
                    )
                    if processes:
                        # Get any process from the (compatible) idle processes.
                        process_handle = processes.pop()
                        log.debug(
                            f"Process Pool: Using idle process ({process_handle.pid})."
                        )
                        if not process_handle.is_alive():
                            # Process died while trying to get it.
                            log.critical(
                                f"Process Pool: Unexpected: Idle process exited "
                                f"({process_handle.pid})."
                            )
                            continue

                        self._add_to_running_processes(process_handle)
                    else:
                        # No compatible process: we need to create one now.
                        n_running = self._get_running_processes_count_unlocked()
                        if n_running < self.max_processes:
                            created_process = self._create_process(
                                action, action_package
                            )
                            if request_generation != current_generation:
                                # A stale route may share a key with the new
                                # generation.  Remove exactly the worker just
                                # created instead of taking an arbitrary idle
                                # worker from that shared key.
                                process_handle = created_process
                                self._idle_processes[key].remove(created_process)
                            else:
                                processes = self._idle_processes.get(key)
                                assert processes, f"Expected idle processes bound to key: {key} at this point!"
                                process_handle = processes.pop()
                            log.debug(
                                f"Process Pool: Created process ({process_handle.pid})."
                            )
                            if not process_handle.is_alive():
                                # Process died while trying to get it.
                                log.critical(
                                    f"Process Pool: Unexpected: Idle process exited right "
                                    f"after creation ({process_handle.pid})."
                                )
                                continue
                            self._add_to_running_processes(process_handle)
                            if request_generation != current_generation:
                                process_handle.can_reuse = False
                        else:
                            log.critical(
                                f"Unable to run: {action.name} because "
                                f"{self.max_processes} actions are already running "
                                "(waiting for another action to finish running). "
                                "THIS IS UNEXPECTED AT THIS POINT "
                                "(the semaphore with the max number of processes is "
                                "not working as expected)."
                            )

                if process_handle is not None:
                    break
                else:
                    continue
        except BaseException as e:
            if not isinstance(e, CancelledError):
                log.exception(
                    "CRITICAL ERROR IN Action Server Process Pool! This may make the Action Server unresponsive. Please report error!"
                )

            if acquired_process_semaphore:
                self._processes_running_semaphore.release()

            raise

        if process_handle is None:
            raise AssertionError(
                "Expected process_handle to be not None at this point!"
            )

        if not acquired_process_semaphore:
            raise AssertionError(
                "Expected 'acquired_process_semaphore' to be True at this point!"
            )

        try:
            yield process_handle
        finally:
            should_retire = False
            with self._lock:
                self._remove_from_running_processes(process_handle)
                if process_handle.is_alive():
                    if self._reuse_processes:
                        curr_idle = self._get_idle_processes_count_unlocked()
                        if not process_handle.can_reuse:
                            log.debug(
                                f"Process Pool: Exited process ({process_handle.pid}) -- process marked as non-reusable."
                            )
                            # We cannot reuse it!
                            should_retire = True

                        elif self.min_processes <= curr_idle:
                            log.debug(
                                f"Process Pool: Exited process ({process_handle.pid}) -- min processes already satisfied."
                            )
                            # We cannot reuse it!
                            should_retire = True
                        else:
                            log.debug(
                                f"Process Pool: Adding back to pool ({process_handle.pid})."
                            )
                            self._add_to_idle_processes(process_handle)
                    else:
                        log.debug(
                            f"Process Pool: Exited process ({process_handle.pid}) -- not reusing processes."
                        )
                        # We cannot reuse it!
                        should_retire = True
                else:
                    # A completed/dead handle still needs an owned wrapper wait
                    # and descendant cleanup before capacity can be returned.
                    should_retire = True

                if should_retire:
                    if not hasattr(self, "_pending_retirements"):
                        self._pending_retirements = {}
                    self._pending_retirements[process_handle] = True

            retirement_complete = False
            retirement_owns_capacity = False
            if should_retire:
                try:
                    retirement_complete = bool(process_handle.retire())
                except Exception:
                    log.exception("Worker retirement failed.")
                if retirement_complete:
                    with self._lock:
                        if process_handle in self._pending_retirements:
                            retirement_owns_capacity = self._pending_retirements.pop(
                                process_handle
                            )

            # Refill only after a successful retirement is removed from total
            # worker accounting. An unresolved handle continues to occupy its
            # capacity slot and counts toward the warmup target.
            try:
                self._warmup_processes()
            finally:
                if should_retire:
                    if retirement_owns_capacity:
                        with self._lock:
                            self._processes_running_semaphore.release()
                else:
                    self._processes_running_semaphore.release()


_actions_process_pool: Optional[ActionsProcessPool] = None


@contextmanager
def setup_actions_process_pool(
    settings: Settings,
    action_package_id_to_action_package: Dict[str, ActionPackage],
    actions: List[Action],
):
    global _actions_process_pool

    _actions_process_pool = ActionsProcessPool(
        settings, action_package_id_to_action_package, actions
    )
    yield
    _actions_process_pool = None


def get_actions_process_pool() -> ActionsProcessPool:
    assert _actions_process_pool is not None
    return _actions_process_pool
