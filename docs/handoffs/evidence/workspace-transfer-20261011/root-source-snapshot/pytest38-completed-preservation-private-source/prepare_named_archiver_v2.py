from pathlib import Path
OUT=Path(__file__).parent
s=(OUT/'preserve_exact_pytest38_once.py').read_text()
a=s.index('def global_guard(config):');b=s.index('\n\ndef authorization',a)
s=s[:a]+'''def git_rows(source, head):
    raw=subprocess.check_output(['git','-C',str(source),'ls-tree','-r','-z',head],timeout=30)
    result=[]
    for part in raw.split(b'\\x00'):
        if not part:continue
        info,name=part.split(b'\\t',1);mode,kind,oid=info.decode().split()
        need(kind=='blob','SOURCE_NONBLOB')
        result.append(dict(path=name.decode(),mode=mode,oid=oid))
    return result


def global_guard(config):
    for row in config['retained_files']: binding(row)
    need(Path(config['failed563_existence_only']).is_dir(), 'FAILED563_EXISTENCE_ONLY')
    source=Path(config['source_root'])
    need(subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],timeout=10).decode().strip()
         ==config['current_head'],'CURRENT_SOURCE_HEAD')
    need(subprocess.check_output(['git','-C',str(source),'status','--porcelain'],timeout=10)==b'',
         'CURRENT_SOURCE_CLEAN')
    for headkey,rowkey in [('current_head','current_rows'),('historical_head','historical_rows')]:
        rows=config[rowkey]
        need(git_rows(source,config[headkey])==[{k:r[k] for k in ('path','mode','oid')} for r in rows],
             'COMPLETE_GIT_BODY_MODE_SET')
        raw=subprocess.check_output(['git','-C',str(source),'cat-file','--batch'],
              input=''.join(r['oid']+'\\n' for r in rows).encode(),timeout=60)
        cursor=0
        for r in rows:
            end=raw.index(b'\\n',cursor);oid,kind,size=raw[cursor:end].decode().split();size=int(size)
            body=raw[end+1:end+1+size];cursor=end+size+2
            need(oid==r['oid'] and kind=='blob' and len(body)==r['bytes'] and
                 hashlib.sha256(body).hexdigest()==r['sha256'],'GIT_BODY_HASH')
            if rowkey=='current_rows':
                p=source/r['path'];st=p.lstat()
                if r['mode']=='120000':
                    need(p.is_symlink() and hashlib.sha256(os.fsencode(os.readlink(p))).hexdigest()==r['sha256'],
                         'CURRENT_SOURCE_LINK')
                else:
                    need(stat.S_ISREG(st.st_mode) and not p.is_symlink() and sha(p)==r['sha256']
                         and stat.S_IMODE(st.st_mode)==r['fs_mode'],'CURRENT_SOURCE_BODY_MODE')
        need(cursor==len(raw),'GIT_BATCH_COMPLETE')
    for path,digest in config['prepared_inputs'].items():
        need(sha(source/path)==digest,'PREPARED_INPUT_BYTES')
    native=Path(config['native_root'])
    for row in config['native_members']:
        p=native/row['path'];need(stat.S_IMODE(p.lstat().st_mode)==row['mode'],'NATIVE_MODE')
        if row['kind']=='file':need(not p.is_symlink() and sha(p)==row['content_sha256'],'NATIVE_BODY')
        elif row['kind']=='directory':need(p.is_dir() and not p.is_symlink(),'NATIVE_DIRECTORY')
        else:need(p.is_symlink() and os.readlink(p)==row['link_target'],'NATIVE_LINK')
    need({p.relative_to(native).as_posix() for p in native.rglob('*')}==
         {r['path'] for r in config['native_members']},'NATIVE_COMPLETE_SET')
    wanted=config['failed_result_member']
    with tarfile.open(config['failed_archive']['path'],'r|gz') as t:
        for member in t:
            if member.name==wanted:
                need(member.isfile() and member.size==config['failed_result_bytes'],'FAILED_ORIGINAL_MEMBER')
                raw=t.extractfile(member).read()
                need(hashlib.sha256(raw).hexdigest()==config['failed_result_sha256'] and
                     json.loads(raw)['status']=='FAIL','FAILED_ACTUAL_UNCHANGED');break
        else:need(False,'FAILED_ORIGINAL_MEMBER_MISSING')
    return dict(retained=len(config['retained_files']),current_source_head=config['current_head'],
         current_source_count=len(config['current_rows']),current_source_qualification='HOLD',
         historical_source_count=len(config['historical_rows']),native_members=len(config['native_members']),
         failed563='EXISTENCE_ONLY',original_failed_actual='FAIL_UNCHANGED')
''' + s[b:]
s=s.replace("owner_proposal=config['owner_proposal'],independent_review=release.get('independent_review'),", "owner_proposal=config['owner_proposal'],implementation_proposal=release.get('implementation_proposal'),\n         independent_review=release.get('independent_review'),")
s=s.replace("review=release['independent_review']; binding(review)","implementation=release['implementation_proposal'];binding(implementation)\n    implementation_body=json.loads(Path(implementation['path']).read_bytes())\n    need(implementation_body['script']['sha256']==sha(__file__) and\n         implementation_body['configuration']['sha256']==config_sha,'IMPLEMENTATION_PROPOSAL_BINDING')\n    review=release['independent_review']; binding(review)")
s=s.replace("# Parent guards are attempted before and after every operation outcome, including timeout.","# Parent guards are attempted before and after every operation outcome, including timeout.\n    def parent_terminated(signum,frame):raise RuntimeError('PARENT_OUTER_DEADLINE_SIGNAL')\n    signal.signal(signal.SIGTERM,parent_terminated)")
# If killed while an inventory/index phase runs, original remains until the guarded removal step.
p=OUT/'preserve_exact_pytest38_once_v2.py';p.open('x').write(s);p.chmod(0o600)
t=(OUT/'test_pytest38_archiver_controls.py').read_text().replace("HERE/'preserve_exact_pytest38_once.py'","HERE/'preserve_exact_pytest38_once_v2.py'")
t=t.replace('import tarfile\n','import tarfile\nimport zlib\n').replace('==7','==6').replace("match='ARCHIVE_CEILING'","match='ARCHIVE_SIZE_BOUND'").replace("match='ARCHIVE_FREE_RESERVE'","match='ARCHIVE_FREE_SPACE_BOUND'").replace('(RuntimeError,OSError,EOFError)','(RuntimeError,OSError,EOFError,zlib.error)')
p=OUT/'test_pytest38_archiver_controls_v2.py';p.open('x').write(t);p.chmod(0o600)
