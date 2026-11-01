import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as geometry from '../geometry.js';
import * as coverage from '../coverage.js';
import * as tide from '../tide.js';
import * as clock from '../clock.js';
import * as mapGestures from '../map-gestures.js';
import * as currents from '../currents.js';
import * as spots from '../spots.js';
import * as flowLayer from '../flow-layer.js';
import {parseTides} from '../worker/api.js';
import {packHarmonic} from '../worker/harmonic-build.mjs';
import {harmonicResponse} from '../worker/harmonic.js';
import {frameResponse} from '../worker/frame.js';
const harmonic=packHarmonic(new URL('../data',import.meta.url).pathname);
const coastalMap=JSON.parse(fs.readFileSync(new URL('../data/coastal-model.json',import.meta.url))).map;
const source=fs.readFileSync(new URL('../app.js',import.meta.url),'utf8').replace(/^import .*;\n/gm,'');
function setup(stall,now=Date.parse('2026-10-23T23:30:00Z')){
 class FixedDate extends Date {constructor(...args){super(...(args.length?args:[now]));}static now(){return now;}}
 const elements=new Map(),timers=new Set(),requests=[];const classes=()=>{const values=new Set();return {toggle(k,on){const active=on===undefined?!values.has(k):on;active?values.add(k):values.delete(k);return active},add(k){values.add(k)},remove(k){values.delete(k)},contains(k){return values.has(k)}}};
 const canvas=new Proxy({measureText:()=>({width:80})},{get:(o,k)=>o[k]??(()=>{})});
 const element=id=>{if(!elements.has(id))elements.set(id,{textContent:'',innerHTML:'',hidden:false,value:id==='heading'?'337.5':id==='seat'?'port':'',style:{},classList:classes(),clientWidth:390,clientHeight:500,getContext:()=>canvas,addEventListener(){},setAttribute(k,v){this[k]=v},getAttribute(k){return this[k]},getBoundingClientRect:()=>({left:0,top:0,width:390,height:500}),replaceChildren(){},scrollIntoView(){}});return elements.get(id)};
 const fetch=async(url,options={})=>{
  requests.push(url);
  if(stall(url))return new Promise((resolve,reject)=>{options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')),{once:true})});
  const u=new URL(url,'http://local');
  if(u.pathname==='/api/map-config')return Response.json({provider:'standard'});
  if(u.pathname.startsWith('/api/harmonic/'))return harmonicResponse(u.pathname,harmonic,frameResponse);
  if(u.pathname==='/coastal-map.json')return Response.json(coastalMap);
  if(u.pathname==='/api/current'){const data=JSON.parse(fs.readFileSync(new URL('../data/current-20261024-8.json',import.meta.url)));data.date=u.searchParams.get('date');data.hour=Number(u.searchParams.get('hour'));return Response.json(data);}
  if(u.pathname==='/api/tide'){const code=u.searchParams.get('station');return Response.json(parseTides(fs.readFileSync(new URL('../data/'+code+'-2026.txt',import.meta.url),'utf8'),u.searchParams.get('date'),code));}
  if(u.pathname==='/overview-map.json')return new Response(fs.readFileSync(new URL('../data/overview-map.json',import.meta.url)),{headers:{'content-type':'application/json'}});
  return new Response('Not found',{status:404});
 };
 const context=vm.createContext({...geometry,...coverage,...tide,...clock,...mapGestures,...currents,...spots,...flowLayer,Date:FixedDate,extract:async d=>({...d,stations:d.stations.map(s=>({...s,bearing:180}))}),fetch,AbortController,URL,Int16Array,Int32Array,Uint16Array,console,devicePixelRatio:1,document:{getElementById:element,querySelectorAll:()=>[],addEventListener(){},body:{classList:classes()},head:{append(){}},createElement:()=>element('created')},window:{},localStorage:{getItem:()=>null},sessionStorage:{getItem:()=>null},Image:class{},ResizeObserver:class{observe(){}},setTimeout:(fn,ms)=>{const t=setTimeout(()=>{timers.delete(t);fn()},ms===15000?60:ms===30000?120:ms===4500?50:ms);timers.add(t);return t},clearTimeout:t=>{clearTimeout(t);timers.delete(t)}});
 vm.runInContext(source,context);return {element,requests,context,close(){for(const t of timers)clearTimeout(t)}};
}
async function until(predicate){const end=Date.now()+3000;while(!predicate()){if(Date.now()>end)throw Error('Condition not met');await new Promise(r=>setTimeout(r,5))}}
const ready=h=>h.element('status').textContent.includes('潮流モデル（');
function chooseDate(h,date){const input=h.element('date');input.value=date;input.onchange({target:input});}

test('stalled offshore startup cannot block the harmonic model',async()=>{const h=setup(url=>url.startsWith('/api/current'));try{await until(()=>ready(h));assert.equal(h.element('coastalMode').classList.contains('active'),true);assert.match(h.element('modelMethod').textContent,/250m/);assert.match(h.element('peekFlow').textContent,/kt/);assert.match(h.element('speedUnit').textContent,/モデル/);assert.equal(h.requests.some(u=>u.startsWith('/api/current')),false)}finally{h.close()}});

test('stalled basemap metadata cannot block model results',async()=>{const h=setup(url=>url==='/coastal-map.json'||url==='/overview-map.json');try{await until(()=>ready(h));assert.match(h.element('peekFlow').textContent,/kt/)}finally{h.close()}});

test('stalled model data times out, shows no value, and can be retried',async()=>{let blocked=true;const h=setup(url=>blocked&&/\/api\/harmonic\/outer-[0-9a-f]+\.bin$/.test(url));try{await until(()=>h.element('status').textContent.includes('取得失敗'));assert.match(h.element('status').textContent,/タップで再取得/);assert.equal(h.element('speed').textContent,'—');assert.match(h.element('peekFlow').textContent,/取得できません/);assert.equal(h.requests.some(u=>u.startsWith('/api/current')),false);blocked=false;h.element('status').onclick();await until(()=>ready(h));assert.match(h.element('peekFlow').textContent,/kt/)}finally{h.close()}});

test('any date uses the same model; the 10/24 shortcut sets the case date and 8:30',async()=>{
 const h=setup(()=>false);try{await until(()=>ready(h));assert.equal(h.element('date').value,'2026-10-24');
 const before=h.element('peekFlow').textContent;
 chooseDate(h,'2026-12-15');await until(()=>ready(h)&&h.element('date').value==='2026-12-15');assert.match(h.element('modelMethod').textContent,/調和モデル/);assert.match(h.element('peekFlow').textContent,/kt/);assert.equal(h.requests.some(u=>u.startsWith('/api/current')),false);
 assert.equal(h.requests.filter(u=>u==='/api/harmonic/index.json').length,1);
 h.element('caseDate').onclick();await until(()=>ready(h)&&h.element('date').value==='2026-10-24');assert.equal(h.element('time').textContent,'08:30');assert.equal(h.element('peekFlow').textContent,before);
 }finally{h.close()}
});
test('unavailable model data does not fall back to another calculation',async()=>{
 const h=setup(u=>u==='/api/harmonic/index.json');try{await until(()=>h.element('status').textContent.includes('取得失敗'));assert.equal(h.element('speed').textContent,'—');assert.equal(h.requests.some(u=>u.startsWith('/api/current')),false);
 chooseDate(h,'2026-10-25');await new Promise(r=>setTimeout(r,150));assert.equal(h.element('date').value,'2026-10-25');assert.equal(h.element('speed').textContent,'—');
 }finally{h.close()}
});
test('time shortcuts and the slider keep the selected date and resynthesize',async()=>{
 const h=setup(()=>false);try{await until(()=>ready(h));chooseDate(h,'2026-11-05');await until(()=>h.element('date').value==='2026-11-05'&&ready(h));
 h.element('slider').oninput({target:{value:'30'}});await until(()=>h.element('time').textContent==='15:00'&&ready(h));assert.equal(h.element('date').value,'2026-11-05');assert.match(h.element('peekFlow').textContent,/kt/);
 }finally{h.close()}
});
test('official mode still reads the offshore stations',async()=>{const h=setup(()=>false);try{await until(()=>ready(h));h.element('officialMode').onclick();await until(()=>h.element('status').textContent.includes('公式推算'));assert.match(h.element('peekFlow').textContent,/kn/);h.element('coastalMode').onclick();await until(()=>ready(h));}finally{h.close()}});

test('operator map configuration cannot block current data',async()=>{const h=setup(u=>u==='/api/map-config');try{await until(()=>ready(h));assert.match(h.element('peekFlow').textContent,/kt/);}finally{h.close()}});

test('fresh access uses the Japanese date',async()=>{const h=setup(()=>false,Date.parse('2026-10-26T15:30:00Z'));try{await until(()=>ready(h));assert.equal(h.element('date').value,'2026-10-27');assert.equal(h.element('time').textContent,'00:30');assert.equal(h.requests.some(u=>u.startsWith('/api/current')),false);}finally{h.close()}});
