import hashlib,json,os,re,stat,subprocess
from pathlib import Path
b=Path('/workspace/engineering'); w=b/'campaign-checkpoint'; dst=w/'docs/handoffs/evidence/workspace-transfer-20261011/root-source-snapshot';dst.mkdir(parents=True,exist_ok=True)
worktrees={Path(x[9:]) for x in subprocess.check_output(['git','worktree','list','--porcelain'],cwd=w,text=True).splitlines() if x.startswith('worktree ')}
patterns=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|X-Amz-Signature=[a-fA-F0-9]{30,}|[?&]sig=[A-Za-z0-9%]{32,}|Bearer [A-Za-z0-9._-]{30,})')
rows=[];excluded=[]
paths=sorted(set(b.glob('*'))|set(b.glob('*/*')))
for p in paths:
 if not p.is_file() or p.is_symlink() or p.parent in worktrees:continue
 selected=p.suffix in ('.py','.sh','.patch') or p.name.startswith('OWNERFINAL') or (p.suffix=='.json' and ('config' in p.name.lower() or 'frozen' in p.name.lower()))
 if not selected:continue
 s=p.stat();r=dict(source=str(p),bytes=s.st_size,mode=oct(stat.S_IMODE(s.st_mode)))
 if s.st_size>2000000: r['reason']='oversize metadata; local only';excluded.append(r);continue
 raw=p.read_bytes();r['sha256']=hashlib.sha256(raw).hexdigest()
 try:raw.decode('utf8')
 except UnicodeDecodeError:r['reason']='nontext';excluded.append(r);continue
 if patterns.search(raw):r['reason']='potential credential or signed URL; not copied';excluded.append(r);continue
 q=dst/p.relative_to(b);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw);q.chmod(0o600)
 r['copy']=str(q.relative_to(w));rows.append(r)
manifest={'scope':'Preservation only. Historical scripts/configuration retain obsolete absolute paths and consumed grants. NOT executable authority, accepted tests, or a portable environment. Rebind fresh paths and validate before use.','copies':rows,'excluded':excluded,'files':len(rows),'bytes':sum(x['bytes'] for x in rows)}
(dst/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'files':len(rows),'bytes':manifest['bytes'],'excluded':excluded}))
