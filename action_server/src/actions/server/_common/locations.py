import os
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache
def get_default_actions_home_dir() -> Path:
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
    return home


def get_default_executable_path(name: str, version: str) -> Path:
    """
    Provides the default path for an Actions-managed executable.

    Args:
        name: The name of the executable (i.e.: "action-server", "agent-cli", etc).
        version: The version of the executable.

    Returns:
        The path to the executable. Something as:
        <actions_home>/bin/action-server/0.1.0/action-server.exe
    """

    # We need to download the action server to the default Actions home dir
    # because the action server will use it to store the actions.

    action_server_download_dir = get_default_actions_home_dir() / "bin" / name / version

    suffix = ""
    if sys.platform == "win32":
        suffix = ".exe"

    target_location = action_server_download_dir / f"{name}{suffix}"
    return target_location
