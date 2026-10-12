import os, json, stat, hashlib, time
from pathlib import Path
from collections import Counter
OUT=Path('/workspace/engineering/capacity-recovery-batch26-proposal')
BASE=Path('/workspace/actions-cloud/robocorp/temp')
archives=sorted(set(Path('/tmp').glob('actions-completed-scratch-recovery*/*.tar.gz'))|set(Path('/dev/shm').glob('actions-completed-scratch-recovery*/*.tar.gz')))
excluded={p.name.removesuffix('.tar.gz') for p in archives}|{'563d911e4172f035','ad13a81675676d7b'}
rows=[]
for p in BASE.iterdir():
    if p.name in excluded or p.is_symlink() or not p.is_dir(): continue
    try:
        if (p/'recycle.now').read_text().strip()!='True': continue
    except (OSError,UnicodeError): continue
    total=0; logical=0; seen=set(); kinds=Counter(); entries=[]
    for d, ds, fs in os.walk(p,followlinks=False):
        for n in ds+fs:
            f=Path(d)/n;s=f.lstat();kind='file' if stat.S_ISREG(s.st_mode) else 'directory' if stat.S_ISDIR(s.st_mode) else 'symlink' if stat.S_ISLNK(s.st_mode) else 'fifo' if stat.S_ISFIFO(s.st_mode) else 'unsupported';kinds[kind]+=1
            if (s.st_dev,s.st_ino) not in seen: total+=s.st_blocks*512;seen.add((s.st_dev,s.st_ino))
            if kind=='file':logical+=s.st_size
    rows.append({'name':p.name,'allocated_unique_blocks_bytes':total,'regular_logical_bytes':logical,'member_kinds':dict(kinds),'marker_true':True})
rows.sort(key=lambda x:x['allocated_unique_blocks_bytes'],reverse=True)
assert rows
selected=[];allocated=0
for row in rows[:8]:
 selected.append(row);allocated+=row['allocated_unique_blocks_bytes']
 if allocated>=200000000:break
x={'captured_unix':time.time(),'prior_archive_count':len(archives),'prior_archive_paths_private':[str(p) for p in archives],'excluded_names_private':sorted(excluded),'completed_candidates_private':rows,'selected':selected,'selected_total_allocated':allocated,'source_origin':'UNREPORTED'}
f=OUT/'private-complete-completed-candidate-metadata-census.json';f.write_text(json.dumps(x,indent=2)+'\n');f.chmod(0o600)
print(json.dumps({'prior_archive_count':len(archives),'completed_candidate_count':len(rows),'selected_names':[r['name'] for r in selected],'selected_allocated_bytes':allocated,'selected_logical_bytes':sum(r['regular_logical_bytes'] for r in selected),'selected_count':len(selected)}))
