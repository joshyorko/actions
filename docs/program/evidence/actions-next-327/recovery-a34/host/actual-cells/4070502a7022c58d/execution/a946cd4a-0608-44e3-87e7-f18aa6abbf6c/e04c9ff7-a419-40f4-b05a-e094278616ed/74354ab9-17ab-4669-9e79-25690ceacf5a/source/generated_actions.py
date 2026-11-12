from actions import action
import os,time
from pathlib import Path
@action
def generated_echo(value: str) -> str:
    if value == "pause":
        (Path(os.environ["TMPDIR"])/"task-host-entered").write_text("owned synthetic test")
        time.sleep(30)
    if value == "hello":
        time.sleep(0.25)
    return value
