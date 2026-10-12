"""Root-only future envelope; preparation imports execute no gates."""
import argparse,hashlib,json,os,stat,subprocess,time
from pathlib import Path
D=Path(__file__).parent
PROPOSAL=D/'OWNERFINAL-pr312-actual300-current-e3c-configured-full-NOEXECUTION-proposal-v2.json'
def binding(path):
 p=Path(path);body=p.read_bytes();return {'path':str(p),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
def write_new(path,payload):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as stream:json.dump(payload,stream,indent=2);stream.write('\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--execute-root-authorized',action='store_true');args=parser.parse_args()
 if not args.execute_root_authorized:parser.error('Distinct root authorization is required')
 proposal=json.loads(PROPOSAL.read_bytes());owned=Path(proposal['execution_prerequisites']['expected_owned_execution_directory'])
 assert owned.is_dir() and stat.S_IMODE(owned.stat().st_mode)==0o700
 authpath=owned/'root-one-distinct-source-full-authorization.json';auth=json.loads(authpath.read_bytes())
 assert stat.S_IMODE(authpath.stat().st_mode)==0o600
 assert auth['head']==proposal['head'] and auth['tree']==proposal['tree'] and auth['attempts']==1
 assert auth['approved_proposal_sha256']==binding(PROPOSAL)['sha256']
 for row in proposal['bindings']:
  actual=binding(row['path']);assert actual['bytes']==row['bytes'] and actual['sha256']==row['sha256']
 for row in proposal['fresh_immediate_installed_source_bindings']:
  actual=binding(row['path']);assert actual['bytes']==row['bytes'] and actual['sha256']==row['sha256']
 result={};start=time.monotonic();primarylog=owned/'original-configured-full.private.log'
 # Returned raw output and primary status are sealed BEFORE any postguard.
 fd=os.open(primarylog,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as stream:
  try:
   done=subprocess.run(proposal['command']['primary_argv'],cwd=proposal['command']['cwd'],stdout=stream,stderr=subprocess.STDOUT,check=False)
   result['returncode']=done.returncode;result['exception_category']=None
  except BaseException as error:
   result['returncode']=None;result['exception_category']=type(error).__name__
 result['elapsed_seconds']=time.monotonic()-start;result['original_output']=binding(primarylog)
 try:write_new(owned/'primary-terminal-before-postguards.json',result)
 except BaseException as error:result['terminal_record_error_category']=type(error).__name__
 postlog=owned/'original-postguard.private.log';post={};start=time.monotonic()
 fd=os.open(postlog,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as stream:
  try:
   done=subprocess.run(proposal['command']['post_argv'],cwd=proposal['command']['cwd'],stdout=stream,stderr=subprocess.STDOUT,check=False)
   post['returncode']=done.returncode;post['exception_category']=None
  except BaseException as error:
   post['returncode']=None;post['exception_category']=type(error).__name__
 post['elapsed_seconds']=time.monotonic()-start;post['original_output']=binding(postlog)
 try:write_new(owned/'postguard-terminal-separate.json',post)
 except BaseException as error:post['terminal_record_error_category']=type(error).__name__
 overall=0 if result['returncode']==0 and post['returncode']==0 and 'terminal_record_error_category' not in result and 'terminal_record_error_category' not in post else 10
 write_new(owned/'terminal-primary-and-postguard-distinct.json',{'head':proposal['head'],'tree':proposal['tree'],'primary':result,'postguard':post,'overall_returncode':overall,'attempts':1})
 return overall
if __name__=='__main__':raise SystemExit(main())
