// Browser integration checks. The Google adapter uses a local SDK stub:
// this does not validate a real Google API key, billing, or Google's own gestures.
const assert=require('node:assert/strict');const fs=require('node:fs');
const {chromium}=require('playwright');
const stub=`
window.__maps=[];window.__overlays=[];
class MockGoogleMap {
 constructor(el,opts){this.el=el;this.opts=opts;this.center=opts.center;this.zoom=opts.zoom;this.events={};window.__maps.push(this);el.style.background='#dbe8e4';setTimeout(()=>this.emit('tilesloaded'),60);}
 addListener(name,fn){(this.events[name]??=[]).push(fn);return {remove:()=>{this.events[name]=this.events[name].filter(x=>x!==fn);}};}
 emit(name,arg){for(const fn of this.events[name]||[])fn(arg);}
 getCenter(){return {lat:()=>this.center.lat,lng:()=>this.center.lng};}
 getZoom(){return this.zoom;}
 setCenter(c){this.center=c;this.emit('idle');for(const o of window.__overlays)if(o.map===this)o.draw();}
 setZoom(z){this.zoom=z;this.emit('idle');for(const o of window.__overlays)if(o.map===this)o.draw();}
}
class LatLng {constructor(lat,lon){this.lat=()=>lat;this.lng=()=>lon;}}
class OverlayView {
 constructor(){window.__overlays.push(this);}
 setMap(map){if(!map)this.onRemove();this.map=map;if(map){this.onAdd();this.draw();}}
 getProjection(){const map=this.map;return {fromLatLngToContainerPixel(ll){const world=(lat,lon)=>{const n=256*2**map.zoom,s=Math.sin(lat*Math.PI/180);return {x:(lon+180)/360*n,y:(.5-Math.log((1+s)/(1-s))/(4*Math.PI))*n};};const p=world(ll.lat(),ll.lng()),c=world(map.center.lat,map.center.lng);return {x:p.x-c.x+map.el.clientWidth/2,y:p.y-c.y+map.el.clientHeight/2};}};}
}
window.google={maps:{Map:MockGoogleMap,LatLng,OverlayView}};window.shioReady();
`;
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const ctx=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true});
  await ctx.addInitScript(()=>{localStorage.setItem('shio-google-key','legacy-personal-key');sessionStorage.setItem('shio-google-key','legacy-session-key');localStorage.setItem('shio-pin',JSON.stringify({lat:35.279,lon:139.708}));});
  const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://localhost:4173');await page.locator('#caseDate').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('10/24 潮汐試験'));
  assert.equal(await page.locator('#googleSetup,#key,#copyReferrer,#rememberGoogle').count(),0);
  await page.waitForFunction(()=>localStorage.getItem('shio-google-key')===null);assert.equal(await page.evaluate(()=>sessionStorage.getItem('shio-google-key')),null);assert.ok(await page.evaluate(()=>localStorage.getItem('shio-pin')));
  await page.locator('#settings').click();assert.doesNotMatch(await page.locator('#modalBody').textContent(),/Google Cloud|API|課金|許可URL/);
  await page.locator('#lat').fill('99');await page.locator('#setCoordinates').click();assert.match(await page.locator('#settingsMessage').textContent(),/青枠内/);
  await page.locator('#lat').fill('35.2795');await page.locator('#lon').fill('139.71');await page.locator('#setCoordinates').click();assert.match(await page.locator('#coordinates').textContent(),/35.27950/);
  const beforeScale=await page.locator('#scale').textContent(),beforePin=await page.locator('#coordinates').textContent(),rect=await page.locator('#map').boundingBox(),x=rect.x+rect.width/2,y=rect.y+rect.height/2;
  const cdp=await ctx.newCDPSession(page);await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{id:1,x:x-25,y},{id:2,x:x+25,y}]});
  for(const d of [40,60,90])await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{id:1,x:x-d,y},{id:2,x:x+d,y}]});await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  assert.notEqual(await page.locator('#scale').textContent(),beforeScale);assert.equal(await page.locator('#coordinates').textContent(),beforePin);
  await page.locator('#home').click();await page.screenshot({path:'/workspace/shio-public-map-390.png',fullPage:true});assert.deepEqual(errors,[]);
  const desktop=await browser.newPage({viewport:{width:1440,height:950}});await desktop.goto('http://localhost:4173');await desktop.locator('#caseDate').click();await desktop.waitForFunction(()=>document.querySelector('#peekFlow').textContent.includes('kn'));assert.equal(await desktop.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await desktop.screenshot({path:'/workspace/shio-public-map-1440.png',fullPage:true});await desktop.close();
  const configured=await browser.newContext({viewport:{width:390,height:844}}),g=await configured.newPage(),gerrors=[];g.on('pageerror',e=>gerrors.push(e.message));
  await g.route('**/api/map-config',r=>r.fulfill({json:{provider:'google',apiKey:'operator-map-test-key'}}));
  await g.route('https://maps.googleapis.com/maps/api/js?*',r=>{assert.equal(new URL(r.request().url()).searchParams.get('key'),'operator-map-test-key');return r.fulfill({contentType:'text/javascript',body:stub});});
  await g.goto('http://localhost:4173');await g.locator('#caseDate').click();await g.waitForFunction(()=>document.querySelector('#mapCredit').textContent.startsWith('Google Maps')&&document.querySelector('#peekFlow').textContent.includes('kn'));
  assert.equal(await g.evaluate(()=>__maps[0].opts.gestureHandling),'greedy');assert.equal(await g.locator('#googleSetup,#key').count(),0);assert.equal(await g.evaluate(()=>localStorage.getItem('shio-google-key')),null);
  await g.evaluate(()=>{__maps[0].setZoom(16);__maps[0].emit('click',{latLng:new google.maps.LatLng(35.2795,139.71)});});assert.match(await g.locator('#coordinates').textContent(),/35.27950/);
  await g.reload();await g.waitForFunction(()=>document.querySelector('#mapCredit').textContent.startsWith('Google Maps'));await g.evaluate(()=>window.gm_authFailure());await g.waitForFunction(()=>!document.body.classList.contains('google'));assert.equal(await g.evaluate(()=>__overlays.every(o=>o.map===null)),true);assert.doesNotMatch(await g.locator('#toast').textContent(),/API|課金|許可/);assert.deepEqual(gerrors,[]);await configured.close();
  const bad=await browser.newPage({viewport:{width:390,height:844}});await bad.route('**/api/map-config',r=>r.fulfill({json:{provider:'google',apiKey:'invalid-operator-key'}}));await bad.route('https://maps.googleapis.com/maps/api/js?*',r=>r.fulfill({contentType:'text/javascript',body:stub.replace('window.shioReady();','window.shioReady();setTimeout(()=>window.gm_authFailure(),5);')}));
  await bad.goto('http://localhost:4173');await bad.locator('#caseDate').click();await bad.waitForFunction(()=>document.querySelector('#toast').textContent.includes('標準表示')&&document.querySelector('#peekFlow').textContent.includes('kn'));assert.equal(await bad.evaluate(()=>document.body.classList.contains('google')),false);assert.match(await bad.locator('#peekFlow').textContent(),/kn/);await bad.close();
  console.log('PASS: public page has no API setup; coordinate input, standard-map pinch, saved fishing point, legacy-key cleanup, and desktop/mobile layouts work.');
  console.log('PASS: operator-configured Google adapter loads automatically; no personal key storage; authentication failure falls back without technical setup prompts.');
  console.log('Google SDK was stubbed; real operator-key validation is pending configuration.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
