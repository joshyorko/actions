from pathlib import Path
import re,json,hashlib
D=Path('/workspace/engineering/pr306-actual776-refresh');p=D/'original1a-linux-job-114414469493.private.log';text=p.read_text();lines=text.splitlines()
checkouts=[]
for i,line in enumerate(lines):
 if 'git log -1' in line:
  for j in range(i+1,min(i+5,len(lines))):
   tail=re.sub(r'^\d{4}-\d\d-\d\dT[^ ]+\s+','',lines[j]).strip()
   if re.fullmatch('[0-9a-f]{40}',tail):checkouts.append({'line':j+1,'sha':tail})
nodes=[]
for i,line in enumerate(lines):
 for m in re.finditer(r'\b(?:FAILED|ERROR)\s+((?:tests/)?(?:action_server_tests|contract_tests)/[A-Za-z0-9_/.]+\.py::[A-Za-z0-9_]+)',line):nodes.append({'line':i+1,'node_without_parameters':m[1]})
counters=[]
for i,line in enumerate(lines):
 if ' passed' in line and re.search(r'\d+ passed',line) and ('====' in line or ' failed,' in line):
  counters.append({'line':i+1,'counts':{k:int(m[1]) for k in ('failed','passed','skipped','deselected','warnings') if (m:=re.search(r'(\d+) '+k,line))},'seconds':float(m[1]) if (m:=re.search(r'in ([0-9.]+)s',line)) else None})
categories={label:[i+1 for i,line in enumerate(lines) if regex.search(line)] for label,regex in {'TimeoutError':re.compile(r'\bTimeoutError\b'),'ValueError':re.compile(r'\bValueError\b'),'AssertionError':re.compile(r'\bAssertionError\b'),'DID_NOT_RAISE':re.compile('DID NOT RAISE'),'ready_port_poll':re.compile('port.*ready|ready.*port',re.I),'startup_cleanup_note':re.compile('cleanup did not fully complete'),'connection_error':re.compile(r'ConnectionRefusedError|ConnectError|ConnectionError'),'ERROR_or_FAILED_summary':re.compile(r'\b(?:ERROR|FAILED)\s+(?:action_server_tests|contract_tests)')}.items()}
result={'original_log':{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':oct(p.stat().st_mode&0o777)},'decoded_lines':len(lines),'full_decoded_connector_structuredContent_saved_once':True,'checkout_sha_candidates':checkouts,'failure_nodes_without_parameters':nodes,'pytest_terminal_counters':counters,'fixed_line_categories':categories,'observer_receipt_presence':'UNAVAILABLE; no diagnostic artifact acquired','no_raw_lines_payload_or_credentials_emitted':True}
(D/'safe-original-linux-log-census.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
