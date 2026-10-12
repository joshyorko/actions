"""Known9 semantic RED/fresh GREEN pairs; requires separate review and ROOT release."""
import argparse,datetime,hashlib,json,os,stat,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET

BASE=Path('/workspace/engineering/pr308-known-nine-18-semantic-JUnit-envelope-once2-preexecution-NOTRUN')
CONFIG=BASE/'FROZEN-known-nine18-JUnit-envelope-once2-config-NOTRUN.json'
CONFIG_SHA='90bc9cff117ad704cfd9c1656b6e92d0d753e02438b963163aebc6a645dcf5e7'
CACHED='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'

def need(ok,code):
    if not ok:raise ValueError(code)

def binding(path):
    path=Path(path);metadata=path.lstat()
    need(stat.S_ISREG(metadata.st_mode) and not path.is_symlink(),'SEMANTIC_REGULAR_FILE')
    body=path.read_bytes()
    return {'path':str(path),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'mode':oct(stat.S_IMODE(metadata.st_mode))}

def read(row):
    need(binding(row['path'])==row,'SEMANTIC_BOUND_IDENTITY')
    return Path(row['path']).read_bytes()

def durable(path,body,mode=0o600):
    if not isinstance(body,bytes):body=(json.dumps(body,indent=2,sort_keys=True)+'\n').encode()
    with path.open('xb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
    path.chmod(mode)
    descriptor=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)

def physical(path,mode):
    metadata=Path(path).lstat()
    need(stat.S_ISREG(metadata.st_mode) and not Path(path).is_symlink() and stat.S_IMODE(metadata.st_mode)==mode
         and metadata.st_uid==os.getuid()==1000 and metadata.st_gid==os.getgid()==1000,'SEMANTIC_OPERATOR_PHYSICAL_IDENTITY')

def decode_semantic_failure(path,phase,limit,source_path):
    metadata=path.lstat();need(stat.S_ISREG(metadata.st_mode) and not path.is_symlink() and metadata.st_size<=limit,'SEMANTIC_ROBOLOG_IDENTITY_OR_SIZE')
    memo={};locations={};task=None;starts=[];ends=[];stack=[];traces=[]
    for index,line in enumerate(path.read_text().splitlines(),1):
        typ,_,value=line.partition(' ')
        if typ=='M':
            key,body=value.split(':',1);memo[key]=json.loads(body)
        elif typ=='P':
            key,body=value.split(':',1);parts=body.split('|');locations[key]=[memo[x] for x in parts[:4]]+[int(parts[4])]
        elif typ=='ST':
            parts=value.split('|');task=locations[parts[0]][0]
            if task.startswith('test_'):starts.append(task)
        elif typ=='ET':
            parts=value.split('|')
            if task and task.startswith('test_'):ends.append({'task':task,'status':memo[parts[0]]})
            task=None
        elif typ=='STB':
            parts=value.split('|');stack.append({'task':task,'exception':memo[parts[0]],'frames':[]})
        elif typ=='TBE':
            parts=value.split('|')
            if stack:stack[-1]['frames'].append({'source':memo[parts[0]],'line':int(parts[1]),'function':memo[parts[2]],'assertion':memo[parts[3]],'record_line':index})
        elif typ=='ETB':
            need(bool(stack),'SEMANTIC_ROBOLOG_TRACE_BALANCE');traces.append(stack.pop())
    need(starts==[phase['test']] and ends==[{'task':phase['test'],'status':'FAIL'}] and not stack,'SEMANTIC_EXACT_FAILED_LOG_TASK')
    pred=phase['predicate'];wanted=[]
    for trace in traces:
        if trace['task']!=phase['test'] or not trace['exception'].startswith('AssertionError:'):continue
        for frame in trace['frames']:
            if (Path(frame['source']).resolve()==Path(source_path).resolve() and Path(frame['source']).name==pred['source_file'] and frame['line']==pred['source_line']
                and frame['function']==pred['source_function'] and frame['assertion'].strip()==pred['assertion_source']):
                wanted.append(frame)
    need(bool(wanted),'SEMANTIC_INTENDED_ASSERTION_FRAME_REQUIRED')
    return {'robolog_binding':binding(path),'actual_test':phase['test'],'actual_task_status':'FAIL','intended_assertion_frames':wanted,'exception_class':'AssertionError'}

def admit_phase(phase,outcome,cfg):
    need(outcome.get('returncode')==phase['expected_returncode'],'SEMANTIC_WRONG_RC_OR_TIMEOUT')
    junit=Path(phase['junit']);physical(junit,0o600)
    need(junit.stat().st_size<=cfg['JUnit_max_decode_bytes'],'SEMANTIC_JUNIT_SIZE')
    tree=ET.fromstring(junit.read_bytes());cases=list(tree.iter('testcase'))
    need(len(cases)==1 and cases[0].get('name')==phase['test'],'SEMANTIC_EXACT_ONE_CASE')
    case=cases[0];failure=case.find('failure');error=case.find('error');skip=case.find('skipped')
    counts={'passed':int(failure is None and error is None and skip is None),'failed':int(failure is not None),'errors':int(error is not None),'skipped':int(skip is not None)}
    need(counts==phase['expected_counts'],'SEMANTIC_CASE_COUNTS')
    suites=list(tree.iter('testsuite'));reported={key:sum(int(s.get(key,'-1')) for s in suites) for key in ('tests','failures','errors','skipped')}
    need(bool(suites) and reported=={'tests':1,'failures':counts['failed'],'errors':0,'skipped':0},'SEMANTIC_SUITE_ENVELOPE')
    result={'junit_binding':binding(junit),'actual_counts':counts,'actual_reported_counts':reported,'test':phase['test'],'phase':phase['kind'],'label':phase['label']}
    if phase['kind']=='RED':
        need('type' not in failure.attrib or failure.get('type')=='AssertionError','SEMANTIC_RED_EXCEPTION_TYPE')
        text=''.join(failure.itertext())+'\n'+failure.get('message','')
        need('PRIVATE_MUTANT_MUST_CHANGE_EXACTLY_ONE_CURRENT_SEAM' not in text,'SEMANTIC_MUTATOR_SANITY_IS_NOT_RED')
        result['semantic_assertion']=decode_semantic_failure(Path(phase['output_parent'])/'pytest-logging/output.robolog',phase,cfg['raw_log_max_decode_bytes'],cfg['test_source']['path'])
    else:need(failure is None and error is None and skip is None,'SEMANTIC_RESTORED_GREEN')
    return result

parser=argparse.ArgumentParser();parser.add_argument('--release',required=True);parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
physical(CONFIG,0o400);physical(Path(__file__).resolve(),0o400)
config_binding=binding(CONFIG);need(config_binding['sha256']==CONFIG_SHA,'SEMANTIC_CONFIG_SHA');cfg=json.loads(read(config_binding))
need(cfg['schema']==1 and cfg['source_leaves']==1440 and len(cfg['phases'])==18 and len(cfg['case_order'])==9,'SEMANTIC_CONFIG_SCHEMA')
physical(Path(args.release),0o600);need(Path(args.release)==Path(cfg['root_release_path']),'SEMANTIC_ROOT_RELEASE_PATH')
release_binding=binding(args.release);need(release_binding['sha256']==args.release_sha256,'SEMANTIC_ROOT_RELEASE_SHA');release=json.loads(read(release_binding))
self_binding=binding(Path(__file__).resolve())
expected={'schema':1,'scope':cfg['required_release_scope'],'source':cfg['source'],'tree':cfg['tree'],'config_binding':config_binding,'launcher_binding':self_binding,'baseline_dependency':cfg['baseline_dependency'],'serialized_no_other_heavy_or_storage_mutations':True}
need(set(release)==set(expected)|{'independent_review'},'SEMANTIC_ROOT_RELEASE_KEYS')
for key,value in expected.items():need(type(release[key]) is type(value) and release[key]==value,'SEMANTIC_ROOT_RELEASE_SCOPE')
review=json.loads(read(release['independent_review']))
for key,value in {'schema':1,'status':cfg['required_review_status'],'source':cfg['source'],'tree':cfg['tree'],'config_sha256':CONFIG_SHA,'launcher_sha256':self_binding['sha256']}.items():need(type(review.get(key)) is type(value) and review[key]==value,'SEMANTIC_INDEPENDENT_PREEXEC')
need(not sys.flags.optimize and 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ and 'RCC_RELOAD_PRIVATE_MUTANT' not in os.environ,'SEMANTIC_NO_INHERITED_OVERRIDE')
need(Path(sys.executable).resolve()==Path(CACHED).resolve(),'SEMANTIC_CACHED_PARENT_INTERPRETER')
need(len(cfg['activation'])==18 and all(os.environ.get(k)==v for k,v in cfg['activation'].items()),'SEMANTIC_ACTIVATION18')
need(os.environ['PATH'].split(os.pathsep)[:2]==cfg['path_prefix2'] and all(k not in os.environ for k in cfg['forbidden_operator_exports']),'SEMANTIC_PATH_AND_OPERATORS')
for row in cfg['original_bindings']:read(row)
baseline=json.loads(read(cfg['baseline_dependency']));need(baseline['decision']=='GO_ORIGINAL_CURRENT8D49_CORRECTED_NINE_ONCE2_BASELINE_ONLY' and baseline['source']==cfg['source'] and baseline['tree']==cfg['tree'],'SEMANTIC_ACTUAL_BASELINE_DEPENDENCY')
need({k:baseline['counts'][k] for k in ('passed','failed','errors','skipped')}=={'passed':9,'failed':0,'errors':0,'skipped':0} and baseline['counts']['unique_cases']==9 and baseline['exact_existing_case_names']==cfg['case_order'],'SEMANTIC_BASELINE_NINE_GENUINE_PASS')
need(all(row['returncode']==0 for row in baseline['all8_original_phase_statuses'].values()),'SEMANTIC_BASELINE_ALL_OUTCOMES')
owned=Path(cfg['root_once']);need(not owned.exists() and not owned.is_symlink(),'SEMANTIC_ONCE_ROOT_ABSENT');os.umask(0o077);owned.mkdir(mode=0o700,exist_ok=False)
durable(owned/'consumed-distinct-root-release.json',{'release_binding':release_binding,'release':release,'native':'NOT_RUN'})
outcomes={};admitted=[];started=time.monotonic();failure=None

def run(name,argv,parent_seconds,parent):
    begin=time.monotonic()
    with (parent/'original.stdout.private').open('xb') as stdout,(parent/'original.stderr.private').open('xb') as stderr:
        try:
            result=subprocess.run(argv,cwd='/workspace/engineering/pr308/action_server',stdout=stdout,stderr=stderr,timeout=parent_seconds,check=False)
            outcome={'returncode':result.returncode,'elapsed_seconds':time.monotonic()-begin}
        except BaseException as error:outcome={'exception_class':type(error).__name__,'elapsed_seconds':time.monotonic()-begin}
        stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
    outcome.update({'stdout_binding':binding(parent/'original.stdout.private'),'stderr_binding':binding(parent/'original.stderr.private'),'argv':argv,'parent_seconds':parent_seconds})
    durable(parent/'original-terminal.json',outcome);outcomes[name]=outcome;return outcome

try:
    before=owned/'before';before.mkdir(mode=0o700)
    need(run('before',cfg['guard_argv'],cfg['guard_parent_seconds'],before).get('returncode')==0,'SEMANTIC_BEFORE_GUARD')
    for index,row in enumerate(cfg['origins']):
        parent=owned/('own-origin-'+str(index));parent.mkdir(mode=0o700)
        code='import importlib,pathlib,sys; m=importlib.import_module('+repr(row['module'])+'); assert pathlib.Path(sys.prefix).resolve()==pathlib.Path('+repr(row['prefix'])+').resolve(); assert pathlib.Path(m.__file__).resolve()==pathlib.Path('+repr(row['origin'])+').resolve()'
        argv=['timeout','--signal=TERM','--kill-after=10s','15s',row['python'],'-c',code]
        need(run('own-origin-'+str(index),argv,cfg['origin_parent_seconds'],parent).get('returncode')==0,'SEMANTIC_OWN_ORIGIN')
    for index,phase in enumerate(cfg['phases']):
        need(phase['kind']==('RED' if index%2==0 else 'RESTORED_GREEN'),'SEMANTIC_PAIR_ORDER')
        if index%2:need(admitted[-1]['label']==phase['label'] and admitted[-1]['phase']=='RED','SEMANTIC_GREEN_REQUIRES_INTENDED_RED')
        read(cfg['test_source'])
        parent=Path(phase['output_parent']);need(parent.parent==owned and not parent.exists() and not parent.is_symlink(),'SEMANTIC_FRESH_PHASE');parent.mkdir(mode=0o700)
        for child in ('basetemp','pytest-logging','original-junit.xml'):need(not (parent/child).exists() and not (parent/child).is_symlink(),'SEMANTIC_ABSENT_CHILD')
        outcome=run(phase['label']+'-'+phase['kind'],phase['argv'],phase['parent_seconds'],parent)
        admission=admit_phase(phase,outcome,cfg);durable(parent/'original-semantic-admission.json',admission);admitted.append(admission)
except BaseException as error:
    failure={'exception_class':type(error).__name__}
    durable(owned/'original-primary-failure.private.json',{'exception_class':type(error).__name__,'private_error_text':str(error)})
finally:
    try:
        parent=owned/'always-post';parent.mkdir(mode=0o700)
        post=run('always-post',cfg['guard_argv'],cfg['guard_parent_seconds'],parent)
        if post.get('returncode')!=0 and failure is None:failure={'code':'SEMANTIC_ALWAYSPOST_FAILED'}
        for row in cfg['original_bindings']:read(row)
        for row in (config_binding,self_binding,release_binding,release['independent_review']):read(row)
    except BaseException as error:
        if failure is None:failure={'post_exception_class':type(error).__name__}
        durable(owned/'original-post-failure.private.json',{'exception_class':type(error).__name__,'private_error_text':str(error)})
result={'schema':1,'status':'PASS_KNOWN9_SEMANTIC_RED_FRESH_GREEN_SOURCE_ONLY' if len(admitted)==18 and failure is None else 'FAIL_OR_HOLD_STOP_NO_RETRY','source':cfg['source'],'tree':cfg['tree'],'launcher_binding':self_binding,'config_binding':config_binding,'release_binding':release_binding,'independent_review':release['independent_review'],'actual_baseline_dependency':cfg['baseline_dependency'],'outcomes':outcomes,'semantic_admitted_phases':admitted,'failure':failure,'elapsed_seconds':time.monotonic()-started,'capture':datetime.datetime.now(datetime.timezone.utc).isoformat(),'native':'NOT_RUN','snapshot_oracle_sensitivity':'NOT_RUN_SEPARATE_REQUIRED','source_adoption':'NONE','phase_census':'ORIGINAL18JUNIT_AND_RAW_REQUIRED_INDEPENDENT_ACTUAL_REVIEW'}
durable(owned/'OWNERFINAL-root-one-original-known-nine-18-semantic-RED-restored-GREEN.json',result,0o400)
print(json.dumps({'status':result['status'],'semantic_phase_count':len(admitted),'native':'NOT_RUN','snapshot_oracle_sensitivity':'NOT_RUN'}))
raise SystemExit(0 if result['status']=='PASS_KNOWN9_SEMANTIC_RED_FRESH_GREEN_SOURCE_ONLY' else 1)
