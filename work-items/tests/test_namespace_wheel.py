import subprocess
import zipfile
from pathlib import Path


def test_wheel_omits_root_actions_initializer(tmp_path):
    subprocess.run(
        ["poetry", "build", "-f", "wheel", "-o", str(tmp_path)],
        check=True,
        cwd=Path(__file__).parents[1],
    )

    wheel = next(tmp_path.glob("actions_work_items-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    assert "actions/__init__.py" not in names
    assert "actions/work_items/__init__.py" in names
