from actions import action
import hashlib
import actions
import sys
from importlib.metadata import version
from pathlib import Path

@action
def staged_source_probe() -> dict[str, str]:
    source = Path(__file__).resolve()
    core = Path(actions.__file__).resolve()
    return {
        'action_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'action_source_path': str(source),
        'core_origin': str(core),
        'core_version': version('actions-core'),
        'python_executable': str(Path(sys.executable).resolve()),
    }
