import ast
import datetime
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import yaml

R = pathlib.Path('/workspace/engineering/pr282')
B = pathlib.Path('/workspace/engineering/pr282-actual618-refresh')
OUT = pathlib.Path('/workspace/engineering/pr282-actual618-independent-source-review')
HEAD = 'e736f846557ed1d603348e97c5eb80060d62e3e2'
TREE = '07b716104ba623df81c00bd83be08dde84dd29f1'
PARENTS = ['c75dfa6969c2c562a59a967e2e674fea6c8af457', '6181b044c75de35386f1ae30e71725398b6a7feb']
OLD = '92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
cache = {}
def sha(data): return hashlib.sha256(data).hexdigest()
def file_sha(p):
    p = pathlib.Path(p)
    key = (str(p), p.stat().st_size, p.stat().st_mtime_ns)
    if key not in cache:
        h = hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda: f.read(1048576), b''): h.update(chunk)
        cache[key] = h.hexdigest()
    return cache[key]
def git(*args): return subprocess.check_output(['git', '--no-optional-locks', '-C', str(R), *args])
def load(p): return json.loads(pathlib.Path(p).read_bytes())
def binding(row):
    p = pathlib.Path(row['path'])
    assert p.stat().st_size == row['bytes'], 'binding size'
    assert file_sha(p) == row['sha256'], 'binding digest'
    return row
def leaves(ref):
    result = {}
    for row in git('ls-tree', '-r', '-z', ref).split(b'\0'):
        if row:
            meta, path = row.split(b'\t', 1)
            result[path.decode()] = meta.decode().split()
    return result
def blob(ref, path): return git('show', ref + ':' + path)
def ast_dump(data): return ast.dump(ast.parse(data), include_attributes=False)

receipt = binding({'path': str(B/'frozen-source-receipt.json'), 'bytes': 67074, 'sha256': '78f41d01e5a1bdfe4df059f7cc797c7a8a80a840b9d12b8d95fad6a98816db71'})
d = load(receipt['path'])
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert git('rev-parse', 'HEAD^{tree}').decode().strip() == TREE
assert git('show', '-s', '--format=%P', HEAD).decode().split() == PARENTS
assert git('status', '--porcelain') == b''
assert git('branch', '--show-current').decode().strip() == 'feat/canvas-template-20261010'
assert d['head'] == HEAD and d['tree'] == TREE and d['ordered_parents'] == PARENTS
assert len(d['evidence_files']) == 50
for row in d['evidence_files'].values(): binding(row)
u = load(binding(d['complete_union'])['path'])
assert len(u['prior_refs']) == 43
for row in u['prior_refs']: binding(row)
for key in ('strict_original_Canvas39_gate', 'current_RCC9_sample', 'light_checkpoint', 'prefull', 'prior_original776_source', 'prior_original776_indGO', 'accepted_actual618_indGO'): binding(d[key])
for pair in d['retained_owned_artifacts'].values():
    if isinstance(pair, dict):
        if 'path' in pair: binding(pair)
        else:
            for row in pair.values(): binding(row)

C, A, T, N = map(leaves, (HEAD, *PARENTS, OLD))
assert C == u['typed_union'] and len(C) == 1433
assert set(C) == set(A) | set(T)
novel = sorted(p for p in C if C[p] not in (A.get(p), T.get(p)))
assert novel == u['novel_combined_paths'] == ['docs/skills/repository-operations.md']
base = git('merge-base', *PARENTS).decode().strip()
ancestor = leaves(base)
conflicts = []
for p, row in C.items():
    a, t, prev = A.get(p), T.get(p), ancestor.get(p)
    if a == t: expected = a
    elif a == prev: expected = t
    elif t == prev: expected = a
    else:
        conflicts.append(p)
        continue
    assert row == expected, 'ordinary leaf union'
assert set(conflicts) <= {'docs/skills/repository-operations.md'}

ids = sorted(set(v[2] for v in C.values()))
raw = git('cat-file', '--batch') if not ids else subprocess.check_output(['git', '--no-optional-locks', '-C', str(R), 'cat-file', '--batch'], input=('\n'.join(ids)+'\n').encode())
bodies = {}; at = 0
for ident in ids:
    end = raw.index(b'\n', at); h, kind, size = raw[at:end].decode().split(); size = int(size)
    assert h == ident and kind == 'blob'
    bodies[ident] = raw[end+1:end+1+size]
    at = end+size+2
assert at == len(raw)
pre = load(B/'committed-union-pre-full.json')
assert pre['head'] == HEAD and pre['tree'] == TREE and pre['parents'] == PARENTS
observed = {}; executables = 0; symlinks = 0
for p, (mode, kind, ident) in C.items():
    path = R/p; st = path.lstat(); data = bodies[ident]
    assert kind == 'blob'
    if mode == '120000':
        assert stat.S_ISLNK(st.st_mode) and os.fsencode(os.readlink(path)) == data
        symlinks += 1
    else:
        assert stat.S_ISREG(st.st_mode) and path.read_bytes() == data
        assert bool(st.st_mode & 0o111) == bool(st.st_mode & stat.S_IXUSR) == (mode == '100755')
        assert pre['pre_full_executable_bits'][p] == (mode == '100755')
        executables += mode == '100755'
    observed[p] = sha(data)
assert observed == pre['pre_full_sha256'] == u['before_commit_current_sha256']

gen = '.github/workflows/_gen_workflows.py'
assert C[gen] == A[gen]
assert ast_dump(blob(HEAD, gen)) == ast_dump(blob(PARENTS[0], gen))
assert len(ast.parse(blob(HEAD, gen)).body) == 32
original = '9c8f1c95caeded6495877280ed1465fd9850b254'
def method(ref): return next(n for n in ast.walk(ast.parse(blob(ref, gen))) if isinstance(n, ast.FunctionDef) and n.name == 'published_canvas_acceptance')
assert ast.dump(method(HEAD), include_attributes=False) == ast.dump(method(original), include_attributes=False)
workflow = '.github/workflows/actions_runtime_tests.yml'
def canvas_step(ref):
    return next(s for s in yaml.safe_load(blob(ref, workflow))['jobs']['build']['steps'] if s.get('name') == 'Verify Canvas published-Core Runtime and browser acceptance')
step = canvas_step(HEAD)
assert step == canvas_step(original)
script = step['run']; program = script.split("<<'PY'\n", 1)[1].rsplit('\nPY',1)[0]
validator = ast.parse(program)
checks = next(n.value for n in ast.walk(validator) if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id == 'checks' for t in n.targets))
assert isinstance(checks, ast.Tuple) and len(checks.elts) == 39
names = [ast.literal_eval(n.elts[0]) for n in checks.elts]
assert len(set(names)) == 39
owned = list(u['original_Canvas3_exact9c'])
O = leaves(original)
assert len(owned) == 3
for p in owned: assert C[p] == A[p] == O[p] == u['original_Canvas3_exact9c'][p]
helper = R/'action_server/tests/action_server_tests/mcp/test_canvas_query_template.py'
assert file_sha(helper) == 'edc7ccfb85bd20bc89775f73ee45039bcf4c501fe6dae9a5ebd81a80e16eda4e'
nine = load(d['current_RCC9_sample']['path'])['nine_sample']; D = leaves('d642a3ac24f8da85101538bdfdf59b509fd74bfb')
assert len(nine) == 9
for row in nine.values():
    p = row['path']; assert C[p] == T[p] == D[p] == row['mode_blob']; assert observed[p] == row['sha256']
deps = {f'{p}/{name}' for p in ('action_server', 'actions', 'actions-http-helper') for name in ('pyproject.toml','poetry.lock')}
producer = lambda entries: {p:v for p,v in entries.items() if p.startswith(('action_server/src/', 'actions/src/', 'actions-http-helper/src/')) or p in deps}
current, historical = producer(C), producer(N)
changed = sorted(p for p in historical if current.get(p) != historical[p]); added = sorted(set(current)-set(historical))
assert len(current) == 275 and len(historical) == 268 and len(changed) == 9 and len(added) == 7
assert current == d['current_producer']['typed_inventory']
assert set(changed) == set(d['current_producer']['changed']) and added == d['current_producer']['added']
assert not set(historical)-set(current)
for p,row in d['five_selected_tests_separate'].items(): assert C[p] == A[p] == T[p] == N[p] == row
assert len(d['five_selected_tests_separate']) == 5

prep = load(B/'own-Bootstrap-reuse-inputs-and-origins.json'); postprep = load(B/'prepared30-origin5-ownedRCC-postfull-retention.json')
assert prep['measured_inputs'] == len(prep['inputs_exact_prepared_git_bytes_sha256']) == 30
assert prep['inputs_exact_prepared_git_bytes_sha256'] == postprep['measured30_prepared_input_sha256']
for p,digest in prep['inputs_exact_prepared_git_bytes_sha256'].items(): assert observed[p] == sha(blob(prep['prepared_source'],p)) == digest
assert file_sha(prep['original_bootstrap_log']) == prep['original_bootstrap_log_sha256']
assert 'actual main robot run" was SUCCESS' in pathlib.Path(prep['original_bootstrap_log']).read_text()
assert prep['own5venvs_current_config_and_python'] == postprep['own5config_and_python']
assert len(prep['own5actual_prefix_and_source_origin_assertions']) == 5
for package,row in prep['own5venvs_current_config_and_python'].items():
    prefix = R/package/'.venv'
    assert file_sha(prefix/'pyvenv.cfg') == row['config_sha256']
    assert str((prefix/'bin/python').resolve()) == row['python_resolved']
    origin = load(B/('origin-'+package+'.json'))
    assert origin in prep['own5actual_prefix_and_source_origin_assertions']
    assert pathlib.Path(origin['prefix']).resolve() == prefix.resolve()
    assert pathlib.Path(origin['python']) == prefix/'bin/python'
    assert pathlib.Path(origin['origin']).resolve().is_relative_to((R/package/'src').resolve())
owned_rcc = load(B/'owned-pinned-RCC-retention.json'); rcc = pathlib.Path(owned_rcc['owned_ignored_RCC'])
assert file_sha(rcc) == owned_rcc['sha256'] == '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
assert stat.S_IMODE(rcc.stat().st_mode) == 0o711
assert git('check-ignore', str(rcc)).strip()

roundtrip = load(B/'generator-roundtrip.json')
assert roundtrip['before'] == roundtrip['after'] and len(roundtrip['before']) == 26
yaml_paths = sorted(p for p in C if p.endswith(('.yaml','.yml')))
assert len(yaml_paths) == roundtrip['all_tracked_yaml_count'] == 30
for p in yaml_paths: yaml.safe_load(bodies[C[p][2]])
for p,digest in roundtrip['before'].items(): assert observed[p] == digest
assert len(roundtrip['generated_workflows']) == 8

log_counts = {}
for name in ['Doctor.log','Toolkit.log','Canvas-scoped.log','Canvas-gateway-contract.log','current-RCC-and-static.log','generator-roundtrip.log','full-configured-source.log']:
    text = (B/name).read_text()
    assert 'actual main robot run" was SUCCESS' in text, name
    counts = re.findall(r'(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) deselected)?(?:, (\d+) warnings)? in ([\d.]+)s', text)
    log_counts[name] = counts
full = (B/'full-configured-source.log').read_text()
assert '1233 passed, 12 skipped, 15 warnings in 133.96s' in full and '2 workers' in full
static = (B/'current-RCC-and-static.log').read_text()
assert '348 source files' in static
assert '112 passed, 1 skipped, 3 deselected' in static
assert '179 passed' in (B/'Toolkit.log').read_text()
assert '75 passed' in (B/'Canvas-scoped.log').read_text()
assert '4 passed, 24 deselected' in (B/'Canvas-scoped.log').read_text()
diagnostic = load(B/'initial-freeze-parser-schema-diagnostic.json')
assert diagnostic['gates_repeated'] is False and diagnostic['source_mutation'] is False
assert file_sha(B/'initial-freeze-parser-before-log-schema-correction.py') == diagnostic['original_parser_sha256']
assert file_sha(B/'current-RCC-and-static.log') == diagnostic['original_configured_log_sha256']

docs = ['docs/skills/repository-operations.md','docs/skills/provenance-observability.md']
patch = git('diff', PARENTS[0], HEAD, '--', 'docs/skills')
assert patch == (B/'exact-both-parent-canonical-import.patch').read_bytes()
assert len(patch) == 13633 and sha(patch) == '436b14701d385f7b652ad16496a32b64a965caa930970b3950b993e64f0c2b9e'
for p in docs:
    current_text = bodies[C[p][2]].decode()
    for parent in PARENTS:
        additions = [line[1:] for line in git('diff','--unified=0',base,parent,'--',p).decode().splitlines() if line.startswith('+') and not line.startswith('+++') and line[1:].strip()]
        assert all(line in current_text for line in additions), 'parent canonical lesson lost'
adds = sum(line.startswith(b'+') and not line.startswith(b'+++') for line in patch.splitlines())
removes = sum(line.startswith(b'-') and not line.startswith(b'---') for line in patch.splitlines())

assert git('rev-parse','HEAD').decode().strip() == HEAD and git('status','--porcelain') == b''
proof = {'status':'PASS_READ_ONLY_EXACT_CURRENT_SOURCE_AND_RECORDED_GATES', 'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'receipt':receipt,
    'source':{'head':HEAD,'tree':TREE,'ordered_parents':PARENTS,'branch':'feat/canvas-template-20261010','clean':True},
    'complete_union':{'typed_leaves':len(C),'parent_counts':[len(A),len(T)],'no_deletions':True,'novel_combined_paths':novel,'three_way_conflicts':conflicts,'Git_FS_prepost_body_exec_bits_exact':True,'executable_files':executables,'symlinks':symlinks,'typed_sha256':sha(json.dumps(C,sort_keys=True,separators=(',',':')).encode())},
    'references':{'final':50,'historical':43,'all_hash_size_exact':True},
    'Canvas':{'whole39_names':names,'method_AST_and_step_equal_original9c':True,'three_original_tests_staging_equal_original9c':True,'generator_body_AST_equal_c75':True,'no_fresh_2_plus_8_claim':True,'helper_edc7_exact':True},
    'RCC':{'nine_sample_exact_d642_and_618':True,'scope':'Nine source sample; not whole producer/actual/full134'},
    'producer':{'historical':268,'current':275,'matching':259,'changed':changed,'added':added,'five_selected_separate_exact':True,'native':'UNQUALIFIED'},
    'prepared':{'inputs':30,'old_source_current_bytes_exact':True,'origins':5,'own_configs_prefixes_python_origins_exact':True,'ignored_RCC_sha256':owned_rcc['sha256'],'mode':'0711','new_installer':False},
    'recorded_gates':d['gates'],'observed_log_counts':log_counts,'YAML':{'tracked':30,'workflow_plus_dependabot':26,'generated':8,'original_before_after_current_exact':True},
    'initial_parser_failure':{'original_immutable_retained':True,'scope':'Receipt log-schema parser failure; unchanged original successful gates and no source gate rerun'},
    'documentation':{'canonical_files':docs,'exact_accepted_parent_patch_sha256':sha(patch),'bytes':len(patch),'additions':adds,'removals':removes,'both_parent_added_lessons_retained':True,'no_cosmetic_child':True},
    'not_run':['Tests/gates/installer/native/browser/provider/download','Git mutation/push/merge'], 'upstream_disposition':'none'}
dest = OUT/'independent-exact-source-and-evidence-proof.json'
assert not dest.exists(); dest.write_text(json.dumps(proof,indent=2)+'\n');dest.chmod(0o444)
print(json.dumps({'status':proof['status'],'proof_bytes':dest.stat().st_size,'proof_sha256':file_sha(dest),'source_leaves':len(C),'final_and_prior_refs':93,'canonical_added_removed':[adds,removes]}))
