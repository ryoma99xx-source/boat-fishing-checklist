// No real Google API calls: validate load suppression and fallback with an SDK stub.
const {chromium}=require('playwright'),fs=require('fs'),assert=require('assert/strict');
const origin=process.env.SHIO_QA_ORIGIN||'http://localhost:4173';
const stub=fs.readFileSync(__dirname+'/qa-google.cjs','utf8').match(/const stub=`([\s\S]*?)`;/)[1];
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  async function create(mode='normal'){
   const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
   await context.addInitScript(()=>{const BaseDate=Date;window.Date=class extends BaseDate{constructor(...args){super(...(args.length?args:['2026-10-23T23:30:00Z']));}static now(){return new BaseDate('2026-10-23T23:30:00Z').getTime();}};});
   if(mode==='storage')await context.addInitScript(()=>{Storage.prototype.setItem=()=>{throw Error('storage unavailable');};});
   const page=await context.newPage();let requests=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',r=>{const u=new URL(r.request().url());
    if(u.pathname==='/api/map-config')return r.fulfill({json:{provider:'google',apiKey:'operator-map-test-key'}});
    if(u.hostname==='maps.googleapis.com'){requests++;return mode==='quota'?r.fulfill({status:429,contentType:'text/javascript',body:''}):r.fulfill({contentType:'text/javascript',body:stub});}
    if(u.origin!==origin)return r.abort();return r.continue();
   });return {page,context,errors,requests:()=>requests};
  }
  const h=await create();await h.page.goto(origin,{waitUntil:'networkidle'});await h.page.waitForFunction(()=>document.querySelector('#mapCredit').textContent.startsWith('Google Maps'));
  await h.page.locator('[data-time="22"]').click();await h.page.waitForFunction(()=>document.querySelector('#time').textContent==='11:00'&&document.querySelector('#peekFlow').textContent.includes('kn'));
  assert.equal(await h.page.evaluate(()=>__maps.length),1,'changing tide time must reuse the map');
  await h.page.reload({waitUntil:'networkidle'});await h.page.waitForFunction(()=>document.body.classList.contains('google'));
  await h.page.reload({waitUntil:'networkidle'});await h.page.waitForFunction(()=>document.body.classList.contains('google'));
  assert.equal(h.requests(),3);await h.page.reload({waitUntil:'networkidle'});
  assert.equal(h.requests(),3,'fourth reload must not request the Google SDK');
  assert.equal(await h.page.evaluate(()=>document.body.classList.contains('google')),false);
  await h.page.waitForFunction(()=>document.querySelector('#peekFlow').textContent.includes('kn'));assert.deepEqual(h.errors,[]);await h.context.close();
  for(const mode of ['storage','quota']){const h=await create(mode);await h.page.goto(origin,{waitUntil:'networkidle'});await h.page.waitForFunction(()=>document.querySelector('#peekFlow').textContent.includes('kn'));assert.equal(await h.page.evaluate(()=>document.body.classList.contains('google')),false);assert.equal(h.requests(),mode==='storage'?0:1);assert.deepEqual(h.errors,[]);await h.context.close();}
  console.log('PASS: fourth rapid reload never loads Google; changing tide time reuses one map; blocked storage and HTTP 429 retain the standard map and current data.');
  console.log('Limits are browser-local supplementary controls, not a global usage or billing cap. Real Google quotas/key validation remain operator setup.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
