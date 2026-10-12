"""Metadata-only successor filling the real independent V9 source-review slot."""
from pathlib import Path
import json
import hashlib
import os
import stat

BASE=Path(__file__).resolve().parent
ORIGINAL=BASE/'FROZEN-current8d49-control3-qualified-V9-entry-config.json'
ORIGINAL_SHA='e66d63863d1f2f2384bca32dec1e5bbf448e056b891a3d972689402d36646358'
REVIEW=Path('/workspace/engineering/rcc-current8d49-V9-entry-bootstrap-independent-source-review/OWNERFINAL-independent-current8d49-V9-entry-bootstrap-SOURCE-review.json')
REVIEW_SHA='bfce810be260cf7b9630516777fc9c6c9197c976feffa16927db22396d032c8b'
OUTPUT=BASE/'FROZEN-current8d49-control3-qualified-V9-entry-config-v2.json'

def bind(p):
    p=Path(p);meta=p.lstat();assert stat.S_ISREG(meta.st_mode) and not p.is_symlink();raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mode=oct(stat.S_IMODE(meta.st_mode)))

if __name__=='__main__':
    assert bind(ORIGINAL)['sha256']==ORIGINAL_SHA
    assert bind(REVIEW)['sha256']==REVIEW_SHA
    cfg=json.loads(ORIGINAL.read_text());review=json.loads(REVIEW.read_text())
    assert review['decision']=='GO_CURRENT8D49_NAMED_V9_ENTRY_BOOTSTRAP_SOURCE_ONLY' and review['source']==cfg['source'] and review['tree']==cfg['tree']
    previous=list(cfg['bindings']);assert len(previous)==305
    for p in (REVIEW,Path(__file__).resolve(),BASE/'validate_named_V9_config_plan_import_only.py'):
        row=bind(p);assert row['path'] not in {r['path'] for r in cfg['bindings']};cfg['bindings'].append(row)
    assert cfg['bindings'][:305]==previous and len(cfg['bindings'])==308
    assert not Path(cfg['owned_root']).exists() and not Path(cfg['owned_root']).is_symlink()
    raw=(json.dumps(cfg,indent=2,sort_keys=True)+'\n').encode();f=os.open(OUTPUT,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(f,'wb') as out:out.write(raw)
    print(json.dumps({'config':bind(OUTPUT),'source_review':bind(REVIEW),'only_metadata_delta':'Append exactly3 independent-review/constructor/data-only-plan-proof bindings; all305 previous rows and other topfields exact','native_executed':False}))
