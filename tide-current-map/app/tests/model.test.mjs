import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {facing,compass,relativeFlow,shapeBearing,distanceKm,chartCoordinate,tidePhase} from '../geometry.js';
import {parseTides,parseStations,validDate} from '../worker/api.js';
test('left seat and diagonal observation use nautical bearings',()=>{
 assert.equal(facing(337.5,'port'),247.5);assert.equal(compass(247.5),'西南西');
 assert.equal(relativeFlow(112.5,247.5,.7),'奥から手前へ、向かってくる');
 assert.equal(relativeFlow(247.5,247.5,.7),'手前から奥へ、払い出す向き');
 assert.equal(relativeFlow(337.5,247.5,.7),'正面を横切り、右へ流れる');
});
test('arrow digitization resolves the head for each quadrant',()=>{
 const points=[];for(let y=-15;y<=15;y++)for(let x=-8;x<=8;x++)if((y<2&&Math.abs(x)<=2)||(y>=0&&Math.abs(x)<=8*(15-y)/15))points.push([x,y]);
 for(const angle of [0,45,90,135,180,225,270,315]){const a=angle*Math.PI/180,rot=points.map(([x,y])=>[x*Math.cos(a)-y*Math.sin(a),x*Math.sin(a)+y*Math.cos(a)]);const expected=(180+angle)%360,actual=shapeBearing(rot);const diff=Math.abs(((actual-expected+540)%360)-180);assert.ok(diff<1,`${actual} vs ${expected}`);}
});
test('chart graticule maps known coordinates correctly',()=>{assert.deepEqual(chartCoordinate(30,631),{lat:35,lon:139.5});assert.ok(Math.abs(chartCoordinate(367.5,71).lon-140)<1e-9);});
test('JMA fixed-width values keep date, sign and hourly alignment',()=>{const raw=fs.readFileSync('data/TK-2026.txt','utf8');const d=parseTides(raw,'2026-10-24');assert.equal(d.hours.length,24);assert.equal(d.hours[8],85);assert.equal(d.hours[10],67);assert.equal(d.hours[16],191);assert.equal(tidePhase(d.hours,8),'潮位は下降中');assert.equal(tidePhase(d.hours,12),'潮位は上昇中');assert.throws(()=>parseTides(raw,'2027-01-01'));});
test('bad dates do not silently roll over',()=>{assert.equal(validDate('2026-02-30'),false);assert.equal(validDate('2026-10-24'),true);assert.equal(validDate('2026-99-99'),false);});
test('official station parsing retains the speed and location',()=>{const s=parseStations('<AREA coords=190,395,10 ALT="1.1kn." TITLE="1.1kn." shape=CIRCLE>');assert.equal(s.length,1);assert.equal(s[0].speed,1.1);assert.ok(s[0].lon>139.73&&s[0].lon<139.74);});
test('observation-day snapshots are actual sparse source points',()=>{for(const h of [8,9,10,11,12]){const d=JSON.parse(fs.readFileSync(`data/current-20261024-${h}.json`));assert.equal(d.stations.length,41);assert.equal(d.hour,h);assert.ok(d.image.startsWith('data:image/png;base64,iVBOR'));const nearest=d.stations.reduce((a,b)=>distanceKm({lat:35.279,lon:139.708},a)<distanceKm({lat:35.279,lon:139.708},b)?a:b);assert.ok(distanceKm({lat:35.279,lon:139.708},nearest)>2);}});
