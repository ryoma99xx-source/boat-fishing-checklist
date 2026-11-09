import fs from 'node:fs';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {packHarmonic} from '../worker/harmonic-build.mjs';
const api=fs.readFileSync('worker/api.js','utf8').replaceAll('export ','');
const frameApi=fs.readFileSync('worker/frame.js','utf8').replaceAll('export ','');
const mapConfigApi=fs.readFileSync('worker/map-config.js','utf8').replaceAll('export ','');
const harmonicApi=fs.readFileSync('worker/harmonic.js','utf8').replaceAll('export ','');
const htmlSource=fs.readFileSync('app.html','utf8');
const js=fs.readFileSync('app.js','utf8');
const geo=fs.readFileSync('geometry.js','utf8');
const coverage=fs.readFileSync('coverage.js','utf8');
const chart=fs.readFileSync('chart.js','utf8');
const modules={};for(const f of ['harmonic.js','currents.js','spots.js','flow-layer.js'])modules['/'+f]=fs.readFileSync(f,'utf8');
const tideModule=fs.readFileSync('tide.js','utf8');
const clockModule=fs.readFileSync('clock.js','utf8');
const googleGuard=fs.readFileSync('google-guard.js','utf8');
const mapGestures=fs.readFileSync('map-gestures.js','utf8');
const harmonic=packHarmonic('data');
if(!JSON.parse(harmonic.index).grids.length)throw Error('No harmonic current grid in data/');
// Only the basemap placement is needed from the old coastal model.
const coastalMap=JSON.stringify(JSON.parse(fs.readFileSync('data/coastal-model.json','utf8')).map);
// Legacy static basemaps: no longer fetched by the app; bundled only if present.
const map=fs.existsSync('data/coastal-map.webp')?fs.readFileSync('data/coastal-map.webp').toString('base64'):'';
const logo=fs.readFileSync('data/brand-logo.png').toString('base64');
const iconTypes={'favicon.ico':'image/x-icon','favicon-32.png':'image/png','apple-touch-icon.png':'image/png','icon-192.png':'image/png','icon-512.png':'image/png'};
const icons={};for(const [name,type] of Object.entries(iconTypes))icons['/'+name]={type,data:fs.readFileSync('data/site-icons/'+name).toString('base64')};
const iconRevision=createHash('sha256').update(JSON.stringify(icons)).digest('hex').slice(0,12);
const webmanifest=JSON.stringify({id:'/',name:'東京湾の潮と流れ | TIDE & CURRENT MAP',short_name:'潮流マップ',lang:'ja',start_url:'/',scope:'/',display:'standalone',background_color:'#06080f',theme_color:'#06080f',icons:[{src:'/icon-192.png?v='+iconRevision,sizes:'192x192',type:'image/png',purpose:'any'},{src:'/icon-512.png?v='+iconRevision,sizes:'512x512',type:'image/png',purpose:'any'}]});
const overview=fs.readFileSync('data/overview-map.json','utf8');
const overviewMap=fs.existsSync('data/overview-map.webp')?fs.readFileSync('data/overview-map.webp').toString('base64'):'';
const css=fs.readFileSync('app.css','utf8');
const revision=createHash('sha256').update(js+css+Object.values(modules).join('')).digest('hex').slice(0,12);
const html=htmlSource.replace('/app.js','/app.js?v='+revision).replace('/app.css','/app.css?v='+revision).replaceAll('__ICON_VERSION__',iconRevision);
const tideTables={};for(const code of ['TK','Z1','MR','TT','ZF','CS']){const path='data/'+code+'-2026.txt';if(fs.existsSync(path))tideTables[code]=fs.readFileSync(path,'utf8');}
const snapshots={};for(const f of fs.readdirSync('data'))if(f.startsWith('current-')){const d=JSON.parse(fs.readFileSync('data/'+f,'utf8'));snapshots[d.date+'/'+d.hour]=d;}
fs.mkdirSync('dist/server',{recursive:true});fs.mkdirSync('dist/.openai',{recursive:true});
const manifest=JSON.parse(fs.readFileSync('.openai/hosting.json','utf8'));delete manifest.static;
fs.writeFileSync('.openai/hosting.json',JSON.stringify(manifest,null,2));
fs.copyFileSync('.openai/hosting.json','dist/.openai/hosting.json');
fs.writeFileSync('dist/server/index.js',api+frameApi+mapConfigApi+harmonicApi+`\nconst HTML=${JSON.stringify(html)},JS=${JSON.stringify(js)},GEO=${JSON.stringify(geo)},COVERAGE=${JSON.stringify(coverage)},CHART=${JSON.stringify(chart)},COASTALMAP=${JSON.stringify(coastalMap)},MAP=${JSON.stringify(map)},OVERVIEW=${JSON.stringify(overview)},OVERVIEWMAP=${JSON.stringify(overviewMap)},CSS=${JSON.stringify(css)},TIDETABLES=${JSON.stringify(tideTables)},SNAPSHOTS=${JSON.stringify(snapshots)};
const LOGO=${JSON.stringify(logo)},ICONS=${JSON.stringify(icons)},WEBMANIFEST=${JSON.stringify(webmanifest)},TIDEMODULE=${JSON.stringify(tideModule)},MODULES=${JSON.stringify(modules)},HARMONIC=${JSON.stringify(harmonic)};
const memo=new Map();
export default {async fetch(request,env,ctx){
 const u=new URL(request.url),path=u.pathname;
 if(path==='/clock.js')return new Response(${JSON.stringify(clockModule)},{headers:{'content-type':'text/javascript; charset=utf-8','cache-control':'no-cache'}});
 if(path==='/google-guard.js')return new Response(${JSON.stringify(googleGuard)},{headers:{'content-type':'text/javascript; charset=utf-8','cache-control':'no-cache'}});
 if(path==='/map-gestures.js')return new Response(${JSON.stringify(mapGestures)},{headers:{'content-type':'text/javascript; charset=utf-8','cache-control':'no-cache'}});
 if(path==='/api/map-config')return mapConfigResponse(env,request);
 if(path==='/site.webmanifest')return new Response(WEBMANIFEST,{headers:{'content-type':'application/manifest+json; charset=utf-8','cache-control':'no-cache'}});
 if(Object.hasOwn(ICONS,path)){const icon=ICONS[path];return new Response(Uint8Array.from(atob(icon.data),c=>c.charCodeAt(0)),{headers:{'content-type':icon.type,'cache-control':'public, max-age=86400','X-Content-Type-Options':'nosniff'}});}
 if(path==='/brand-logo.png')return new Response(Uint8Array.from(atob(LOGO),c=>c.charCodeAt(0)),{headers:{'content-type':'image/png','cache-control':'public, max-age=86400'}});
 if(path==='/tide.js')return new Response(TIDEMODULE,{headers:{'content-type':'text/javascript; charset=utf-8','cache-control':'no-cache'}});
 if(Object.hasOwn(MODULES,path))return new Response(MODULES[path],{headers:{'content-type':'text/javascript; charset=utf-8','cache-control':'no-cache'}});
 if(path.startsWith('/api/harmonic/'))return harmonicResponse(path,HARMONIC);

 if(path==='/coastal-map.json')return new Response(COASTALMAP,{headers:{'content-type':'application/json; charset=utf-8','cache-control':'public, max-age=3600'}});
 if(path==='/overview-map.json')return new Response(OVERVIEW,{headers:{'content-type':'application/json; charset=utf-8'}});
 if(path==='/overview-map.webp'){const str=atob(OVERVIEWMAP),bytes=Uint8Array.from(str,c=>c.charCodeAt(0));return new Response(bytes,{headers:{'content-type':'image/webp','cache-control':'public, max-age=3600'}});}
 if(path==='/coastal-map.webp'){const str=atob(MAP),bytes=Uint8Array.from(str,c=>c.charCodeAt(0));return new Response(bytes,{headers:{'content-type':'image/webp','cache-control':'public, max-age=3600'}});}
 if(path==='/api/current'||path==='/api/tide'){
  try{
   const date=u.searchParams.get('date')||'',hour=Number(u.searchParams.get('hour'));
   if(!validDate(date)||+date.slice(0,4)<1900||+date.slice(0,4)>2100||!Number.isInteger(hour)||hour<0||hour>23)return Response.json({error:'日付または時刻が不正です。'},{status:400});
   const station=u.searchParams.get('station')||'TK';if(path==='/api/tide'&&!TIDE_STATIONS[station])return Response.json({error:'対応していない潮位地点です。'},{status:400});
   const area=u.searchParams.get('area')||'01';if(path==='/api/current'&&!['01','03'].includes(area))return Response.json({error:'対応していない海域です。'},{status:400});
   const key=path+date+hour+(path==='/api/tide'?station:area);
   if(memo.has(key))return Response.json(memo.get(key));
   let result;
   if(path==='/api/current')result=(area==='01'&&SNAPSHOTS[date+'/'+hour])||await current(date,hour,area);
   else {const year=date.slice(0,4);const raw=year==='2026'&&TIDETABLES[station]?TIDETABLES[station]:await(await upstream('https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/'+year+'/'+station+'.txt')).text();result=parseTides(raw,date,station);}
   if(memo.size>100)memo.delete(memo.keys().next().value);memo.set(key,result);
   return Response.json(result,{headers:{'Cache-Control':'public, max-age=3600'}});
  }catch(e){return Response.json({error:e.message||'データを取得できません。'},{status:502});}
 }
 if(path==='/app.js')return new Response(JS,{headers:{'content-type':'text/javascript; charset=utf-8','cache-control':'no-cache'}});
 if(path==='/geometry.js')return new Response(GEO,{headers:{'content-type':'text/javascript; charset=utf-8','cache-control':'no-cache'}});
 if(path==='/coverage.js')return new Response(COVERAGE,{headers:{'content-type':'text/javascript; charset=utf-8','cache-control':'no-cache'}});
 if(path==='/chart.js')return new Response(CHART,{headers:{'content-type':'text/javascript; charset=utf-8','cache-control':'no-cache'}});
 if(path==='/app.css')return new Response(CSS,{headers:{'content-type':'text/css; charset=utf-8'}});
 if(path!=='/'&&path!=='/index.html')return new Response('Not found',{status:404});
 return new Response(HTML,{headers:{'content-type':'text/html; charset=utf-8','cache-control':'no-cache','X-Content-Type-Options':'nosniff','Referrer-Policy':'strict-origin-when-cross-origin'}});
}};`);
console.log('Built Worker ESM: dist/server/index.js',(fs.statSync('dist/server/index.js').size/1e6).toFixed(2)+' MB; harmonic grids: '+JSON.parse(harmonic.index).grids.map(g=>g.name+' '+g.wetCount+' cells').join(', '));
