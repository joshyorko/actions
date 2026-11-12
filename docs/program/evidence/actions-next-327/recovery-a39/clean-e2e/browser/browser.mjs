import {createRequire} from 'node:module';
import fs from 'node:fs';
const require=createRequire(process.env.ACTIONS_PLAYWRIGHT_PACKAGE || '/workspace/actions-327-a38/installed-fixed/source/action_server/frontend/package.json');
const {chromium,expect}=require('@playwright/test');
const input=JSON.parse(fs.readFileSync(process.env.HOST_INPUT,'utf8'));
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1280,height:1000},extraHTTPHeaders:{Authorization:'Bearer '+process.env.TEST_KEY}});
const receipt={status:'FAIL',screenshots:[],officialHost:'ext-apps2.0.3'};
try{
 await page.goto('http://localhost:8080/?tool=canvas_get',{waitUntil:'domcontentloaded'});
 await page.getByLabel('Tool',{exact:true}).selectOption('canvas_get',{timeout:30000});
 await page.locator('textarea').fill(JSON.stringify(input.arguments));
 await page.getByRole('button',{name:'Call Tool',exact:true}).click();
 let frame;const deadline=Date.now()+30000;
 while(Date.now()<deadline){for(const f of page.frames()){if(await f.getByRole('button',{name:'Count words',exact:true}).count()){frame=f;break;}}if(frame)break;await page.waitForTimeout(100);}
 if(!frame)throw Error('official generated word counter did not mount');
 const capture=async label=>{await frame.evaluate(()=>document.fonts.ready);const name=label+'.png';await frame.locator('body').screenshot({path:process.env.EVIDENCE_DIR+'/'+name,animations:'disabled'});receipt.screenshots.push(name);};
 await capture('word-counter-mounted');
 await frame.getByLabel('Text to count',{exact:true}).fill('alpha beta beta');
 await frame.getByRole('button',{name:'Count words',exact:true}).click();
 await frame.getByRole('region',{name:'Execution count'}).getByRole('status').filter({hasText:/^completed$/}).waitFor({timeout:180000});
 await frame.getByRole('button',{name:'Inspect result',exact:true}).click();
 const result=frame.getByRole('region',{name:'Authorized result artifact'});await result.waitFor();
 const raw=await result.locator('pre').innerText();receipt.artifactText=raw;
 if(JSON.parse(raw)!==3)throw Error('wrong actual generated word count');
 await capture('word-counter-completed');
 await result.scrollIntoViewIfNeeded();
 await result.screenshot({path:process.env.EVIDENCE_DIR+'/word-counter-artifact.png',animations:'disabled'});receipt.screenshots.push('word-counter-artifact.png');
 await page.setViewportSize({width:390,height:844});await capture('word-counter-narrow');
 receipt.status='PASS';
}catch(e){receipt.failure=String(e).replaceAll(process.env.TEST_KEY,'[redacted]');throw e;}
finally{fs.writeFileSync(process.env.EVIDENCE_DIR+'/browser.json',JSON.stringify(receipt,null,2));await browser.close();}
