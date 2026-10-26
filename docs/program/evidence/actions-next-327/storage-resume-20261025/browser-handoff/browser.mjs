import {createRequire} from 'node:module';
import fs from 'node:fs';
const receipt={status:'FAIL',phase:'launch',screenshots:[],officialHost:'ext-apps2.0.3',actualChatGPT:false};
let browser;
try {
 const require=createRequire(process.env.ACTIONS_PLAYWRIGHT_PACKAGE);
 const {chromium,expect}=require('@playwright/test');
 const input=JSON.parse(fs.readFileSync(process.env.HOST_INPUT,'utf8'));
 browser=await chromium.launch({headless:true,chromiumSandbox:true});
 receipt.browserVersion=browser.version();
 receipt.playwrightVersion=require('@playwright/test/package.json').version;
 const page=await browser.newPage({viewport:{width:1280,height:1000},extraHTTPHeaders:{Authorization:'Bearer '+process.env.TEST_KEY}});
 receipt.phase='official-host-ui';
 await page.goto('http://localhost:8080/?tool=canvas_get',{waitUntil:'domcontentloaded'});
 await page.getByLabel('Tool',{exact:true}).selectOption('canvas_get',{timeout:30000});
 await page.locator('textarea').fill(JSON.stringify(input.arguments));
 await page.getByRole('button',{name:'Call Tool',exact:true}).click();
 let frame;const deadline=Date.now()+30000;
 while(Date.now()<deadline){for(const f of page.frames()){if(await f.getByRole('button',{name:'Generate report',exact:true}).count()){frame=f;break;}}if(frame)break;await page.waitForTimeout(100);}
 if(!frame)throw Error('generated v2 form did not mount');
 const capture=async label=>{await frame.evaluate(()=>document.fonts.ready);const name=label+'.png';await frame.locator('body').screenshot({path:process.env.EVIDENCE_DIR+'/'+name,animations:'disabled'});receipt.screenshots.push(name);};
 await expect(frame.getByRole('heading',{name:'Generated report',exact:true})).toBeVisible();
 await capture('v2-mounted');
 const submit=async text=>{await frame.getByLabel('Report text',{exact:true}).fill(text);await frame.getByRole('button',{name:'Generate report',exact:true}).click();};
 const visible=async(text,count)=>{
   await expect(frame.getByRole('region',{name:'Processing log entries'})).toContainText('Processed '+text,{timeout:180000});
   await expect(frame.getByRole('region',{name:'Word counts data'})).toContainText(String(count));
   await expect(frame.getByRole('heading',{name:'Report details',exact:true})).toBeVisible();
   await expect(frame.locator('dd').filter({hasText:text})).toBeVisible();
   await expect(frame.getByRole('img',{name:'Word counts',exact:true})).toBeVisible();
 };
 await submit('alpha beta');await visible('alpha beta',2);await capture('v2-first-result');
 await submit('gamma delta epsilon');
 await expect(frame.getByText('Processed alpha beta',{exact:true})).toHaveCount(0);
 await visible('gamma delta epsilon',3);await capture('v2-resubmitted');
 await frame.getByRole('button',{name:'Inspect report artifact',exact:true}).click();
 const artifact=frame.getByRole('region',{name:'Authorized result artifact'});await artifact.waitFor();
 const raw=await artifact.locator('pre').innerText();if(JSON.parse(raw).details.name!=='gamma delta epsilon')throw Error('artifact mismatch');
 await artifact.scrollIntoViewIfNeeded();await artifact.screenshot({path:process.env.EVIDENCE_DIR+'/v2-artifact.png'});receipt.screenshots.push('v2-artifact.png');
 await page.setViewportSize({width:390,height:844});await capture('v2-narrow');
 await submit('fail');await expect(frame.getByText('Processed gamma delta epsilon',{exact:true})).toHaveCount(0);
 await expect(frame.getByRole('region',{name:'Execution report'})).toContainText('failed',{timeout:180000});
 await expect(frame.getByRole('img',{name:'Word counts',exact:true})).toHaveCount(0);await capture('v2-failed-cleared');
 receipt.status='PASS';receipt.phase='complete';receipt.generatedRuns=3;receipt.controls=['resubmit clears prior projection','actual Action failure clears data'];
} catch(error){receipt.failureType=error?.name || 'Error';receipt.failure='Browser qualification failed during '+receipt.phase+'; inspect the private process log.';process.exitCode=1;}
finally{
 if(browser){try{await browser.close();receipt.browserClosed=true;}catch(error){receipt.status='FAIL';receipt.closeFailureType=error?.name || 'Error';process.exitCode=1;}}
 fs.writeFileSync(process.env.EVIDENCE_DIR+'/browser.json',JSON.stringify(receipt,null,2));
}
