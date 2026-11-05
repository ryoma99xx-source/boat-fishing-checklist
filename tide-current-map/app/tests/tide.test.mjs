import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {parseTides} from '../worker/api.js';
import {prepareTide,tideAt,tideMarkup,nearestTideStation} from '../tide.js';
const table=code=>fs.readFileSync(new URL('../data/'+code+'-2026.txt',import.meta.url),'utf8');
test('JMA extrema parse separate two-character hour/minute fields with embedded spaces',()=>{
 const tokyo=parseTides(table('TK'),'2026-10-24');assert.deepEqual(tokyo.events.map(e=>[e.type,e.time,e.height]),[['high','03:26',182],['low','09:37',66],['high','15:42',192],['low','22:03',44]]);assert.equal(tokyo.dayHours.length,25);assert.equal(tokyo.dayHours[24],80);
 const mera=parseTides(table('MR'),'2026-10-24','MR');assert.equal(mera.events[0].time,'03:01');assert.equal(mera.events[1].time,'09:02');assert.equal(mera.station,'布良');assert.throws(()=>parseTides(table('TK'),'2026-10-24','invalid'));
});
test('curve passes through official hourly values and published extrema without overshoot',()=>{
 for(const code of ['TK','Z1','MR']){const data=parseTides(table(code),'2026-10-24',code),g=prepareTide(data);data.dayHours.forEach((v,h)=>assert.ok(Math.abs(tideAt(g,h).height-v)<1e-8));for(const e of data.events){assert.ok(Math.abs(tideAt(g,e.hour).height-e.height)<1e-8);assert.ok(Math.abs(tideAt(g,e.hour).slope)<1e-7)}for(const points of g.segments)for(let i=0;i<points.length-1;i++)for(let j=0;j<=20;j++){const a=points[i],b=points[i+1],v=tideAt(g,a.x+(b.x-a.x)*j/20).height;assert.ok(v>=Math.min(a.y,b.y)-1e-8&&v<=Math.max(a.y,b.y)+1e-8);}}
});
test('missing hourly values remain a gap and are never extrapolated',()=>{const g=prepareTide({date:'2026-10-24',station:'東京',hours:[10,null,20,25],events:[]});assert.equal(tideAt(g,.5),null);assert.equal(tideAt(g,1.5),null);assert.equal(tideAt(g,4),null);assert.ok(tideAt(g,2.5));});
test('nearest reference station and selected-time SVG stay explicit',()=>{assert.equal(nearestTideStation({lat:35.65,lon:139.766667}),'TK');assert.equal(nearestTideStation({lat:35.279,lon:139.708}),'Z1');const g=prepareTide(parseTides(table('Z1'),'2026-10-24','Z1')),svg=tideMarkup(g,8.5,350,230,10);assert.match(svg,/08:30 選択/);assert.match(svg,/満 03:14/);assert.match(svg,/tide-now/);assert.doesNotMatch(svg,/NaN|undefined/);});
