// Read private Site service access through hidden stdin. Never put it in page code.
const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
console.log('Ready for private Site access JSON on hidden stdin.');
const rl=require('node:readline').createInterface({input:process.stdin,terminal:false});
rl.once('line',async line=>{
 rl.close();const access=JSON.parse(line),origin=new URL(access.url).origin;
 const meta=JSON.parse(fs.readFileSync('data/tidal-case.json')),raw=fs.readFileSync('data/tidal-frames.bin'),size=meta.wetIds.length*4;
 const expected=crypto.createHash('sha256').update(raw.subarray(17*size,18*size)).digest('hex');
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const context=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true});
  // This header is added in the Node test driver, only for this Site's origin.
  await context.route(origin+'/**',r=>r.continue({headers:{...r.request().headers(),'OAI-Sites-Authorization':'Bearer '+access.token}}));
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/?check=flow-raw2',{waitUntil:'domcontentloaded'});
  await page.locator('#caseDate').click();await page.locator('[data-time="17"]').click();
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent.includes('10/24 潮汐試験'),{},{timeout:30000});
  await page.waitForFunction(()=>document.querySelector('#tideChart svg'));assert.match(await page.locator('#tideStationNote').textContent(),/油壺/);assert.match(await page.locator('#tideChart').textContent(),/03:14/);console.log('LIVE initial:',await page.locator('#peekFlow').textContent());assert.match(await page.locator('#peekFlow').textContent(),/kn/);
  const field=await page.evaluate(async()=>{const r=await fetch('/api/experiment/frame?index=17&format=raw2'),b=await r.arrayBuffer(),hash=await crypto.subtle.digest('SHA-256',b);return {status:r.status,length:b.byteLength,sha256:Array.from(new Uint8Array(hash),v=>v.toString(16).padStart(2,'0')).join('')}});
  assert.equal(field.status,200);assert.equal(field.length,size);assert.equal(field.sha256,expected);console.log('PASS live frame matches the original bytes after browser HTTP decoding:',field.length,'bytes.');
  for(const slot of [22,24,17]){await page.locator('[data-time="'+slot+'"]').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('10/24 潮汐試験'));assert.match(await page.locator('#peekFlow').textContent(),/kn/);assert.match(await page.locator('#tideChart').textContent(),new RegExp((slot/2).toString().padStart(2,'0')+':00 選択|08:30 選択'));console.log('LIVE time:',await page.locator('#time').textContent(),await page.locator('#peekFlow').textContent());}
  for(const region of ['inner','katsuyama','misaki']){await page.locator('#region').selectOption(region);assert.match(await page.locator('#peekFlow').textContent(),/kn/);}
  await page.locator('#home').click();await page.waitForFunction(()=>document.querySelector('#tideStationNote').textContent.includes('油壺'));assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.screenshot({path:'/workspace/shio-live-fixed-mobile.png',fullPage:true});assert.deepEqual(errors,[]);
  console.log('PASS live mobile: time changes, bay head / Katsuyama / Misaki, no page errors or horizontal overflow.');
 }finally{await browser.close()}
}).on('error',e=>{console.error(e.message);process.exitCode=1});
process.on('unhandledRejection',e=>{console.error(e.message);process.exitCode=1});
