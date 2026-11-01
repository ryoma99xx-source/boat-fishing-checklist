const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});try{
 for(const timezoneId of ['Asia/Tokyo','America/Los_Angeles','Europe/London']){
  const ctx=await browser.newContext({timezoneId,viewport:{width:390,height:844}}),page=await ctx.newPage();
  await page.addInitScript(()=>{const NativeDate=Date,fixed=NativeDate.parse('2026-10-26T15:30:00Z');globalThis.Date=class extends NativeDate{constructor(...args){super(...(args.length?args:[fixed]));}static now(){return fixed;}};});
  await page.route('**/api/current?*',r=>{const u=new URL(r.request().url()),d=JSON.parse(fs.readFileSync('data/current-20261024-8.json'));d.date=u.searchParams.get('date');d.hour=+u.searchParams.get('hour');return r.fulfill({json:d});});
  await page.goto('http://localhost:4173');await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('沿岸参考モデル'));
  assert.equal(await page.locator('#date').inputValue(),'2026-10-27');assert.equal(await page.locator('#time').textContent(),'00:30');
  await page.locator('#date').fill('2026-10-26');await page.locator('#date').dispatchEvent('change');await page.locator('[data-time="22"]').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('沿岸参考モデル'));
  assert.equal(await page.locator('#date').inputValue(),'2026-10-26');assert.equal(await page.locator('#time').textContent(),'11:00');
  await page.locator('#caseDate').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('10/24 潮汐試験'));assert.equal(await page.locator('#date').inputValue(),'2026-10-24');
  await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));await page.waitForFunction(()=>document.querySelector('#date').value==='2026-10-27');
  await page.locator('#caseDate').click();await page.waitForFunction(()=>document.querySelector('#date').value==='2026-10-24');await page.reload();await page.waitForFunction(()=>document.querySelector('#date').value==='2026-10-27');
  console.log('PASS '+timezoneId+': fresh access and restored pages use JST; time buttons preserve date; dated case requires explicit selection.');await ctx.close();
 }
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
