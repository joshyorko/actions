import sys,json,hashlib,traceback,importlib.metadata
from pathlib import Path
b=Path(__file__).resolve().parent
sys.argv=['helper',str(b),str(b/'input.json'),str(b/'result.json')]
try:exec(compile((b/'helper.py').read_text(),str(b/'helper.py'),'exec'),{})
except TypeError as exc:
 assert str(exc)=='Object of type Report is not JSON serializable'
 result={'status':'REPRODUCED','exception_type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc(),'core_version':importlib.metadata.version('actions-core'),'pydantic_version':importlib.metadata.version('pydantic'),'helper_sha256':hashlib.sha256((b/'helper.py').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((b/'generated_actions.py').read_bytes()).hexdigest(),'isolated':bool(sys.flags.isolated),'scope':'actual frozen helper inside exact trusted compiler artifact; independent reproduction, not recovered original child stderr'}
 assert result['core_version']=='1.1.0a5'
 assert not (b/'result.json').exists()
 (b/'proof.json').write_text(json.dumps(result,indent=2)+'\n')
else:raise AssertionError('expected actual frozen helper TypeError')
