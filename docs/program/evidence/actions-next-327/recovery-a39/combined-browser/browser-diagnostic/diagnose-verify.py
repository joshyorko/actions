import ast,json,traceback
from pathlib import Path
from actions.server.deployments.package_revision_compiler import *
from actions.server.deployments.source_manifest import SuppliedSourceEntry
root=Path(__file__).parent
module=ast.parse(Path('/workspace/actions-327-a39/browser-combined/qualify.py').read_text())
f=next(x for x in module.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='compile_counter')
values={x.targets[0].id:ast.literal_eval(x.value) for x in f.body if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id in {'source','tests'}}
entries=tuple(SuppliedSourceEntry(path=n,kind="file",content=b,mode=420) for n,b in [('package.yaml',Path('/workspace/actions-327-a39/compiler/package.yaml').read_bytes()),('generated_actions.py',values['source'].encode()),('tests/test_counter.py',values['tests'].encode())])
try:
 result=compile_generated_python_action(entries,PackageCompilationPolicy('diagnostic-counter','Independent word counter','>=1.1.0a15,<2.0.0','>=1.0.2,<2.0.0'),protected_input_names=['package.yaml'],admission=TrustedDeveloperExecutionAdmission.TRUSTED,executor=PinnedRccPackageBuildExecutor(load_prepared_rcc_environment(Path('/workspace/actions-327-a39/compiler/prepared.json'))),execution_root=root)
 (root/'receipt-verify.json').write_bytes(result.receipt.to_bytes())
 from actions.server.deployments.package_revision_compiler import _verify_compiled_package_revision
 _verify_compiled_package_revision(result.compiled_package)
 verify_compilation_outcome(result)
 print('INTEGRITY PASS')
 print(result.receipt.to_bytes().decode())
except Exception:
 (root/'verify-failure.txt').write_text(traceback.format_exc());raise
