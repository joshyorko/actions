"""Run package commands with the freshly resolved RCC toolchain and Poetry boundary."""
import json, os, pathlib, subprocess, sys
root=pathlib.Path('/workspace/actions-pr313')
env=os.environ.copy()
env.update({x['key']:x['value'] for x in json.loads(pathlib.Path('/workspace/successor-evidence/pr313-toolkit-vars.json').read_text())})
for k in ('VIRTUAL_ENV','POETRY_ACTIVE','CONDA_PREFIX','CONDA_DEFAULT_ENV','PYTHONHOME','PYTHONPATH','PYTHON_EXE','ROBOT_ROOT','ROBOT_ARTIFACTS'):
 env.pop(k,None)
env.update(POETRY_VIRTUALENVS_CREATE='true',POETRY_VIRTUALENVS_IN_PROJECT='true',POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES='false',POETRY_CACHE_DIR='/workspace/successor-toolkit/cache/poetry',TMPDIR='/workspace/successor-toolkit/tmp',ACTIONS_HOME='/workspace/successor-evidence/pr307-actions-home',ROBOTS_HOME='/workspace/successor-evidence/pr307-robots-home',ROBOCORP_HOME='/workspace/successor-toolkit/robocorp',npm_config_cache='/workspace/successor-toolkit/cache/npm',UV_CACHE_DIR='/workspace/successor-toolkit/cache/uv',PYTEST_XDIST_AUTO_NUM_WORKERS='2',ACTIONS_RUNTIME_TEST_PYTHON=str(root/'action_server/.venv/bin/python'))
package,*command=sys.argv[1:]
raise SystemExit(subprocess.run(command,cwd=root/package,env=env).returncode)
