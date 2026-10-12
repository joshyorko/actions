from pathlib import Path
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

ROOT=Path('/workspace/engineering/campaign-checkpoint')
OUT=Path('/workspace/engineering/campaign-checkpoint-independent-review')
REL='docs/program/evidence/wave11/current-engineering-20261011'
DEST=ROOT/REL

def binding(p):
    raw=p.read_bytes()
    return {'path':str(p),'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])

old=json.loads(git('show','HEAD:'+REL+'/manifest.json'))
manifest=json.loads((DEST/'manifest.json').read_text())
new={k:v for k,v in manifest.items() if k not in old}
assert (len(old),len(new),len(manifest))==(50,38,88)
assert all(old[k]==manifest[k] for k in old)
all_rows=[]
for name,m in manifest.items():
    p=DEST/name
    assert p.name==name
    actual=binding(p)
    assert actual['size']==m['bytes'] and actual['sha256']==m['sha256']
    if name in new:
        assert p.read_bytes()==Path(m['source']).read_bytes()
    all_rows.append({'name':name,'new':name in new,'source':m['source'],'bytes':m['bytes'],'sha256':m['sha256']})
patterns=[r'gh[pousr]_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{20,}',r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY',r'AKIA[A-Z0-9]{16}',r'(?i)(?:sig|x-amz-signature|x-goog-signature|access_token)=[^\s"\']{8,}']
for name in new:
    text=(DEST/name).read_text()
    assert not any(re.search(p,text) for p in patterns),name
assert 'job114376917743-original-decoded.log' not in new
assert all('original-decoded.log' not in n and 'windows-job' not in n for n in new)
log_names=[n for n in new if n.endswith('.log')]
assert log_names==['pr302-current-actual-acceptance-summary.log']
assert (DEST/log_names[0]).stat().st_size==686
assert (DEST/log_names[0]).read_text().startswith('Sanitized RCC provider rollback acceptance summary\n')
assert len(list(ET.parse(DEST/'pr302-current-actual-rcc-provider-rollback-junit.xml').getroot().iter('testcase')))==3
assert all(not (e.text and e.text.strip()) for e in ET.parse(DEST/'pr302-current-actual-rcc-provider-rollback-junit.xml').getroot().iter())
urls=[]
def check_urls(x,path=''):
    if isinstance(x,dict):
        for k,v in x.items():check_urls(v,path+'/'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x):check_urls(v,path+'/'+str(i))
    elif isinstance(x,str) and '://' in x:
        u=urlsplit(x)
        assert u.scheme=='http' and u.hostname=='127.0.0.1'
        assert not u.username and not u.password and not u.query and not u.fragment
        urls.append({'field':path,'scope':'owned loopback HTTP; no credentials/query/fragment'})
for name in ['pr302-current-actual-lifecycle-receipt.json','pr302-current-actual-published-details-receipt.json']:
    check_urls(json.loads((DEST/name).read_text()),name)
proposal305=json.loads((DEST/'pr305-bounded-source-and-command-proposal.json').read_text())
assert not proposal305['actual_run_authorized'] and not proposal305['actual_run_executed'] and not proposal305['execution_ready']
assert proposal305['phase']=='READ_ONLY_SOURCE_GAP_AND_COMMAND_PROPOSAL'
assert set(proposal305['planned_command']['env'])=={'ACTIONS_CANVAS_RUNTIME_ACCEPTANCE','ACTIONS_HOME','CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH','DEBUG','MKL_NUM_THREADS','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','PYTEST_XDIST_AUTO_NUM_WORKERS','SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE','TMPDIR/TMP/TEMP','UV_CACHE_DIR','proposed_published_core_mode'}
operations=(ROOT/'docs/skills/repository-operations.md').read_text()
source307=Path('/workspace/engineering/pr307/docs/skills/repository-operations.md').read_text()
block=source307[source307.index('`inv build-oauth2-config` delegates'):source307.index('The source migration PR contains',source307.index('`inv build-oauth2-config` delegates'))]
assert block in operations
for required in ['pre-guard task ignored acquisition exit','all six failures were in','only two nodes had80/88-second observations','five explicit incomplete20-second','sixth failure\'s absent note is not a cleanup pass','No raw Progress was retained there','90-second readiness/20-second cleanup']:
    assert required in operations
readme=(DEST/'README.md').read_text()
for required in ['The earlier pending entries above are retained history.','run38110371338/job114384488800','Complete' if False else 'Full\ncurrent CI remains pending','currentd75 CI is separate','full-manifest authority design is deferred','preparation, not actual\nexecution']:
    assert required in readme
workitems=(ROOT/'docs/skills/work-items.md').read_text()
for required in ['38107100997','65c0cb83','782ff78f','workflow head `f506a04e`','did not retain native JUnit XML','do not establish the actual browser file','Neither receipt proves a public registry installation','Runtime cleanup in each gate was forced','last attempted browser stage only','full issue #208 acceptance']:
    assert required in workitems
for name in ['pr310-platform-guide-proposed.patch','pr310-platform-gate-clarification.patch']:
    patch=(DEST/name).read_text()
    additions=[l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++')]
    meaningful=[l.strip() for l in additions if l.strip()]
    assert all(l in workitems for l in meaningful),name
authored=['docs/skills/repository-operations.md','docs/skills/work-items.md',REL+'/README.md',REL+'/manifest.json']
subprocess.check_call(['git','-C',str(ROOT),'diff','--check','--',*authored])
raw_patch_spaces=[]
for name in new:
    if name.endswith('.patch'):
        for n,line in enumerate((DEST/name).read_text().splitlines(),1):
            if line.endswith((' ','\t')):
                raw_patch_spaces.append({'artifact':name,'line':n,'kind':'original immutable unified-patch line retains trailing/context whitespace'})
receipt={
 'verdict':'GO_NORMAL_COMMIT_AND_PUSH_EXACT_REVIEWED_DURABLE_DOCS_AND_RECEIPTS_ONLY',
 'scope':'read-only safety, copied evidence-byte integrity, and canonical guidance scope; no new actual/native acceptance or source implementation',
 'reviewed_parent':git('rev-parse','HEAD').decode().strip(),
 'new_exact_original_copies':38,'preserved_old_manifest_records':50,'verified_total_manifest_entries':88,
 'all_copied_bindings':all_rows,
 'authored_document_bindings':[binding(ROOT/p) for p in authored],
 'safety':{'token_private_key_signed_query_scan':'PASS; no matches in38 new files','original_full311_raw_job_log':'excluded; remains outside repository','new_log_exception':'only686-byte sanitized302 acceptance summary','new_junit':'3cases; no raw system output text','provider_urls':urls,'private_provider_or_oauth_bodies':'absent; identity digests/inventories and fixed structural categories only','pr305_planned_environment':'fixed owned paths/nonsecret thread limits and explicit unavailable mode; not process environment capture','311_original_raw_json_and_authrecords':'unchanged previously independently allowlisted8JSON+4safe identities'},
 'canonical_dispositions':{'operations307':'exact accepted frozen87e412 guard/gateway block adapted; integration/hosted authority/provider/old recovery HOLD retained','operations311':'current6 first-start failures vs2 instrumented; active CPU/IO no internal phase/root-cause; host-only fields no descendant cleanup;5 incomplete notes and absent6th note notcleanupGO;90/20 retained','declared_job_inventory':'exact revision/matrix/filter/needs inventory; PR validation and expected tag-only skip distinguished; no missing late job waived','workitems310':'both exact original Mac/Windows canonical proposals integrated;65c/f506 historical tuple separate fromLinuxf506/92498/current union;candidateCore/public distinction,missingJUnit/browseridentity,forcedcleanup/missing208cells retained','accepted_workitems_source_guidance':'existing PEP610Windows/provenanceTAR/wrapperinput/EOL/typecheck/replay guidance retained from accepted engineering work; documentation only','readme':'earlier pending rows expressly historical;302exact3case/publicscope/currentCI dependency,282fixed diagnostic-only strict39 unchanged,307source-onlyGO,305preparationonly andno publication/issueclosure retained'},
 'whitespace':{'authored_guides_README_manifest_diffcheck':'PASS','raw_proposed_patches':'immutable exact copies preserved, never normalized; no blanket evidence diffcheck PASS','new_patch_lines_retaining_whitespace':raw_patch_spaces,'earlier_patch_context_space':'prior originaloauth patch line34 unchanged and hashpreserved'},
 'remaining_uncertainty':['Current exact-head complete merge gates are separate from this durable evidence checkpoint.','No approved OAuth source pair/revision/provider qualification, original private metadata proof, or Runtime publication waiver.','No whole#208, coldWindowsRCC root cause, complete original311 descendant cleanup, or actual305 clean consumer execution.','Immutable raw receipts retain original identities and limits; later source unions cannot inherit earlier producer or execution equivalence.'],
 'documentation_improvement':{'canonical_files':authored[:2],'exact_delta':'reviewed root working-tree doc diff bound by authored hashes; adapted already accepted proposals','evidence':'38 exact original copies/88 verified manifest records and accepted scoped independent reviews','stale_ambiguity':'earlier pending history/current gates, preguard acquisition bug/currentguard, current6/historical2 census, previousmark timing/observer timing, oldproducer/currentunion all distinguished','remaining_uncertainty':'acceptance graph gates above','upstream':'none'},
 'mutation':'independent receipt outside repository only; no repo mutation or tests/native runs by reviewer',
}
p=OUT/'current-actual-evidence-batch-prepush-review.json'
p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(binding(p)))
