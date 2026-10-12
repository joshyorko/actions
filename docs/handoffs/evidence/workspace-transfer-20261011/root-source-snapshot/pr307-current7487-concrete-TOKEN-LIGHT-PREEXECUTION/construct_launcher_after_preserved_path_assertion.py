from pathlib import Path
import json,hashlib,os,ast
B=Path(__file__).parent
OLD=Path('/workspace/engineering/pr307-currente2-concrete-LIGHT-PREEXECUTION-v2')
SOURCE='7487d94bf1a0453119928fe2d73d1413a252a312'
TREE='4ae715a497f1f6c643efe2a301a111320b3c18e4'
ATTEMPT='/workspace/engineering/pr307-current7487-token-light-once-owned'
CONFIG_SHA=hashlib.sha256((B/'immutable-one-TOKEN-LIGHT-inputs.json').read_bytes()).hexdigest()
s=(OLD/'launch_one_owned_light.py').read_text()
s=s.replace('/workspace/engineering/pr307-current2314-light-once-owned',ATTEMPT)
s=s.replace('current2314','current7487').replace('CURRENT2314','CURRENT7487')
s=s.replace('2314aea95795fbc1372a6f7b0b7b298b7cf124c3',SOURCE).replace('2987ed3a23e560fb40e13aadbcd6bd613ead3f25',TREE)
s=s.replace('3b4e42668cb99bc38969c6f979ece431abdd123db4217baf282c3cbb581369ce',CONFIG_SHA).replace('immutable-one-LIGHT-inputs.json','immutable-one-TOKEN-LIGHT-inputs.json')
s=s.replace('RELEASE_ONE_CURRENT7487_LIGHT_ONLY','RELEASE_ONE_CURRENT7487_TOKEN_LIGHT_ONLY').replace('GO_CURRENT7487_LIGHT_PREEXECUTION','GO_CURRENT7487_TOKEN_LIGHT_PREEXECUTION').replace('PASSED_CURRENT7487_LIGHT_ONLY','PASSED_CURRENT7487_TOKEN_LIGHT_ONLY')
needle='    assert sys.flags.optimize==0 and Path(sys.prefix).resolve()==CACHED.resolve()\n'
assert s.count(needle)==1
s=s.replace(needle,needle+"    protected=cfg['protected_repository'];protected_root=Path(protected['path'])\n    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=protected_root,text=True).strip()==protected['head']\n    assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=protected_root,text=True).strip()==protected['tree']\n    assert not subprocess.check_output(['git','status','--porcelain=v1'],cwd=protected_root)\n")
s=s.replace('def run_phase(name,command,env,budget):','def run_phase(name,command,env,budget,expected_returncode=0):').replace("terminal.update({'elapsed_seconds'", "terminal.update({'expected_returncode':expected_returncode,'elapsed_seconds'").replace("if terminal['returncode']!=0:","if terminal['returncode']!=expected_returncode:")
needle="        f_env=pytest_env(env,'guard-focus',True)\n"
assert s.count(needle)==1
added='''        # Select only immutable parent YAML through the existing test seam;
        # never replace/mutate the generator or source.
        red_env=pytest_env(env,'token-RED-parent2314',False)
        red_env['RUNTIME_RELEASE_TEST_BASELINE']='2314aea95795fbc1372a6f7b0b7b298b7cf124c3'
        run_phase('token-RED-parent2314',gateway('import toolkit; toolkit.poetry("devutils","run","python","-m","pytest","tests/test_runtime_release_workflows.py","-k","test_generated_pypi_oauth_credentials_are_scoped_to_exact_event","-n","0","-vv")'),red_env,180,expected_returncode=1)
        import xml.etree.ElementTree as ET
        red_cases=ET.parse(ATTEMPT/'token-RED-parent2314'/'junit.xml').getroot().findall('.//testcase')
        assert len(red_cases)==2
        assert {case.attrib['name'] for case in red_cases}=={'test_generated_pypi_oauth_credentials_are_scoped_to_exact_event[build-sdist]','test_generated_pypi_oauth_credentials_are_scoped_to_exact_event[build-wheels]'}
        for case in red_cases:
            assert len(case.findall('failure'))==1 and not case.findall('error') and not case.findall('skipped')
            failure=case.find('failure').text or ''
            assert 'canary.get' in failure and '${{ github.token }}' in failure
        dump(ATTEMPT/'token-RED-parent2314'/'expected-two-original-env-failures.json',{'status':'EXPECTED_RED_CONFIRMED','case_count':2,'underlying_original_pytest_exit':1,'source_unchanged':SOURCE})
        green_env=pytest_env(env,'token-release-line-GREEN',False)
        green_env.pop('RUNTIME_RELEASE_TEST_BASELINE',None)
        run_phase('token-release-line-GREEN',gateway('import toolkit; toolkit.poetry("devutils","run","python","-m","pytest","tests/test_runtime_release_workflows.py","tests/test_actions_runtime_release_line.py","-n","0","-vv")'),green_env,180)
'''
s=s.replace(needle,added+needle)
needle="        assert not list((CACHED/'lib/python3.12/site-packages').glob('*log*pytest*'))\n"
assert s.count(needle)==1
s=s.replace(needle,needle+"        assert not list((ROOT/'devutils/.venv/lib/python3.12/site-packages').glob('*log*pytest*'))\n        assert list((ROOT/'action_server/.venv/lib/python3.12/site-packages').glob('*log*pytest*.dist-info'))\n")
needle='toolkit.poetry("action_server","run","mypy","scripts/build_oauth2_config.py")'
assert s.count(needle)==1
s=s.replace(needle,needle+'; toolkit.poetry("devutils","run","ruff","check","src","tests"); toolkit.poetry("devutils","run","ruff","format","--check","--config","ruff.toml","src","tests"); toolkit.poetry("devutils","run","isort","--check","src","tests"); toolkit.poetry("devutils","run","mypy","--follow-imports=silent","--namespace-packages","--explicit-package-bases","src")')
assert ATTEMPT in s and 'GO_CURRENT7487_TOKEN_LIGHT_PREEXECUTION' in s and 'RELEASE_ONE_CURRENT7487_TOKEN_LIGHT_ONLY' in s
ast.parse(s)
p=B/'launch_one_owned_token_light.py'
fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o444);os.write(fd,s.encode());os.close(fd)
print(json.dumps({'path':str(p),'bytes':len(s.encode()),'sha256':hashlib.sha256(s.encode()).hexdigest(),'status':'AST_ONLY_NOT_EXECUTED'}))
