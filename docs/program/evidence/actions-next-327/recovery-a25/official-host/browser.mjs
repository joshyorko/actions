import {createRequire} from 'node:module';
import fs from 'node:fs';
const require=createRequire('/workspace/actions-recovery-327/installed-a25/source/action_server/frontend/package.json');
const {chromium}=require('@playwright/test');
const input=JSON.parse(fs.readFileSync(process.env.HOST_INPUT,'utf8'));
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1280,height:1100},extraHTTPHeaders:{Authorization:'Bearer '+process.env.TEST_KEY}});
const receipt={application:input.application,status:'FAIL',screenshots:[]};
try{
 await page.goto('http://localhost:8080/?tool=canvas_get',{waitUntil:'domcontentloaded'});
 await page.getByLabel('Tool',{exact:true}).selectOption('canvas_get',{timeout:30000});
 await page.locator('textarea').fill(JSON.stringify(input.arguments));
 await page.getByRole('button',{name:'Call Tool',exact:true}).click();
 let frame;
 const until=Date.now()+30000;
 while(Date.now()<until){for(const f of page.frames()){if(await f.getByRole('button',{name:'Review these results',exact:true}).count()){frame=f;break;}}if(frame)break;await page.waitForTimeout(100);}
 if(!frame)throw Error('official View review action not mounted');
 const capture=async suffix=>{const name=input.application+'-'+suffix+'.png';await frame.evaluate(()=>document.fonts.ready);await frame.locator('body').screenshot({path:process.env.EVIDENCE_DIR+'/'+name,animations:'disabled'});receipt.screenshots.push(name);};
 await capture('mounted');
 await frame.getByRole('button',{name:'Review these results',exact:true}).click();
 await frame.getByRole('button',{name:'Inspect complete saved result',exact:true}).click();
 await frame.getByLabel('Exact saved result').waitFor();
 await capture('review');
 await frame.getByRole('button',{name:'Approve these results',exact:true}).click();
 await frame.getByRole('button',{name:'Execute approved result',exact:true}).click();
 await frame.getByRole('button',{name:'View execution result',exact:true}).waitFor({timeout:120000});
 await frame.getByRole('button',{name:'View execution result',exact:true}).click();
 const text=await frame.getByLabel('Sealed execution result').innerText();
 const expected=input.application==='ndjson-inspector'?'record_count':'invoice_count';
 if(!text.includes(expected))throw Error('unexpected generated result');
 await capture('executed');
 receipt.result_text=text;receipt.status='PASS';
}catch(e){receipt.failure=String(e).replaceAll(process.env.TEST_KEY,'[redacted]');throw e;}
finally{fs.writeFileSync(process.env.EVIDENCE_DIR+'/'+input.application+'-browser.json',JSON.stringify(receipt,null,2));await browser.close();}
