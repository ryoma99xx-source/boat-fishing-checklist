import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as geometry from '../geometry.js';
import * as coastal from '../coastal.js';
import * as experiment from '../experiment.js';
import * as coverage from '../coverage.js';
import * as tide from '../tide.js';
import * as clock from '../clock.js';
import * as mapGestures from '../map-gestures.js';
import {parseTides} from '../worker/api.js';
const meta=JSON.parse(fs.readFileSync(new URL('../data/tidal-case.json',import.meta.url)));
const frames=fs.readFileSync(new URL('../data/tidal-frames.bin',import.meta.url));
const source=fs.readFileSync(new URL('../app.js',import.meta.url),'utf8').replace(/^import .*;\n/gm,'');
function setup(stall,now=Date.parse('2026-10-23T23:30:00Z')){
 class FixedDate extends Date {constructor(...args){super(...(args.length?args:[now]));}static now(){return now;}}
 const elements=new Map(),timers=new Set(),requests=[];const classes=()=>{const values=new Set();return {toggle(k,on){const active=on===undefined?!values.has(k):on;active?values.add(k):values.delete(k);return active},add(k){values.add(k)},remove(k){values.delete(k)},contains(k){return values.has(k)}}};
 const canvas=new Proxy({measureText:()=>({width:80})},{get:(o,k)=>o[k]??(()=>{})});
 const element=id=>{if(!elements.has(id))elements.set(id,{textContent:'',hidden:id==='experimentMode',value:id==='heading'?'337.5':id==='seat'?'port':'',style:{},classList:classes(),clientWidth:390,clientHeight:500,getContext:()=>canvas,addEventListener(){},setAttribute(k,v){this[k]=v},getAttribute(k){return this[k]},getBoundingClientRect:()=>({left:0,top:0,width:390,height:500}),replaceChildren(){},scrollIntoView(){}});return elements.get(id)};
 const fetch=async(url,options={})=>{
  requests.push(url);
  if(stall(url))return new Promise((resolve,reject)=>{options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')),{once:true})});
  const u=new URL(url,'http://local');
  if(u.pathname==='/api/map-config')return Response.json({provider:'standard'});
  if(u.pathname==='/api/current'){const data=JSON.parse(fs.readFileSync(new URL('../data/current-20261024-8.json',import.meta.url)));data.date=u.searchParams.get('date');data.hour=Number(u.searchParams.get('hour'));return Response.json(data);}
  if(u.pathname==='/api/tide'){const code=u.searchParams.get('station');return Response.json(parseTides(fs.readFileSync(new URL('../data/'+code+'-2026.txt',import.meta.url),'utf8'),u.searchParams.get('date'),code));}
  if(u.pathname==='/api/experiment/frame'){const size=meta.wetIds.length*4,i=Number(u.searchParams.get('index'));return new Response(frames.subarray(i*size,(i+1)*size),{headers:{'content-type':'application/octet-stream'}})}
  const path=u.pathname==='/api/experiment/meta'?'tidal-case.json':u.pathname==='/api/coastal-model'?'coastal-model.json':u.pathname==='/overview-map.json'?'overview-map.json':'current-'+u.searchParams.get('date').replaceAll('-','')+'-'+u.searchParams.get('hour')+'.json';
  return new Response(fs.readFileSync(new URL('../data/'+path,import.meta.url)),{headers:{'content-type':'application/json'}});
 };
 const context=vm.createContext({...geometry,...coastal,...experiment,...coverage,...tide,...clock,...mapGestures,Date:FixedDate,extract:async d=>({...d,stations:d.stations.map(s=>({...s,bearing:180}))}),fetch,AbortController,URL,Int16Array,Int32Array,console,devicePixelRatio:1,document:{getElementById:element,querySelectorAll:()=>[],addEventListener(){},body:{classList:classes()},head:{append(){}},createElement:()=>element('created')},window:{},localStorage:{getItem:()=>null},sessionStorage:{getItem:()=>null},Image:class{},ResizeObserver:class{observe(){}},setTimeout:(fn,ms)=>{const t=setTimeout(()=>{timers.delete(t);fn()},ms===15000?60:ms===30000?120:ms===4500?50:ms);timers.add(t);return t},clearTimeout:t=>{clearTimeout(t);timers.delete(t)}});
 vm.runInContext(source,context);return {element,requests,close(){for(const t of timers)clearTimeout(t)}};
}
async function until(predicate){const end=Date.now()+1500;while(!predicate()){if(Date.now()>end)throw Error('Condition not met');await new Promise(r=>setTimeout(r,5))}}

test('stalled offshore startup cannot block the independent regional experiment',async()=>{const h=setup(url=>url.startsWith('/api/current'));try{await until(()=>h.element('status').textContent.includes('10/24 潮汐試験'));assert.equal(h.element('coastalMode').classList.contains('active'),true);assert.match(h.element('modelMethod').textContent,/250m/);assert.match(h.element('peekFlow').textContent,/kn/)}finally{h.close()}});

test('stalled basemap and coastal metadata cannot block regional results',async()=>{const h=setup(url=>url==='/api/coastal-model'||url==='/overview-map.json');try{await until(()=>h.element('status').textContent.includes('10/24 潮汐試験'));assert.match(h.element('peekFlow').textContent,/kn/)}finally{h.close()}});

test('a stalled time frame times out and can be retried without showing stale flow',async()=>{let blocked=true;const h=setup(url=>blocked&&url.startsWith('/api/experiment/frame?index=18'));try{await until(()=>h.element('status').textContent.includes('10/24 潮汐試験'));h.element('play').onclick();await until(()=>h.element('status').textContent.includes('取得失敗'));assert.match(h.element('status').textContent,/タップで再取得/);assert.equal(h.element('speed').textContent,'—');assert.match(h.element('peekFlow').textContent,/取得できません/);assert.equal(h.element('play').getAttribute('aria-label'),'時間を再生');blocked=false;h.element('status').onclick();await until(()=>h.element('status').textContent.includes('10/24 潮汐試験'));assert.equal(h.element('time').textContent,'09:00');assert.match(h.element('peekFlow').textContent,/kn/)}finally{h.close()}});

function chooseDate(h,date){const input=h.element('date');input.value=date;input.onchange({target:input});}
test('one model entry selects the dated case, then the current-date reference without resetting the date',async()=>{
 const h=setup(()=>false);try{await until(()=>h.element('status').textContent.includes('10/24 潮汐試験'));assert.equal(h.element('date').disabled,false);
 chooseDate(h,'2026-10-25');await until(()=>h.element('status').textContent.includes('沿岸参考モデル'));assert.match(h.element('modelMethod').textContent,/100m/);assert.equal(h.element('coastalMode').classList.contains('active'),true);assert.match(h.element('peekFlow').textContent,/kn/);assert.ok(h.requests.some(u=>u.includes('/api/current?date=2026-10-25')));
 h.element('caseDate').onclick();await until(()=>h.element('status').textContent.includes('10/24 潮汐試験'));assert.equal(h.element('date').value,'2026-10-24');assert.match(h.element('modelMethod').textContent,/250m/);
 }finally{h.close()}
});
test('unavailable dated case does not silently fall back to the other calculation',async()=>{
 const h=setup(u=>u==='/api/experiment/meta');try{await until(()=>h.element('status').textContent.includes('取得失敗'));assert.equal(h.element('speed').textContent,'—');assert.equal(h.requests.some(u=>u.startsWith('/api/current')),false);assert.match(h.element('modelMethod').textContent,/250m/);
 chooseDate(h,'2026-10-25');await until(()=>h.element('status').textContent.includes('沿岸参考モデル'));assert.match(h.element('modelMethod').textContent,/100m/);
 }finally{h.close()}
});
test('late case metadata cannot reverse a date change',async()=>{
 const h=setup(u=>u==='/api/experiment/meta');try{chooseDate(h,'2026-10-25');await until(()=>h.element('status').textContent.includes('沿岸参考モデル'));await new Promise(r=>setTimeout(r,100));assert.equal(h.element('date').value,'2026-10-25');assert.match(h.element('modelMethod').textContent,/100m/);assert.equal(h.element('coastalMode').classList.contains('active'),true);}finally{h.close()}
});

test('operator map configuration cannot block current data',async()=>{const h=setup(u=>u==='/api/map-config');try{await until(()=>h.element('status').textContent.includes('10/24 潮汐試験'));assert.match(h.element('peekFlow').textContent,/kn/);}finally{h.close()}});

test('fresh access uses the Japanese date even while the dated case exists',async()=>{const h=setup(()=>false,Date.parse('2026-10-26T15:30:00Z'));try{await until(()=>h.element('status').textContent.includes('沿岸参考モデル'));assert.equal(h.element('date').value,'2026-10-27');assert.equal(h.element('time').textContent,'00:30');assert.ok(h.requests.some(u=>u.startsWith('/api/current?date=2026-10-27')));assert.equal(h.requests.some(u=>u==='/api/experiment/meta'),false);}finally{h.close()}});
