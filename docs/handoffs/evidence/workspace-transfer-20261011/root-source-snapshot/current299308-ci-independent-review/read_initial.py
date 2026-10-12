import json,subprocess,datetime
from pathlib import Path
D=Path('/workspace/engineering/current299308-ci-independent-review')
def api(path):return json.loads(subprocess.check_output(['gh','api',path]))
repo='repos/joshyorko/actions';target='774438b130afb2ead9bbc1c1b76cb6f91e72150a'
for n,h in [(299,'5db93e2251cf039ef81780730098da1b255d8d2e'),(308,'4ca431b51b018b947fac6f096ca3cdc21028dd28')]:
 p=api(f'{repo}/pulls/{n}');assert p['head']['sha']==h;sel={k:p.get(k) for k in ['number','state','draft','mergeable','mergeable_state','merge_commit_sha','html_url','changed_files','commits']};sel['head']={k:p['head'].get(k) for k in ['sha','ref']};sel['base']={k:p['base'].get(k) for k in ['sha','ref']};sel['observedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();(D/f'pr{n}-initial-PR.json').write_text(json.dumps(sel,indent=2)+'\n');print(json.dumps(sel))
ref=api(repo+'/git/ref/heads/integration/community-release-20261008');print('TARGET_REF',ref['object']['sha']);assert ref['object']['sha']==target
