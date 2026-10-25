import importlib,json,os,sys
source,input_file,result_file=sys.argv[1:4]
with open(input_file,'rb') as stream: inputs=json.load(stream)
sys.path.insert(0,source)
module=importlib.import_module('generated_actions')
action=getattr(module,'report')
value=action(**inputs)
payload=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
if len(payload)>524288: raise SystemExit(86)
fd=os.open(result_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as stream: stream.write(payload)
