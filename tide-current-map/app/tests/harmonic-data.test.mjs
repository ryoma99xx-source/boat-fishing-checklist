import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gzipSync, gunzipSync} from 'node:zlib';
import {MPS_TO_KT, encodeRuns, decodeRuns, prepareGrid, updateField, velocityInGrid, velocityAt, sampleCurrents, jstSlotTime, gridFor, inflate, isGzip, canInflate} from '../currents.js';
import {synthesizeCell} from '../harmonic.js';
import {packGrid, packHarmonic, depthBytes, GRID_ORDER} from '../worker/harmonic-build.mjs';
import {harmonicResponse} from '../worker/harmonic.js';
import {frameResponse} from '../worker/frame.js';
import {SPOTS, REFERENCE_POINTS} from '../spots.js';
import {screenSpeed, particleCount, speedColor} from '../flow-layer.js';

const dataUrl = name => new URL('../data/' + name, import.meta.url);
const CONST = {constituents: ['M2'], doodson: [[2, 0, 0, 0, 0, 0]], phaseOffsetDeg: [0], nodal: ['one']};

// Synthetic grid: constant mean flow per cell (mm/s), harmonic amplitudes zero.
function synthetic({nx, ny, lat0, lon0, dlat, dlon, dxM, name, wet, flow}) {
 const ids = wet.slice().sort((a, b) => a - b), coef = new Int16Array(ids.length * 6);
 ids.forEach((id, i) => { const [u, v] = flow(id % nx, Math.floor(id / nx)); coef[i * 6] = u; coef[i * 6 + 1] = v; });
 const meta = {name, nx, ny, lat0, lon0, dlat, dlon, dxM, ...CONST, wetRuns: encodeRuns(ids), wetCount: ids.length};
 const g = prepareGrid(meta, coef, Uint16Array.from(ids, () => 123));
 updateField(g, Date.UTC(2026, 9, 24));
 return g;
}
const all = (nx, ny) => Array.from({length: nx * ny}, (_, i) => i);

test('compact wet-cell runs decode to the original ids', () => {
 const ids = [0, 1, 2, 5, 9, 10, 11, 12, 40];
 const runs = encodeRuns(ids);
 assert.deepEqual(runs, [0, 3, 5, 1, 9, 4, 40, 1]);
 assert.deepEqual([...decodeRuns(runs, ids.length)], ids);
 assert.throws(() => decodeRuns(runs, ids.length + 1));
 const meta = JSON.parse(fs.readFileSync(dataUrl('harmonic-outer.json')));
 assert.deepEqual([...decodeRuns(encodeRuns(meta.wetIds), meta.wetIds.length)], meta.wetIds);
});

test('bilinear sampling inside a grid and knot conversion', () => {
 // u = 100*x mm/s, v = -50 mm/s
 const g = synthetic({nx: 4, ny: 4, lat0: 35, lon0: 139, dlat: .01, dlon: .01, dxM: 1000, name: 'outer', wet: all(4, 4), flow: x => [100 * x, -50]});
 const at = velocityInGrid(g, 35.015, 139.0125);
 assert.ok(Math.abs(at[0] - .125) < 1e-6, at[0]);
 assert.ok(Math.abs(at[1] + .05) < 1e-6);
 const s = sampleCurrents([g], 35.02, 139.02);
 assert.ok(Math.abs(s.speedMps - Math.hypot(.2, .05)) < 1e-6);
 assert.ok(Math.abs(s.speed - s.speedMps * 1.94384) < 1e-9);
 assert.equal(MPS_TO_KT, 1.94384);
 assert.ok(Math.abs(s.bearing - (90 + Math.atan2(.05, .2) * 180 / Math.PI)) < 1e-4);
 assert.equal(s.depth, 12.3);
});

test('land and outside never receive a value; dry corners are not mixed in', () => {
 // column x=3 is land
 const wet = all(4, 4).filter(i => i % 4 !== 3);
 const g = synthetic({nx: 4, ny: 4, lat0: 35, lon0: 139, dlat: .01, dlon: .01, dxM: 1000, name: 'outer', wet, flow: () => [300, 0]});
 assert.equal(sampleCurrents([g], 35.01, 139.03).reason, 'land');
 assert.equal(velocityAt([g], 35.01, 139.03), null);
 assert.equal(sampleCurrents([g], 35.5, 139.5).reason, 'outside');
 assert.equal(sampleCurrents([g], 34.9, 139.01).reason, 'outside');
 assert.equal(sampleCurrents([], 35.01, 139.01).reason, 'loading');
 // Point between a wet (x=2) and dry (x=3) cell, nearest wet: uses only wet corners, no zero dilution.
 const near = velocityInGrid(g, 35.01, 139.024);
 assert.ok(Math.abs(near[0] - .3) < 1e-6);
});

test('inner 50 m grid has priority; inner land stays land; outer used elsewhere', () => {
 const outer = synthetic({nx: 10, ny: 10, lat0: 35, lon0: 139, dlat: .01, dlon: .01, dxM: 250, name: 'outer', wet: all(10, 10), flow: () => [100, 0]});
 const innerWet = all(10, 10).filter(i => i !== 55);
 const inner = synthetic({nx: 10, ny: 10, lat0: 35.04, lon0: 139.04, dlat: .001, dlon: .001, dxM: 50, name: 'inner', wet: innerWet, flow: () => [0, 200]});
 const grids = [inner, outer];
 const a = sampleCurrents(grids, 35.042, 139.042);
 assert.equal(a.grid, 'inner'); assert.equal(a.cellSize, 50); assert.ok(Math.abs(a.vMps - .2) < 1e-6);
 const land = sampleCurrents(grids, 35.045, 139.045);
 assert.equal(land.reason, 'land'); assert.equal(land.grid, 'inner');
 const b = sampleCurrents(grids, 35.08, 139.08);
 assert.equal(b.grid, 'outer'); assert.ok(Math.abs(b.uMps - .1) < 1e-6);
 assert.equal(gridFor(grids, 36, 140), null);
 // without the inner grid, the outer grid alone answers
 assert.equal(sampleCurrents([outer], 35.042, 139.042).grid, 'outer');
});

test('JST date and half-hour slot map to the right instant', () => {
 assert.equal(jstSlotTime('2026-10-24', 17), Date.parse('2026-10-23T23:30:00Z'));
 assert.equal(jstSlotTime('2026-11-02', 0), Date.parse('2026-11-01T15:00:00Z'));
 assert.equal(jstSlotTime('2026-11-01', 48), jstSlotTime('2026-11-02', 0));
});

test('real outer grid: synthesis matches the per-cell reference and covers the Yokosuka reference points', () => {
 const meta = JSON.parse(fs.readFileSync(dataUrl('harmonic-outer.json'))), raw = fs.readFileSync(dataUrl('harmonic-outer.bin'));
 const coef = new Int16Array(Uint8Array.from(raw).buffer);
 const packed = packGrid(meta, raw, 'outer'), served = JSON.parse(packed.files[packed.entry.meta].text);
 assert.equal(served.wetIds, undefined); assert.equal(served.depth, undefined);
 const g = prepareGrid(served, coef, new Uint16Array(Uint8Array.from(depthBytes(meta.depth)).buffer));
 const ms = jstSlotTime('2026-10-24', 17); updateField(g, ms);
 for (const i of [0, 1234, meta.wetIds.length - 1]) {
  const [u, v] = synthesizeCell(meta, coef, i, ms);
  assert.ok(Math.abs(g.field[2 * i] - u) < 1e-6 && Math.abs(g.field[2 * i + 1] - v) < 1e-6);
 }
 for (const p of [...REFERENCE_POINTS, {name: 'observation', lat: 35.279, lon: 139.708}]) {
  if (!gridFor([g], p.lat, p.lon)) continue; // Boso points lie outside the bay grid
  const s = sampleCurrents([g], p.lat, p.lon);
  assert.ok(Number.isFinite(s.speed), p.name + ' ' + JSON.stringify(s));
 }
 assert.equal(sampleCurrents([g], 35.33, 139.62).reason, 'land'); // inland Yokohama/Yokosuka
});

test('fishing spot placeholders are drawn on water in the outer model (vertices) and are labelled as provisional', () => {
 const meta = JSON.parse(fs.readFileSync(dataUrl('harmonic-outer.json')));
 const g = synthetic({...meta, name: 'outer', wet: meta.wetIds, flow: () => [0, 0]});
 for (const spot of SPOTS) {
  assert.match(spot.label, /（仮）$/);
  assert.ok(spot.polygon.length >= 5 && spot.polygon.length <= 8);
  const wet = spot.polygon.filter(([lat, lon]) => sampleCurrents([g], lat, lon).reason !== 'land').length;
  assert.ok(wet >= spot.polygon.length - 2, spot.label + ' wet vertices ' + wet); // 250 m mask is coarse near islands
 }
});

test('served harmonic bytes equal the source bytes, with compression left to hosting', async () => {
 const bundle = packHarmonic(new URL('../data', import.meta.url).pathname);
 const index = JSON.parse(bundle.index);
 assert.ok(index.grids.length >= 1);
 assert.equal(index.grids.at(-1).name, GRID_ORDER.filter(n => fs.existsSync(dataUrl(`harmonic-${n}.json`))).at(-1));
 const res = harmonicResponse('/api/harmonic/index.json', bundle, frameResponse);
 assert.equal(res.headers.get('cache-control'), 'no-cache');
 for (const e of index.grids) {
  const source = fs.readFileSync(dataUrl(`harmonic-${e.name}.bin`)), meta = JSON.parse(fs.readFileSync(dataUrl(`harmonic-${e.name}.json`)));
  assert.match(e.coef, /^\/api\/harmonic\/[a-z]+-[0-9a-f]{12}\.bin$/);
  const r = harmonicResponse(e.coef, bundle, frameResponse);
  assert.equal(r.headers.get('content-encoding'), null);
  assert.match(r.headers.get('cache-control'), /immutable/);
  const bytes = Buffer.from(await r.arrayBuffer());
  assert.equal(bytes.length, e.coefBytes); assert.deepEqual(bytes, source);
  assert.deepEqual(gunzipSync(gzipSync(bytes)), source);
  const depth = Buffer.from(await harmonicResponse(e.depth, bundle, frameResponse).arrayBuffer());
  assert.deepEqual(depth, depthBytes(meta.depth));
  const servedMeta = await harmonicResponse(e.meta, bundle, frameResponse).json();
  assert.deepEqual([...decodeRuns(servedMeta.wetRuns, servedMeta.wetCount)], meta.wetIds);
 }
 assert.equal(harmonicResponse('/api/harmonic/outer-000000000000.bin', bundle, frameResponse).status, 404);
 assert.equal(harmonicResponse('/api/other', bundle, frameResponse), null);
});

test('content hash changes when the coefficients change', () => {
 const meta = {name: 'x', nx: 2, ny: 1, lat0: 35, lon0: 139, dlat: .01, dlon: .01, dxM: 50, ...CONST, wetIds: [0, 1], depth: [5, 6]};
 const a = packGrid(meta, Buffer.alloc(24), 'inner'), b = packGrid(meta, Buffer.alloc(24, 1), 'inner');
 assert.notEqual(a.entry.coef, b.entry.coef);
 assert.throws(() => packGrid(meta, Buffer.alloc(10), 'inner'), /bin length/);
 assert.throws(() => packGrid({...meta, wetIds: [1, 0]}, Buffer.alloc(24), 'inner'), /ascend/);
});

test('particle display keeps weak coastal currents visibly moving within budget', () => {
 assert.ok(screenSpeed(.1) >= 10); assert.ok(screenSpeed(.3) > screenSpeed(.1)); assert.ok(screenSpeed(2) < 4 * screenSpeed(.5));
 assert.equal(particleCount(390, 500, 1), 765);
 assert.equal(particleCount(1440, 700, 1), 1300);
 assert.equal(particleCount(200, 200, 1), 500);
 assert.ok(particleCount(390, 500, .1) < 400);
 assert.deepEqual(speedColor(0).length, 4);
});

for (const name of ['inner', 'mid', 'uchibo', 'boso']) {
 test(`${name} grid (when present): reference points and spot vertices inside it are on water`, {skip: !fs.existsSync(dataUrl(`harmonic-${name}.json`))}, () => {
  const meta = JSON.parse(fs.readFileSync(dataUrl(`harmonic-${name}.json`))), raw = fs.readFileSync(dataUrl(`harmonic-${name}.bin`));
  const g = prepareGrid(meta, new Int16Array(Uint8Array.from(raw).buffer));
  updateField(g, jstSlotTime('2026-11-01', 17));
  assert.equal(g.dxM, {inner: 50, mid: 100, uchibo: 200, boso: 500}[name]);
  let inside = 0;
  for (const p of REFERENCE_POINTS) {
   const s = sampleCurrents([g], p.lat, p.lon);
   if (s.reason === 'outside') continue;
   inside++; assert.ok(Number.isFinite(s.speed), p.name + ' ' + JSON.stringify(s));
  }
  assert.ok(inside >= 2);
  // spot outlines hug islands and forts; the 500 m Boso grid is too coarse to resolve them
  for (const spot of g.dxM <= 200 ? SPOTS : []) for (const [lat, lon] of spot.polygon) {
   const s = sampleCurrents([g], lat, lon);
   if (s.reason === 'outside') continue;
   assert.notEqual(s.reason, 'land', spot.label + ' ' + lat + ',' + lon);
  }
 });
}

test('three nested grids: 50 m > 100 m > 250 m, and land in a finer grid stays land', () => {
 const outer = synthetic({nx: 20, ny: 20, lat0: 35, lon0: 139, dlat: .01, dlon: .01, dxM: 250, name: 'outer', wet: all(20, 20), flow: () => [100, 0]});
 const mid = synthetic({nx: 40, ny: 40, lat0: 35.05, lon0: 139.05, dlat: .002, dlon: .002, dxM: 100, name: 'mid', wet: all(40, 40).filter(i => i !== 0), flow: () => [0, 100]});
 const inner = synthetic({nx: 20, ny: 20, lat0: 35.1, lon0: 139.1, dlat: .0005, dlon: .0005, dxM: 50, name: 'inner', wet: all(20, 20), flow: () => [-100, 0]});
 const grids = [inner, mid, outer];
 assert.equal(sampleCurrents(grids, 35.105, 139.105).grid, 'inner');
 assert.equal(sampleCurrents(grids, 35.08, 139.08).grid, 'mid');
 assert.equal(sampleCurrents(grids, 35.02, 139.02).grid, 'outer');
 const dry = sampleCurrents(grids, 35.05, 139.05);
 assert.equal(dry.reason, 'land'); assert.equal(dry.grid, 'mid');
 // mid absent -> outer answers there
 assert.equal(sampleCurrents([inner, outer], 35.08, 139.08).grid, 'outer');
});

test('gzip copies are served as plain binary and inflate in the browser to the source bytes', async () => {
 const bundle = packHarmonic(new URL('../data', import.meta.url).pathname);
 const index = JSON.parse(bundle.index);
 assert.ok(canInflate());
 for (const e of index.grids) {
  const source = fs.readFileSync(dataUrl(`harmonic-${e.name}.bin`));
  assert.match(e.coefGz, /^\/api\/harmonic\/[a-z]+-[0-9a-f]{12}\.bin\.gz$/);
  const r = harmonicResponse(e.coefGz, bundle, frameResponse);
  assert.equal(r.headers.get('content-encoding'), null);
  assert.equal(r.headers.get('content-type'), 'application/octet-stream');
  const gz = await r.arrayBuffer();
  assert.ok(isGzip(gz)); assert.ok(gz.byteLength < source.length / 2, 'gzip copy should be much smaller');
  assert.deepEqual(Buffer.from(await inflate(gz)), source);
  assert.deepEqual(Buffer.from(await inflate(source.buffer.slice(source.byteOffset, source.byteOffset + source.length))), source); // already inflated bytes pass through
  const depth = await inflate(await harmonicResponse(e.depthGz, bundle, frameResponse).arrayBuffer());
  assert.equal(depth.byteLength, e.wetCount * 2);
 }
});
