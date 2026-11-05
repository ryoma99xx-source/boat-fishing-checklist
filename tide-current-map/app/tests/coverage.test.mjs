import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {VIEW_AREA,REGIONS,contains,modelBounds,fitArea} from '../coverage.js';
import {cellAt} from '../coastal.js';
const g=JSON.parse(fs.readFileSync('data/coastal-model.json'));
test('viewing area includes Tokyo Bay head, Katsuyama, Misaki and Miura west coast',()=>{for(const p of Object.values(REGIONS))assert.equal(contains(VIEW_AREA,p),true,p.name);assert.equal(contains(VIEW_AREA,{lat:35.69,lon:140.05}),true);assert.equal(contains(VIEW_AREA,{lat:35.1384,lon:139.6184}),true);assert.equal(contains(VIEW_AREA,{lat:35.111,lon:139.8295}),true);});
test('new viewing area does not claim local predictions exist at Katsuyama or Misaki',()=>{for(const key of ['katsuyama','misaki']){assert.equal(contains(modelBounds(g),REGIONS[key]),false);assert.equal(cellAt(g,REGIONS[key].lat,REGIONS[key].lon).reason,'outside');}});
test('full-area fit includes all four corners on phone and desktop',()=>{
 const world=(lat,lon,z)=>{const s=Math.sin(lat*Math.PI/180),n=256*2**z;return {x:(lon+180)/360*n,y:(.5-Math.log((1+s)/(1-s))/(4*Math.PI))*n};};
 for(const [w,h]of [[374,520],[1030,675]]){const view=fitArea(VIEW_AREA,w,h,44),c=world(view.center.lat,view.center.lon,view.zoom);for(const lat of [VIEW_AREA.south,VIEW_AREA.north])for(const lon of [VIEW_AREA.west,VIEW_AREA.east]){const p=world(lat,lon,view.zoom);assert.ok(Math.abs(p.x-c.x)<w/2-40);assert.ok(Math.abs(p.y-c.y)<h/2-40);}}
});
test('locations outside the displayed envelope are explicitly outside',()=>{assert.equal(contains(VIEW_AREA,{lat:34.7,lon:139.8}),false);assert.equal(contains(VIEW_AREA,{lat:35.4,lon:141.2}),false);assert.equal(contains(VIEW_AREA,{lat:36.3,lon:140.6}),false);assert.equal(contains(VIEW_AREA,{lat:34.95,lon:139.85}),true);assert.equal(contains(VIEW_AREA,{lat:35.7,lon:140.9}),true);assert.equal(contains(VIEW_AREA,{lat:NaN,lon:139.8}),false);});
