import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire('/workspace/actions-recovery-327/installed-a25/source/action_server/frontend/package.json');
const { chromium } = require('@playwright/test');
const { BASE_URL, TEST_KEY, EVIDENCE_DIR, RESTART } = process.env;
const browser = await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1280,height:900}});
const requests=[];
page.on('request',r=>{const u=new URL(r.url());if(u.pathname==='/api/work-items')requests.push(u.pathname+u.search);});
const receipt={restart:RESTART==='1',requests,screenshots:[]};
try {
 await page.goto(BASE_URL+'/work-items',{waitUntil:'domcontentloaded'});
 await page.getByLabel('API key',{exact:true}).fill(TEST_KEY);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('combobox',{name:'Queue',exact:true}).waitFor();
 const capture=async name=>{await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:EVIDENCE_DIR+'/'+name,fullPage:true,animations:'disabled'});receipt.screenshots.push(name);};
 if(RESTART!=='1') {
  await page.getByRole('heading',{name:'No work items yet'}).waitFor();
  await capture('empty-default-queue.png');
 }
 await page.getByRole('textbox',{name:'Queue to open'}).fill('recovery-custom');
 await page.getByRole('button',{name:'Open queue',exact:true}).click();
 await page.getByText('persisted-a25-proof',{exact:false}).first().waitFor();
 if(await page.getByRole('combobox',{name:'Queue',exact:true}).inputValue()!=='recovery-custom')throw Error('custom selection lost');
 await capture(RESTART==='1'?'custom-queue-after-restart.png':'custom-queue.png');
 if(RESTART!=='1'){
  await page.getByRole('combobox',{name:'Queue',exact:true}).selectOption('');
  await page.getByRole('button',{name:'Create First Item'}).click();
  await page.getByRole('textbox',{name:'Queue Name'}).fill('created-in-ui');
  await page.getByRole('button',{name:'Create',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('select[aria-label="Queue"]')?.value==='created-in-ui');
  await page.getByRole('heading',{name:'Work Items',exact:true}).waitFor();
  await capture('created-custom-queue.png');
  await page.getByRole('textbox',{name:'Queue to open'}).fill('all');
  await page.getByRole('button',{name:'Open queue',exact:true}).click();
  await page.getByRole('heading',{name:'No work items yet'}).waitFor();
  if(!requests.some(u=>u.includes('queue_name=all')))throw Error('literal all omitted');
 }
 receipt.status='PASS';
} catch(e){receipt.status='FAIL';receipt.failure=String(e).replaceAll(TEST_KEY,'[redacted]');throw e;}
finally{fs.writeFileSync(EVIDENCE_DIR+'/browser-'+(RESTART==='1'?'restart':'initial')+'.json',JSON.stringify(receipt,null,2));await browser.close();}
