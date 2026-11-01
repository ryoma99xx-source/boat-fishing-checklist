import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gzipSync,gunzipSync} from 'node:zlib';
import {frameResponse} from '../worker/frame.js';
const meta=JSON.parse(fs.readFileSync(new URL('../data/tidal-case.json',import.meta.url)));
const frames=fs.readFileSync(new URL('../data/tidal-frames.bin',import.meta.url));
test('all stored frames reach hosting as original bytes, with compression owned by hosting',async()=>{
 const size=meta.wetIds.length*4;
 for(let i=0;i<meta.frameCount;i++){
  const original=frames.subarray(i*size,(i+1)*size),response=frameResponse(gzipSync(original).toString('base64'));
  assert.equal(response.headers.get('content-encoding'),null);
  const bytes=Buffer.from(await response.arrayBuffer());assert.equal(bytes.length,size);assert.deepEqual(bytes,original);
  // A hosting proxy may add gzip; one HTTP decompression must restore the actual frame.
  assert.deepEqual(gunzipSync(gzipSync(bytes)),original);
 }
});
