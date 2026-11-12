/* ティップランカウンター: offline support for /tipran/ only. Page is network-first (falls back to the cached copy at sea). */
const VER='tipran-v2';
const PAGE='/tipran/';
const ASSETS=["/tipran/manifest.webmanifest","/tipran/icon-180.png","/tipran/icon-192.png","/tipran/icon-512.png","/tipran/favicon.png"];
const EXTRA='/catalog-extra.json';
self.addEventListener('install',e=>{e.waitUntil(caches.open(VER).then(c=>c.addAll([PAGE,...ASSETS])).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('tipran-')&&k!==VER&&k!=='tipran-fonts'&&k!=='tipran-egi').map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
const timeout=ms=>new Promise((_,r)=>setTimeout(()=>r(new Error('timeout')),ms));
async function netFirst(req,key){const c=await caches.open(VER);try{const res=await Promise.race([fetch(req),timeout(4000)]);if(res&&res.ok)c.put(key,res.clone());return res}catch(err){return (await c.match(key))||Response.error()}}
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;const url=new URL(req.url);
  if(req.mode==='navigate'){if(url.pathname.startsWith('/tipran/'))e.respondWith(netFirst(req,PAGE));return}
  if(url.origin===location.origin&&url.pathname===EXTRA){e.respondWith(netFirst(req,EXTRA));return}
  /* エギの写真：見たものだけ端末に残す（海の上でも出る）。裏で新しいものに入れ替える */
  const swr=name=>e.respondWith((async()=>{const c=await caches.open(name);const hit=await c.match(req);
      const net=fetch(req).then(r=>{if(r.ok)c.put(req,r.clone());return r}).catch(()=>hit||Response.error());return hit||net})());
  if(url.origin===location.origin&&url.pathname.startsWith('/tipran/egi/')){swr('tipran-egi');return}
  if(url.hostname==='fonts.googleapis.com'||url.hostname==='fonts.gstatic.com'){
    e.respondWith((async()=>{const c=await caches.open('tipran-fonts');const hit=await c.match(req);
      const net=fetch(req).then(r=>{c.put(req,r.clone());return r}).catch(()=>hit);return hit||net})());return}
  if(url.origin===location.origin&&ASSETS.includes(url.pathname)){e.respondWith(caches.match(req).then(r=>r||fetch(req)))}
});
