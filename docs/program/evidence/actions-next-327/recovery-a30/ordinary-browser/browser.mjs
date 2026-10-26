import {createRequire} from 'node:module';
import fs from 'node:fs';
const require=createRequire('/workspace/actions/action_server/frontend/package.json');
const {chromium}=require('@playwright/test');
const input=JSON.parse(fs.readFileSync(process.env.HOST_INPUT,'utf8'));
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1280,height:1100},extraHTTPHeaders:{Authorization:'Bearer '+process.env.TEST_KEY}});
const receipt={status:'FAIL',mode:input.mode,phase:input.phase,screenshots:[]};
try {
 await page.goto('http://localhost:8080/?tool=canvas_get',{waitUntil:'domcontentloaded'});
 await page.getByLabel('Tool',{exact:true}).selectOption('canvas_get',{timeout:30000});
 await page.locator('textarea').fill(JSON.stringify(input.arguments));
 await page.getByRole('button',{name:'Call Tool',exact:true}).click();
 let frame;
 const deadline=Date.now()+30000;
 while(Date.now()<deadline){for(const f of page.frames()){if(await f.getByRole('button',{name:input.mode==='consumer'?'Load inputs':'Inspect NDJSON',exact:true}).count()){frame=f;break;}}if(frame)break;await page.waitForTimeout(100);}
 if(!frame)throw Error('official generic input/output form did not mount');
 const capture=async suffix=>{const name=input.mode+'-'+input.phase+'-'+suffix+'.png';await frame.evaluate(()=>document.fonts.ready);await frame.locator('body').screenshot({path:process.env.EVIDENCE_DIR+'/'+name,animations:'disabled'});receipt.screenshots.push(name);};
 await capture('mounted');
 if(input.phase==='execute'){
  if(input.mode==='consumer'){
   await frame.getByRole('button',{name:'Load inputs',exact:true}).click();
   await frame.getByLabel('Input item for echo',{exact:true}).selectOption(input.itemId);
   await capture('selected');
   await frame.getByRole('button',{name:'Claim selected input',exact:true}).click();
   await frame.getByRole('button',{name:'Continue execution',exact:true}).click();
  } else {
   await frame.getByLabel('NDJSON records',{exact:true}).fill(input.ndjson);
   await frame.getByRole('button',{name:'Inspect NDJSON',exact:true}).click();
  }
 }
 await frame.getByRole('region',{name:'Execution echo'}).getByRole('status').filter({hasText:/^completed$/}).waitFor({timeout:180000});
 await frame.getByRole('button',{name:'Load produced items',exact:true}).click();
 const outputs=frame.getByRole('region',{name:'Produced Work Items for echo'});
 await outputs.getByText(/recordCount/).waitFor();
 receipt.producedText=await outputs.innerText();
 if(!receipt.producedText.includes('recordCount')||!receipt.producedText.includes('fieldNames'))throw Error('missing produced summary');
 await frame.getByRole('button',{name:'Inspect result',exact:true}).click();
 const artifact=frame.getByRole('region',{name:'Authorized result artifact'});
 await artifact.waitFor();receipt.artifactText=await artifact.innerText();
 if(!receipt.artifactText.includes('recordCount'))throw Error('missing genuine summary artifact');
 const parsed=JSON.parse(receipt.artifactText);
 if(parsed.result.recordCount!==input.expectedCount||JSON.stringify(parsed.result.fieldNames)!==JSON.stringify(['amount','city']))throw Error('incorrect genuine record summary');
 await capture('completed');receipt.status='PASS';
} catch(e) {receipt.failure=String(e).replaceAll(process.env.TEST_KEY,'[redacted]');throw e;}
finally {fs.writeFileSync(process.env.EVIDENCE_DIR+'/'+input.mode+'-'+input.phase+'-browser.json',JSON.stringify(receipt,null,2));await browser.close();}
