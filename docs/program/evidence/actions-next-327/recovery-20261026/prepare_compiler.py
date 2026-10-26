"""Fresh a53 claimed-Robot compiler; execute only under host pidfd supervisor."""
import hashlib, importlib.metadata, json, os, pathlib, platform, re, shutil, subprocess, sys, sysconfig, time, zipfile
from urllib.parse import urlsplit
P=pathlib.Path
BASE=P('/workspace/327-artifacts/a53')
ROOT=P('/workspace/327-probes/a53-claimed/compiler')
SOURCE='aca51868d14e916c8034c69309e222100d5d50f3'
HASHES={'actions-runtime':'2013b8fc54163d10c3c0edddb3bb1ea8e59cb95b88f9a05a2d810110cdd0d117','actions-core':'42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f','actions-work-items':'72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sys.flags.isolated and sys.version_info[:2]==(3,12) and sys.platform=='linux' and platform.machine()=='x86_64'
assert P(sys.prefix).resolve()==(BASE/'consumer').resolve()
assert (BASE/'source-sha.txt').read_text().strip()==SOURCE
import actions.server
assert P(actions.server.__file__).resolve().is_relative_to(BASE/'consumer')
assert importlib.metadata.version('actions-runtime')=='1.1.0a53'
assert importlib.metadata.version('actions-core')=='1.1.0a8'
site=P(sysconfig.get_paths()['purelib']); wheels={};counts={}
for name,digest in HASHES.items():
    found=list((BASE/'wheels').rglob(name.replace('-','_')+'-*.whl'));assert len(found)==1
    wheel=found[0];assert sha(wheel)==digest;wheels[name]=wheel;count=0
    with zipfile.ZipFile(wheel) as z:
        for n in z.namelist():
            if n.endswith('/') or '.dist-info/' in n or '.data/' in n:continue
            assert (site/n).read_bytes()==z.read(n),n;count+=1
    counts[name]=count
assert counts=={'actions-runtime':339,'actions-core':87,'actions-work-items':26},counts
status={'status':'VERIFIED_PREPARATION_START','source':SOURCE,'installed_payload_members':counts,'wheels':HASHES,'compiler_script_sha256':sha(P(__file__))}
P(__file__).with_name('compiler-start.json').write_text(json.dumps(status,indent=2))
rcc=P(actions.server.__file__).parent/'bin/rcc-18.19.3'
assert sha(rcc)=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
assert not ROOT.exists();assert shutil.disk_usage(ROOT.parent).free>10*1024**3
ROOT.mkdir(mode=0o700)
for child in ('robocorp/wheels','actions-home','robots-home','tmp'):(ROOT/child).mkdir(parents=True,mode=0o700)
package=b'name: claimed-robot-a53\ndescription: Owned claimed Robot cancellation qualification\ndependencies:\n  conda-forge:\n    - python=3.12\n  pypi:\n    - actions-core=1.1.0a8\n    - actions-work-items=0.5.0a2\n    - robotframework=7.4.2\n'
(ROOT/'package.yaml').write_bytes(package)
for name in ('actions-core','actions-work-items'):shutil.copyfile(wheels[name],ROOT/'robocorp/wheels'/wheels[name].name)
verifier=P(__file__).with_name('verify_compiler.py');shutil.copyfile(verifier,ROOT/'verify_compiler.py')
env={'HOME':os.environ['HOME'],'PATH':'/usr/local/bin:/usr/sbin:/sbin:/usr/bin:/bin','ROBOCORP_HOME':str(ROOT/'robocorp'),'ACTIONS_HOME':str(ROOT/'actions-home'),'ROBOTS_HOME':str(ROOT/'robots-home'),'PIP_FIND_LINKS':str(ROOT/'robocorp/wheels'),'TMPDIR':str(ROOT/'tmp'),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8'}
for k,v in os.environ.items():
    if k.lower() in ('http_proxy','https_proxy','all_proxy','no_proxy') or k in ('SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE'):
        if k.lower().endswith('_proxy') and k.lower()!='no_proxy':assert not urlsplit(v).username and not urlsplit(v).password
        env[k]=v
# No inner subreaper: the host supervisor adopts/reaps children throughout execution.
def run(command,label,seconds):
    path=ROOT/(label+'.log')
    with path.open('wb') as stream:
        proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+seconds
        while proc.poll() is None:
            assert time.monotonic()<deadline,label+' deadline'
            assert path.stat().st_size<12*1024**2,'log budget'
            assert shutil.disk_usage(ROOT).free>1024**3,'disk floor'
            time.sleep(.2)
        assert proc.returncode==0,label+' failed'
    return path.read_bytes()
from actions.server.deployments.package_revision_compiler import PreparedRccEnvironment,RccBuildIdentity,load_prepared_rcc_environment
from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor,build_exec_command,read_receipt
assert run([str(rcc),'--version'],'version',30).splitlines()[0].strip()==b'v18.19.3'
raw=run([str(rcc),'env','publish','--environment',str(ROOT/'package.yaml'),'--json','--provider','local'],'publish',650)
rows=[]
for line in raw.splitlines():
    try:value=json.loads(line)
    except (ValueError,UnicodeError):continue
    if isinstance(value,dict) and {'specificationDigest','artifactDigest'}<=value.keys():rows.append(value)
assert len(rows)==1
row=rows[0]
for k in ('specificationDigest','artifactDigest'):assert re.fullmatch(r'sha256:[0-9a-f]{64}',row[k])
yaml_digest='sha256:'+sha(ROOT/'package.yaml')
prepared=PreparedRccEnvironment(ROOT/'robocorp',yaml_digest,RccBuildIdentity(row['specificationDigest'],row['artifactDigest']))
(ROOT/'prepared.json').write_bytes(prepared.to_receipt_bytes());assert load_prepared_rcc_environment(ROOT/'prepared.json')==prepared
descriptor=RccRuntimeDescriptor(artifact_digest=row['artifactDigest'],source_generation='a53-claimed-compiler-proof',source_hash=yaml_digest,environment_fingerprint=row['specificationDigest'].removeprefix('sha256:'),preparation_class='warm-reuse',provider_reference='local')
command=build_exec_command(rcc,descriptor,['python','-I',str(ROOT/'verify_compiler.py'),str(ROOT)],receipt_file=ROOT/'core-exec-qualified.json',local_trust_carrier=ROOT/'robocorp/artifacts/v1/trust')
command.insert(command.index('--'),'--no-build');env['RCC_NO_BUILD']='1'
run(command,'proof',180);read_receipt(ROOT/'core-exec-qualified.json',row['artifactDigest'])
proof=json.loads((ROOT/'core-proof.json').read_text());assert proof['status']=='PASS'
status.update(status='PASS',package_yaml_digest=yaml_digest,artifact_digest=row['artifactDigest'],specification_digest=row['specificationDigest'],prepared_receipt=str(ROOT/'prepared.json'),prepared_receipt_sha256=sha(ROOT/'prepared.json'),core_proof=str(ROOT/'core-proof.json'),core_proof_sha256=sha(ROOT/'core-proof.json'))
(ROOT/'compiler-receipt.json').write_text(json.dumps(status,indent=2));print(json.dumps(status,indent=2))
