import {createRequire} from 'node:module';
const require=createRequire('/workspace/actions/action_server/frontend/package.json');
const {chromium}=require('@playwright/test');
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,chromiumSandbox:true});
try {const page=await browser.newPage();await page.goto('data:text/html,<title>sandbox probe</title>');if(await page.title()!=='sandbox probe')throw Error('title mismatch');console.log('SANDBOXED_BROWSER_PASS');} finally {await browser.close();}
