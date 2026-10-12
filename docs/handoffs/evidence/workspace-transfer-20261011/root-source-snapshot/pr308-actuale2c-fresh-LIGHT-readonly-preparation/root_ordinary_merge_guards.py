"""Read-only guards for root's explicitly adopted ordinary merge; no gate execution."""
import subprocess,sys
R='/workspace/engineering/pr308';S='396925cb3d6527af1768b7f5333f9653c005fc55';T='e2c81adce7858d5a952991ba9a8b7f72e902038a';TREE='929410b09fff3521c554cf935411c71f9e2e6b95'
def git(*x):return subprocess.check_output(['git','-C',R,*x]).decode().strip()
assert sys.flags.optimize==0 and sys.argv[1] in ('before','merged-index','committed')
assert git('branch','--show-current')=='fix/rcc-candidate-wheel-identities-20261010'
assert git('rev-parse','refs/remotes/origin/integration/community-release-20261008')==T
if sys.argv[1]=='before':
 assert git('rev-parse','HEAD')==S and not git('status','--porcelain')
elif sys.argv[1]=='merged-index':
 assert git('rev-parse','HEAD')==S and git('rev-parse','MERGE_HEAD')==T
 assert git('write-tree')==TREE and not git('diff','--name-only')
else:
 assert git('show','-s','--format=%P','HEAD').split()==[S,T]
 assert git('rev-parse','HEAD^{tree}')==TREE and not git('status','--porcelain')
print('ROOT_ORDINARY_MERGE_GUARD_PASS',sys.argv[1])
