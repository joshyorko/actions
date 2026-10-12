"""PREPARATION ONLY. Root release and independent review required before use.

This module never invokes GitHub, imports a wheel, extracts an archive, builds,
installs or publishes. The connector is invoked once by the separately bound JS.
"""
import argparse,base64,hashlib,json,os,re,stat,sys,time,traceback,urllib.parse,urllib.request,zipfile
from pathlib import Path

O=Path(__file__).resolve().parent
DEST=Path('/tmp/actions-pr221-e2-aggregate-11708952448-one-owned')
ARTIFACT=11708952448
EXPECTED_BYTES=80745614
EXPECTED_SHA='e16a414fefc1778ba49d09c466fd9d8054cfbf952e7766ee5cc6558f871f4def'
NAME='actions-runtime-dist-11708952448-original.zip'
SOURCE='e2c81adce7858d5a952991ba9a8b7f72e902038a'
POLICY=O/'frozen-current-e2-publisher-outer-archive-policy.json'
MODULE=Path(__file__).resolve()

def require(ok,code):
    if not ok:raise ValueError(code)

def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def unique_json(raw):
    def pairs(items):
        d={}
        for k,v in items:
            require(k not in d,'DUPLICATE_JSON_KEY');d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs)

def bound(row):
    p=Path(row['path']);s=p.lstat()
    require(stat.S_ISREG(s.st_mode) and not p.is_symlink(),'BOUND_FILE_TYPE')
    require(s.st_size==row['bytes'] and digest(p)==row['sha256'],'BOUND_FILE_BYTES')
    require(oct(stat.S_IMODE(s.st_mode))==row['mode'],'BOUND_FILE_MODE')

def exclusive(p,b):
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())

def root_admission(args):
    require(sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE'),'OPTIMIZATION_FORBIDDEN')
    p=Path(args.release);require(not p.is_symlink() and digest(p)==args.release_sha256,'ROOT_RELEASE_HASH')
    r=unique_json(p.read_bytes())
    require(r['schema']==1 and type(r['schema']) is int,'ROOT_RELEASE_SCHEMA')
    require(r['status']=='ROOT_RELEASE_ONE_CURRENT_E2_ORIGINAL_AGGREGATE_CONNECTOR_AND_TRANSFER','ROOT_RELEASE_STATUS')
    require(r['source']==SOURCE and r['artifact_id']==ARTIFACT and type(r['artifact_id']) is int,'ROOT_RELEASE_SUBJECT')
    require(r['aggregate_API_bytes']==EXPECTED_BYTES and r['aggregate_API_sha256']==EXPECTED_SHA,'ROOT_RELEASE_API_BYTES')
    require(r['executor_sha256']==digest(MODULE) and r['publisher_policy_sha256']==digest(POLICY),'ROOT_RELEASE_EXECUTOR_POLICY')
    require(r['serialized_no_other_heavy_or_installer'] is True,'ROOT_RELEASE_SERIALIZATION')
    require(r['data_only_no_package_native_consumer_or_publication'] is True,'ROOT_RELEASE_SCOPE')
    require(r['original_checkout_UNKNOWN_retained'] is True,'ROOT_RELEASE_CHECKOUT_LIMIT')
    for key in ['proposal','independent_preexecution_GO']:
        bound(r[key])
    require(type(r['independent_preexecution_GO']) is dict,'ROOT_REVIEW_REQUIRED')
    for row in r['immutable_original_preparations_and_metadata']:bound(row)
    return r

def own_dir():
    s=DEST.lstat();require(stat.S_ISDIR(s.st_mode) and not DEST.is_symlink(),'OWNED_DIRECTORY_TYPE')
    require(s.st_uid==os.getuid() and s.st_gid==os.getgid() and stat.S_IMODE(s.st_mode)==0o700,'OWNED_DIRECTORY_MODE_OWNER')

def begin(args):
    root_admission(args)
    require(os.statvfs('/tmp').f_bavail*os.statvfs('/tmp').f_frsize>=536870912,'TMP_CAPACITY_FLOOR')
    require(os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize>=1288490189,'WORKSPACE_CAPACITY_FLOOR')
    require(not DEST.exists() and not DEST.is_symlink(),'ATTEMPT_ALREADY_EXISTS_NO_RETRY')
    DEST.mkdir(mode=0o700);own_dir()
    exclusive(DEST/'original-one-attempt-intent.json',json.dumps(dict(status='INTENT_BEFORE_CONNECTOR_CALL',artifact_id=ARTIFACT,source=SOURCE,connector_call_limit=1,transfer_limit=1,no_retry=True),indent=2).encode()+b'\n')
    print(json.dumps(dict(repo_full_name='joshyorko/actions',artifact_id=ARTIFACT,file_name=NAME)))

def retain(args):
    root_admission(args);own_dir()
    raw=base64.b64decode(args.serialized_tool_result_base64,validate=True)
    require(len(raw)<=49152,'TOOL_RESULT_SERIALIZATION_CEILING')
    # Original observed logical MCP result serialization, never claimed wire bytes.
    exclusive(DEST/'original-connector-tool-result.generated.json',raw)

def resolve(raw):
    d=unique_json(raw);require(d.get('isError') is not True,'CONNECTOR_IS_ERROR')
    s=d['structuredContent'];f=s['file_uri'];n=s['structuredContent']
    require(type(f) is dict and type(n['file_uri']) is dict,'FILE_SERVICE_MAPPING_REQUIRED')
    require(type(s['artifact_id']) is int and s['artifact_id']==n['artifact_id']==ARTIFACT,'REFERENCE_ARTIFACT_ID')
    require(s['file_name']==n['file_name']==f['file_name']==NAME,'REFERENCE_FILE_NAME')
    require(s['mime_type']==n['mime_type']==f['mime_type']=='application/zip','REFERENCE_MIME')
    require(f==n['file_uri'],'REFERENCE_NESTED_MAPPING')
    require(f['file_id']==n['file_id'] and type(f['file_id']) is str and bool(f['file_id']),'REFERENCE_FILE_ID')
    require(f['download_url']==n['download_url'],'REFERENCE_DOWNLOAD_IDENTITY')
    u=urllib.parse.urlsplit(f['download_url'])
    require(u.scheme=='https' and bool(u.hostname) and not u.username and not u.password and not u.fragment,'REFERENCE_HTTPS_NO_USERINFO')
    require(not f['file_id'].startswith('file_') or not str(f['download_url']).startswith('sediment:'),'FILE_SERVICE_NOT_SEDIMENT')
    return f['download_url']

class HTTPSFiniteRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections=3
    max_repeats=1
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        require(urllib.parse.urlsplit(newurl).scheme=='https','NON_HTTPS_REDIRECT')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def filenames(names,policy):
    artifacts=[n for n in names if n!=policy['manifest_name']]
    require(len(artifacts)==7,'DISTRIBUTION_COUNT')
    sdist=f"{policy['artifact_prefix']}-{policy['distribution_version']}.tar.gz"
    require(artifacts.count(sdist)==1,'EXACT_SDIST_NAME')
    slots=[];prefix=f"{policy['artifact_prefix']}-{policy['distribution_version']}-"
    for name in artifacts:
        if name==sdist:continue
        require(name.startswith(prefix) and name.endswith('.whl'),'EXACT_WHEEL_PREFIX')
        tags=name[len(prefix):-4].split('-');require(len(tags)==3,'WHEEL_NO_BUILD_TAG')
        py,abi,platform=tags;ps=platform.split('.')
        require(len(ps)==len(set(ps)) and len(py.split('.'))==1 and len(abi.split('.'))==1,'DUPLICATE_OR_UNAPPROVED_TAG')
        found=[i for i,s in enumerate(policy['wheel_slots']) if py==s['python'] and abi==s['abi'] and set(ps)==set(s['exact_platform_tag_set'])]
        require(len(found)==1,'UNAPPROVED_WHEEL_SLOT');slots+=found
    require(len(slots)==6 and len(set(slots))==6,'COMPLETE_SIX_SLOT_MATRIX')
    return sorted(artifacts)

def inspect_zip(path,policy,deadline):
    rows=[];manifest=None;total=0
    with zipfile.ZipFile(path) as z:
        infos=z.infolist();require(len(infos)==8,'OUTER_MEMBER_COUNT')
        names=[i.filename for i in infos]
        require(len(set(names))==8 and len(set(n.casefold() for n in names))==8,'OUTER_DUPLICATE_NAMES')
        for i in infos:
            n=i.filename;mode=i.external_attr>>16;kind=stat.S_IFMT(mode)
            require(i.orig_filename==n and bool(re.fullmatch(r'[A-Za-z0-9_.-]+',n)) and n not in ('.','..'),'UNSAFE_ROOT_NAME')
            require(not i.is_dir() and not(i.flag_bits&1) and kind in (0,stat.S_IFREG),'OUTER_MEMBER_TYPE_OR_ENCRYPTION')
            require(i.file_size<=policy['single_member_byte_ceiling'],'SINGLE_EXPANDED_CEILING')
            total+=i.file_size;require(total<=policy['expanded_byte_ceiling'],'TOTAL_EXPANDED_CEILING')
        arts=filenames(names,policy)
        for i in infos:
            h=hashlib.sha256();actual=0;buf=[]
            with z.open(i) as f:
                while True:
                    require(time.monotonic()<deadline,'CRC_INSPECTION_DEADLINE')
                    b=f.read(65536)
                    if not b:break
                    actual+=len(b);require(actual<=i.file_size,'MEMBER_EXPANDED_OVERFLOW');h.update(b)
                    if i.filename==policy['manifest_name']:
                        require(actual<=16384,'MANIFEST_CEILING');buf.append(b)
            require(actual==i.file_size,'MEMBER_SIZE');rows.append(dict(name=i.filename,bytes=actual,sha256=h.hexdigest(),CRC32=i.CRC,external_mode=oct(i.external_attr>>16),create_system=i.create_system))
            if buf:manifest=b''.join(buf).decode('utf-8')
        require(manifest is not None,'MISSING_MANIFEST');entries={}
        for line in manifest.splitlines():
            require(bool(re.fullmatch(r'[0-9a-f]{64}  [A-Za-z0-9_.-]+',line)),'MANIFEST_LITERAL_FORMAT')
            h,n=line.split('  ',1);require(n not in entries,'MANIFEST_DUPLICATE');entries[n]=h
        require(set(entries)==set(arts) and len(entries)==7,'MANIFEST_EXACT_SEVEN')
        for row in rows:
            if row['name'] in entries:require(entries[row['name']]==row['sha256'],'MANIFEST_BODY_SHA')
    return rows

def transfer(args):
    r=root_admission(args);own_dir()
    exclusive(DEST/'original-one-transfer-intent.json',b'{"status":"INTENT_BEFORE_SINGLE_TRANSFER_NO_RETRY"}\n')
    raw=(DEST/'original-connector-tool-result.generated.json').read_bytes();url=resolve(raw)
    policy=unique_json(POLICY.read_bytes());require(policy['source']==SOURCE,'POLICY_SOURCE')
    target=DEST/NAME;fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    start=time.monotonic();download_deadline=start+120;whole_deadline=start+180;h=hashlib.sha256();count=0
    opener=urllib.request.build_opener(HTTPSFiniteRedirect())
    with os.fdopen(fd,'wb') as out:
        with opener.open(url,timeout=max(.01,download_deadline-time.monotonic())) as response:
            require(response.status==200,'FILE_SERVICE_HTTP_STATUS')
            sock=getattr(getattr(getattr(response,'fp',None),'raw',None),'_sock',None)
            require(sock is not None and callable(getattr(sock,'settimeout',None)),'REMAINING_SOCKET_TIMEOUT_UNAVAILABLE')
            length=response.headers.get('Content-Length')
            if length is not None:require(int(length)==EXPECTED_BYTES,'HTTP_CONTENT_LENGTH')
            while True:
                require(time.monotonic()<download_deadline,'TRANSFER_DEADLINE')
                sock.settimeout(max(.01,download_deadline-time.monotonic()))
                b=response.read(65536)
                if not b:break
                count+=len(b);require(count<=policy['compressed_byte_ceiling'],'COMPRESSED_CEILING');out.write(b);h.update(b)
        out.flush();os.fsync(out.fileno())
    require(count==EXPECTED_BYTES and h.hexdigest()==EXPECTED_SHA,'ORIGINAL_API_ZIP_SIZE_SHA')
    rows=inspect_zip(target,policy,whole_deadline)
    exclusive(DEST/'private-complete-original-eight-member-inventory.json',json.dumps(rows,indent=2).encode()+b'\n')
    for row in r['immutable_original_preparations_and_metadata']:bound(row)
    require(digest(MODULE)==r['executor_sha256'] and digest(POLICY)==r['publisher_policy_sha256'],'POST_EXECUTOR_POLICY')
    final=dict(status='SCOPED_ORIGINAL_E2_AGGREGATE_OUTER_DATA_ADMISSION_ONLY',artifact_id=ARTIFACT,source_API_head=SOURCE,run_id=38157482815,original_builder_checkout='UNKNOWN_NOT_LOG_ACQUIRED',original_ZIP=dict(path=str(target),bytes=count,sha256=h.hexdigest(),mode='0o600'),original_MCP_tool_result='Generated logical result serialization retained privately; wire bytes not claimed',outer_members=8,distribution_files=7,manifest_records=7,complete_outer_CRC_size_SHA_and_manifest=True,actual_inner_RECORD_OAuth_source_content_consumer_native_registry='NOT_INSPECTED_NOT_RUN_NOT_ADMITTED',retry='FORBIDDEN',elapsed_seconds=time.monotonic()-start)
    exclusive(DEST/'OWNERFINAL-original-one-aggregate-data-result.json',json.dumps(final,indent=2).encode()+b'\n')
    print(json.dumps(dict(status=final['status'],artifact_id=ARTIFACT,ZIP_bytes=count,ZIP_sha256=h.hexdigest(),outer_members=8)))

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['begin','retain-tool-result','transfer']);p.add_argument('--release',required=True);p.add_argument('--release-sha256',required=True);p.add_argument('--serialized-tool-result-base64');args=p.parse_args();os.umask(0o077)
    try:
        {'begin':begin,'retain-tool-result':retain,'transfer':transfer}[args.phase](args)
    except BaseException as e:
        if DEST.exists() and not DEST.is_symlink():
            try:
                exclusive(DEST/('original-'+args.phase+'-exception.private.txt'),traceback.format_exc().encode())
                exclusive(DEST/('safe-'+args.phase+'-failure.json'),json.dumps(dict(status='FAIL_OR_HOLD_ORIGINAL_PARTIAL_RETAINED_NO_RETRY',phase=args.phase,error_class=type(e).__name__,original_builder_checkout='UNKNOWN',archive_extraction_remove_retry='NOT_RUN')).encode()+b'\n')
            except BaseException:pass
        print(json.dumps(dict(status='FAIL_OR_HOLD_ORIGINAL_PARTIAL_RETAINED_NO_RETRY',phase=args.phase,error_class=type(e).__name__)));return 1
    return 0

if __name__=='__main__':sys.exit(main())
