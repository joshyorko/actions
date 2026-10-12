import toolkit
code="""import importlib.util,json,traceback
from pathlib import Path
p=Path('/workspace/engineering/pr221-current776-linux-consumer-preflight/current-input-admission-v2.py')
s=importlib.util.spec_from_file_location('old_current_input_gate',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
v=json.loads(Path('/workspace/engineering/pr221-current618-linux-consumer-preflight/input-and-source-admission.json').read_text())
try:m.admit(Path(v['original_archive']['path_private']),Path(v['original_selected_wheel']['private_path']),v,Path('/workspace/engineering/pr282'))
except AssertionError:
 traceback.print_exc();print('EXPECTED_RED_OLD_ARTIFACT_LITERAL_RECORD215_REJECTS_NEW221_NO_CONSUMER');raise SystemExit(0)
raise AssertionError('Expected original artifact-specific guard to reject different current count')
"""
toolkit.poetry('action_server','run','python','-c',code)
