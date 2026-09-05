import logging
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterator, Optional

from termcolor import colored

from actions.server._protocols import ArgumentsNamespaceDevEnvTask
from actions.server.vendored_deps.termcolors import bold_red

from ._protocols import ArgumentsNamespaceRequiringDatadir

# Header constants

# Something as "0.2" to set time after which the action server will unblock the request and return that completion will be asynchronous.
HEADER_ACTIONS_ASYNC_TIMEOUT = "x-actions-async-timeout"

# A request id that can be converted to a run id later on to cancel the action, get the status, result, etc.
HEADER_ACTIONS_REQUEST_ID = "x-actions-request-id"

# Can be set to a callback url that will be called when the action is completed.
HEADER_ACTIONS_ASYNC_CALLBACK = "x-actions-async-callback"

# The run id to cancel the action, get the status, result, etc (set as a header in the response).
HEADER_ACTION_SERVER_RUN_ID = "x-action-server-run-id"

# Set to "1" in the response if the action will finish asynchronously.
HEADER_ACTION_ASYNC_COMPLETION = "x-action-async-completion"

# A context that will be passed to the action with information on the request (agent id, thread id, etc).
HEADER_ACTION_INVOCATION_CONTEXT = "x-action-invocation-context"

# boolean (true if the action is consequential -- i.e.: it'll change the state of the world, false means it's an action that shouldn't change anything).
# Set in the openapi spec.
OPENAPI_SPEC_IS_CONSEQUENTIAL = "x-openai-isConsequential"

# 'action' or 'query' (set in the openapi spec).
OPENAPI_SPEC_OPERATION_KIND = "x-operation-kind"

log = logging.getLogger(__name__)


def _get_redis_url_from_env() -> Optional[str]:
    """
    Auto-detect Redis URL from environment variables.

    Checks multiple common environment variable names for Redis configuration.
    Returns the first non-empty value found, or None if no Redis URL is configured.
    """
    for var in ["ACTION_SERVER_REDIS_URL", "REDIS_URL"]:
        if url := os.environ.get(var):
            return url
    return None


def is_frozen():
    if getattr(sys, "frozen", False):
        return True
    try:
        __file__
    except NameError:
        return True

    return False


def get_python_exe_from_env(env):
    python = env.get("PYTHON_EXE")
    if not python:
        if is_frozen():
            raise RuntimeError(
                "Unable to run because no 'package.yaml' was present to bootstrap the environment\n"
                "(note: when the action server is distributed without sources, an 'package.yaml' for "
                "the target environment is always required)."
            )
        else:
            python = sys.executable

    return python


def _legacy_get_default_settings_dir() -> Path:
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if not localappdata:
            raise RuntimeError("Error. LOCALAPPDATA not defined in environment!")
        path = Path(localappdata) / "robocorp" / ".action_server"
    else:
        # Linux/Mac
        path = Path("~/.robocorp/.action_server").expanduser()
    return path


@lru_cache
def get_default_settings_dir() -> Path:
    # Check for env vars (support both new and legacy)
    home_env_var = os.environ.get("ACTIONS_HOME")
    if home_env_var:
        home = Path(home_env_var)
    else:
        if sys.platform == "win32":
            localappdata = os.environ.get("LOCALAPPDATA")
            if not localappdata:
                raise RuntimeError("Error. LOCALAPPDATA not defined in environment!")
            home = Path(localappdata) / "actions"
        else:
            # Linux/Mac
            home = Path("~/.actions").expanduser()

    default_settings_dir = home / "action-server"

    # Notify users about backward incompatible change
    # (as this is lru-cached, should notify only once).
    old_dir = _legacy_get_default_settings_dir()
    if os.path.exists(old_dir):
        log.critical(
            bold_red(
                f"""Note: the action server settings are now stored in:
{default_settings_dir}

instead of:
{old_dir}

If you want to keep data on old runs, consider moving
the contents of {old_dir} to {default_settings_dir}

-- otherwise, please remove:
{old_dir}

so that this message is no longer shown.
"""
            )
        )

    default_settings_dir.mkdir(parents=True, exist_ok=True)
    return default_settings_dir


@lru_cache
def get_user_actions_path() -> Path:
    """Get user's actions home directory."""
    home_env_var = os.environ.get("ACTIONS_HOME")
    if home_env_var:
        home = Path(home_env_var)
    elif sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if not localappdata:
            raise RuntimeError("Error. LOCALAPPDATA not defined in environment!")
        home = Path(localappdata) / "actions"
    else:
        # Linux/Mac
        home = Path("~/.actions").expanduser()

    user_actions_path = home / "action-server"
    user_actions_path.mkdir(parents=True, exist_ok=True)
    return user_actions_path


@lru_cache
def get_actions_home() -> Path:
    """
    Get RCC home directory for action executions.

    Uses ACTIONS_HOME env var if set, otherwise defaults to ~/.actions.
    This provides a separate holotree from robots to avoid lock contention.
    """
    actions_home_env = os.environ.get("ACTIONS_HOME")
    if actions_home_env:
        home = Path(actions_home_env).expanduser()
    else:
        if sys.platform == "win32":
            localappdata = os.environ.get("LOCALAPPDATA")
            if not localappdata:
                raise RuntimeError("Error. LOCALAPPDATA not defined in environment!")
            home = Path(localappdata) / "actions"
        else:
            # Linux/Mac
            home = Path("~/.actions").expanduser()

    home.mkdir(parents=True, exist_ok=True)
    return home


@lru_cache
def get_robots_home() -> Path:
    """
    Get RCC home directory for robot executions.

    Uses ROBOTS_HOME env var if set, otherwise defaults to ~/.robots.
    This provides a separate holotree from actions to avoid lock contention.
    """
    robots_home_env = os.environ.get("ROBOTS_HOME")
    if robots_home_env:
        home = Path(robots_home_env).expanduser()
    else:
        if sys.platform == "win32":
            localappdata = os.environ.get("LOCALAPPDATA")
            if not localappdata:
                raise RuntimeError("Error. LOCALAPPDATA not defined in environment!")
            home = Path(localappdata) / "robots"
        else:
            # Linux/Mac
            home = Path("~/.robots").expanduser()

    home.mkdir(parents=True, exist_ok=True)
    return home


@dataclass(slots=True, kw_only=True)
class Settings:
    artifacts_dir: Path
    datadir: Path

    artifact_storage_backend: str = "local"
    artifact_storage_root: Optional[Path] = None

    title: str = "Actions Runtime"

    address: str = "localhost"
    port: int = 8080
    verbose: bool = False
    db_file: str = "server.db"
    database_url: Optional[str] = None
    expose_provider: str = "auto"
    server_url: str = "<generated -- i.e.: http://localhost:8080>"

    min_processes: int = 2
    max_processes: int = 20
    reuse_processes: bool = False

    full_openapi_spec: bool = False

    use_https: bool = False

    ssl_self_signed: bool = False
    ssl_keyfile: str = ""  # The path to the server.key
    ssl_certfile: str = ""  # The path to the certificate.pem (contains the public key)

    oauth2_settings: str = ""

    # This is set after the server is started
    # (so, even if the port is 0, it should map to the actually mapped port).
    base_url: Optional[str] = None

    # Scheduler settings
    enable_scheduler: bool = True
    scheduler_check_interval: float = 10.0  # seconds
    scheduler_max_concurrent_global: int = 10

    # Trigger settings
    enable_triggers: bool = True
    trigger_webhook_base_url: Optional[str] = None  # For generating webhook URLs

    # Notification settings
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_use_tls: bool = True

    # Distributed mode settings (auto-enabled when Redis is available)
    # Redis URL can be provided via --redis-url flag or REDIS_URL/ACTION_SERVER_REDIS_URL env vars
    redis_url: Optional[str] = None
    redis_password: Optional[str] = None

    # Worker settings (distributed mode)
    worker_concurrency: int = 4
    worker_poll_timeout: int = 30

    @classmethod
    def defaults(cls):
        fields = cls.__dataclass_fields__
        ret = {}
        SENTINEL = []
        for name, field in fields.items():
            v = getattr(field, "default", SENTINEL)
            if v is not SENTINEL:
                ret[name] = v
        return ret

    @classmethod
    def _create(
        cls, args: ArgumentsNamespaceRequiringDatadir | ArgumentsNamespaceDevEnvTask
    ) -> "Settings":
        from actions.server._errors_action_server import ActionServerValidationError

        user_specified_datadir = args.datadir
        if not user_specified_datadir:
            import hashlib

            curr_cwd_dir = Path(".").absolute()
            name = curr_cwd_dir.name
            as_posix = curr_cwd_dir.as_posix()
            if sys.platform == "win32":
                as_posix = as_posix.lower()

            # Not secure, but ok for our purposes
            short_hash = hashlib.sha256(as_posix.encode()).hexdigest()[:8]
            datadir_name = f"{get_default_settings_dir()}/{name}_{short_hash}"

            log.info(colored(f"Using datadir: {datadir_name}", attrs=["dark"]))
            user_expanded_datadir = Path(datadir_name).expanduser()

        else:
            log.info(f"Using user-specified datadir: {user_specified_datadir}")
            user_expanded_datadir = Path(user_specified_datadir).expanduser()

        datadir = user_expanded_datadir.absolute()

        settings = Settings(
            datadir=datadir,
            artifacts_dir=datadir / "artifacts",
            artifact_storage_root=datadir / "artifacts",
        )

        # Optional (just in 'start' command, not in 'import')
        for attr in (
            "address",
            "port",
            "min_processes",
            "max_processes",
            "reuse_processes",
            "full_openapi_spec",
            "ssl_self_signed",
            "ssl_keyfile",
            "ssl_certfile",
            "oauth2_settings",
            "expose_provider",
            # Distributed mode (Redis)
            "redis_url",
            "redis_password",
            "database_url",
            "artifact_storage_backend",
            "artifact_storage_root",
        ):
            assert hasattr(settings, attr)
            if hasattr(args, attr):
                setattr(settings, attr, getattr(args, attr))

        if settings.artifact_storage_backend == "shared-filesystem":
            if settings.artifact_storage_root is None:
                raise ActionServerValidationError(
                    "--artifact-storage-root is required with --artifact-storage-backend shared-filesystem."
                )
        elif settings.artifact_storage_root is None:
            settings.artifact_storage_root = settings.artifacts_dir

        if hasattr(args, "https"):
            settings.use_https = args.https

        protocol = "https" if settings.use_https else "http"

        if settings.use_https:
            if not settings.ssl_self_signed:
                if not settings.ssl_keyfile or not settings.ssl_certfile:
                    raise ActionServerValidationError(
                        "When --https is used, either `--ssl-self-signed` must be passed or the `--ssl-keyfile` and `--ssl-certfile` arguments must be provided."
                    )
            else:
                if settings.ssl_keyfile or settings.ssl_certfile:
                    raise ActionServerValidationError(
                        "When `--ssl-self-signed`is passed `--ssl-keyfile` and `--ssl-certfile` should not be provided (a key/certificate will be generated in the default location)."
                    )

        if hasattr(args, "server_url") and args.server_url is not None:
            settings.server_url = args.server_url
        else:
            settings.server_url = f"{protocol}://{settings.address}:{settings.port}"

        # Used in either import or start commands.
        settings.verbose = args.verbose

        if hasattr(args, "db_file"):
            settings.db_file = args.db_file
        if not settings.database_url:
            settings.database_url = os.environ.get("ACTION_SERVER_DATABASE_URL")
        if settings.database_url:
            from ._database import normalize_database_url

            settings.database_url = str(normalize_database_url(settings.database_url))

        if args.command == "start":
            # At this point, if using a self-signed certificate, it'll be
            # created and ssl_keyfile/ssl_certfile will be set.
            user_path = get_user_actions_path()

            if settings.use_https:
                if settings.ssl_self_signed:
                    from actions.server.vendored_deps import gen_certificate
                    from actions.server.vendored_deps.termcolors import bold

                    private_path = user_path / "action-server-private-keyfile.pem"
                    public_path = user_path / "action-server-public-certfile.pem"

                    if not private_path.exists() or not public_path.exists():
                        from actions.server._storage import KEY_FILE_PERMISSIONS

                        public, private = gen_certificate.gen_self_signed_certificate()

                        public_path.write_bytes(public)
                        private_path.write_bytes(private)
                        private_path.chmod(KEY_FILE_PERMISSIONS)

                    log.info(
                        f"Self-signed certificate being used at: {bold(public_path)}\n  Note: accessing the `Action Server` with browser will require adding an exception in the browser unless the certificate is manually imported in the system."
                    )

                    settings.ssl_keyfile = str(private_path)
                    settings.ssl_certfile = str(public_path)
                else:
                    # Note: this was already previously checked.
                    assert settings.ssl_keyfile and settings.ssl_certfile

            if not settings.oauth2_settings:
                settings.oauth2_settings = str(user_path / "oauth2_config.yaml")

            # Auto-detect Redis URL from environment if not provided via CLI
            if not settings.redis_url:
                settings.redis_url = _get_redis_url_from_env()

            # Check for redis password from environment if not provided
            if settings.redis_url and not settings.redis_password:
                settings.redis_password = os.environ.get("ACTION_SERVER_REDIS_PASSWORD")

            # Log Redis configuration if available
            if settings.redis_url:
                log.info(
                    colored(
                        f"Distributed mode enabled (Redis: {settings.redis_url})",
                        attrs=["bold"],
                    )
                )

        return settings

    def to_uvicorn(self) -> dict:
        """
        Provides keyword arguments that will later be used
        to create a `uvicorn.Config` instance.
        """

        ret = {
            "host": self.address,
            "port": self.port,
            "reload": False,
            "log_config": None,
        }

        if self.use_https:
            ret["ssl_keyfile"] = self.ssl_keyfile
            ret["ssl_certfile"] = self.ssl_certfile

        return ret


_global_settings: Optional[Settings] = None


@contextmanager
def setup_settings(
    args: ArgumentsNamespaceRequiringDatadir | ArgumentsNamespaceDevEnvTask,
) -> Iterator[Settings]:
    global _global_settings
    settings = Settings._create(args)
    _global_settings = settings
    try:
        yield settings
    finally:
        _global_settings = None


def get_settings() -> Settings:
    if _global_settings is None:
        raise AssertionError("It seems that the settings have not been setup yet.")
    return _global_settings
