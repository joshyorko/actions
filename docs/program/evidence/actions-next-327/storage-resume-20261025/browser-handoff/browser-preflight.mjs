import {createRequire} from 'node:module';
import fs from 'node:fs';
let browser;
const receipt={status:'FAIL',sandbox:true,phase:'launch'};
try {
 const require=createRequire(process.env.ACTIONS_PLAYWRIGHT_PACKAGE);
 const {chromium}=require('@playwright/test');
 browser=await chromium.launch({headless:true,chromiumSandbox:true});
 receipt.browserVersion=browser.version();
 receipt.playwrightVersion=require('@playwright/test/package.json').version;
 const page=await browser.newPage();
 await page.goto('data:text/html,<title>Sandbox preflight</title>');
 if(await page.title()!=='Sandbox preflight')throw Error('title mismatch');
 receipt.status='PASS';receipt.phase='complete';
} catch(error){receipt.failureType=error?.name || 'Error';process.exitCode=1;}
finally {
 if(browser){try{await browser.close();receipt.browserClosed=true;}catch(error){receipt.status='FAIL';receipt.closeFailureType=error?.name || 'Error';process.exitCode=1;}}
 fs.writeFileSync(process.env.EVIDENCE_DIR+'/browser-preflight.json',JSON.stringify(receipt,null,2));
}
