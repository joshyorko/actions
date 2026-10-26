import {createRequire} from 'node:module';
import fs from 'node:fs';
const require=createRequire('/workspace/actions/action_server/frontend/package.json');
const {chromium}=require('@playwright/test');
const input=JSON.parse(fs.readFileSync(process.env.HOST_INPUT,'utf8'));
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1280,height:1100},extraHTTPHeaders:{Authorization:'Bearer '+process.env.TEST_KEY}});
const receipt={status:'FAIL',mode:input.mode,screenshots:[]};
try{
 await page.goto('http://localhost:8080/?tool=canvas_get',{waitUntil:'domcontentloaded'});
 await page.getByLabel('Tool',{exact:true}).selectOption('canvas_get',{timeout:30000});
 await page.locator('textarea').fill(JSON.stringify(input.arguments));
 await page.getByRole('button',{name:'Call Tool',exact:true}).click();
 let frame;
 const deadline=Date.now()+30000;
 while(Date.now()<deadline){for(const f of page.frames()){if(await f.getByRole('button',{name:'Run job',exact:true}).count()){frame=f;break;}}if(frame)break;await page.waitForTimeout(100);}
 if(!frame)throw Error('official generic form did not mount');
 const capture=async suffix=>{const name=input.mode+'-'+suffix+'.png';await frame.evaluate(()=>document.fonts.ready);await frame.locator('body').screenshot({path:process.env.EVIDENCE_DIR+'/'+name,animations:'disabled'});receipt.screenshots.push(name);};
 await capture('mounted');
 if(input.mode==='execute'){
  await frame.getByLabel('Value',{exact:true}).fill('Installed browser generic execution');
  await frame.getByRole('button',{name:'Run job',exact:true}).click();
 }
 await frame.getByRole('region',{name:'Execution echo'}).getByRole('status').filter({hasText:/^completed$/}).waitFor({timeout:180000});
 await frame.getByRole('button',{name:'Inspect result',exact:true}).click();
 const artifact=frame.getByRole('region',{name:'Authorized result artifact'});
 await artifact.waitFor();
 receipt.artifactText=await artifact.innerText();
 if(!receipt.artifactText)throw Error('empty artifact readback');
 await capture('completed');receipt.status='PASS';
}catch(e){receipt.failure=String(e).replaceAll(process.env.TEST_KEY,'[redacted]');throw e;}
finally{fs.writeFileSync(process.env.EVIDENCE_DIR+'/'+input.mode+'-browser.json',JSON.stringify(receipt,null,2));await browser.close();}
