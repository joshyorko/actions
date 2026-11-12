"""Exact installed wheel identity and no-work MCP transport probe."""
import asyncio,hashlib,importlib,importlib.metadata,json,sys,zipfile
from pathlib import Path
base=Path('/workspace/actions-327-a41');out=base/'locked-consumer-evidence';consumer=base/'locked-consumer'
inputs=json.loads((out/'inputs.json').read_text())
result={'python':sys.executable,'modules':{},'wheel_members':{},'mcp':{}}
for name in ('actions.server','actions','actions.work_items','mcp'):
 module=importlib.import_module(name)
 location=Path(module.__file__).resolve()
 assert location.is_relative_to(consumer),str(location)
 result['modules'][name]=str(location)
for name,entry in inputs['wheels'].items():
 dist=importlib.metadata.distribution(name)
 assert dist.version==entry['version']
 members=[];total=0
 with zipfile.ZipFile(entry['path']) as archive:
  for member in archive.infolist():
   if member.is_dir() or member.filename.endswith('.dist-info/RECORD'):continue
   assert '.data/' not in member.filename,member.filename
   path=Path(dist.locate_file(member.filename)).resolve()
   assert path.is_relative_to(consumer),str(path)
   data=archive.read(member)
   assert path.read_bytes()==data,member.filename
   members.append({'path':member.filename,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
   total+=len(data)
 result['wheel_members'][name]={'version':dist.version,'count':len(members),'bytes':total,'members':members,'record_excluded':'pip rewrites RECORD during installation'}
assert importlib.metadata.version('mcp')=='2.0.0'
assert importlib.metadata.version('mcp-types')=='2.0.0'
(out/'installed-bytes.json').write_text(json.dumps(result,indent=2)+'\n')

async def probe():
 import httpx2
 from mcp import ClientSession
 from mcp.client.streamable_http import streamable_http_client
 from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
 helper=McpServerSetupHelper()
 app=helper.server.streamable_http_app(streamable_http_path='/mcp',json_response=True,stateless_http=True,transport_security=helper.transport_security)
 async with app.router.lifespan_context(app):
  async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),base_url='http://127.0.0.1:8000') as http:
   async with streamable_http_client('http://127.0.0.1:8000/mcp',http_client=http) as streams:
    async with ClientSession(streams[0],streams[1]) as session:
     handshake=await session.initialize()
     tools=await session.list_tools()
     assert tools.tools==[]
     return {'mcp_version':importlib.metadata.version('mcp'),'mcp_types_version':importlib.metadata.version('mcp-types'),'initialize':handshake.model_dump(mode='json',by_alias=True),'empty_tool_catalog':True,'transport':'in-process ASGI; no network listener or job execution'}
try:
 result['mcp']=asyncio.run(asyncio.wait_for(probe(),timeout=30))
 (out/'mcp-initialize.json').write_text(json.dumps(result['mcp'],indent=2)+'\n')
except BaseException as exc:
 (out/'mcp-initialize.json').write_text(json.dumps({'status':'failed','error_type':type(exc).__name__,'error':str(exc)},indent=2)+'\n')
 raise
print(json.dumps({'member_counts':{k:v['count'] for k,v in result['wheel_members'].items()},'mcp':result['mcp']},indent=2))
