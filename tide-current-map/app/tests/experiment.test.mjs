import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {prepareExperiment,sampleExperiment} from '../experiment.js';

test('regional experiment respects land, shallow cells and its rectangular grid',()=>{
 const meta=prepareExperiment({nx:5,ny:4,lat0:35,lon0:139,dlat:.01,dlon:.01,dx:250,wetIds:[6,7,8,11,12,13],mask:[0,0,0,0,0,0,1,1,1,0,0,1,1,1,2,0,0,0,0,0],velocityScale:.001,depth:[10,20,30,40,50,60],shore:[250,500,750,250,500,750],ne:[1,1,1,1,1,1],nn:[0,0,0,0,0,0]});
 const vector=new Int16Array([514,0,0,514,-514,0,0,-514,0,0,100,100]);
 const east=sampleExperiment(meta,vector,35.01,139.01);assert.equal(east.bearing,90);assert.ok(Math.abs(east.speed-1)<.002);assert.equal(east.depth,10);assert.equal(east.cellSize,250);
 assert.equal(sampleExperiment(meta,vector,35.01,139.03).bearing,270);
 assert.equal(sampleExperiment(meta,vector,35.02,139.01).bearing,180);
 assert.equal(sampleExperiment(meta,null,35.01,139.01).reason,'loading');
 assert.equal(sampleExperiment(meta,vector,34,139).reason,'outside');
 assert.equal(sampleExperiment(meta,vector,35.01,139.00).reason,'outside');
});

// The old 10/24 case data is left out of the slim deployment package; check it only when present.
test('saved tidal case has complete, finite half-hour fields and covers requested offshore sites',{skip:!fs.existsSync(new URL('../data/tidal-frames.bin',import.meta.url))},()=>{
 const g=prepareExperiment(JSON.parse(fs.readFileSync('data/tidal-case.json'))),bytes=fs.readFileSync('data/tidal-frames.bin');
 assert.equal(g.frameCount,49);assert.equal(bytes.byteLength,g.frameCount*g.wetIds.length*4);assert.ok(g.report.maxMassResidualM<1e-8);
 for(const slot of [17,22,24]){const offset=slot*g.wetIds.length*4,copy=Uint8Array.from(bytes.subarray(offset,offset+g.wetIds.length*4));const vector=new Int16Array(copy.buffer);for(const [lat,lon]of [[35.279,139.708],[35.113,139.805],[35.13,139.615],[35.61,139.9]]){const flow=sampleExperiment(g,vector,lat,lon);assert.ok(Number.isFinite(flow.speed),JSON.stringify({lat,lon,flow}));assert.ok(flow.depth>=3);}}
});
