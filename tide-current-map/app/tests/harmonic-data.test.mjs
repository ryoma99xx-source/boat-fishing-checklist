import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gzipSync, gunzipSync} from 'node:zlib';
import {MPS_TO_KT, encodeRuns, decodeRuns, prepareGrid, updateField, velocityInGrid, velocityAt, sampleCurrents, jstSlotTime, gridFor, inflate, isGzip, canInflate, emptyGrid, applyTile, encodeTile, decodeTile} from '../currents.js';
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

test('tiles served by the Worker rebuild every grid exactly (coefficients, depth, wet cells)', async () => {
 const bundle = packHarmonic(new URL('../data', import.meta.url).pathname);
 const index = JSON.parse(bundle.index);
 assert.ok(index.grids.length >= 1);
 assert.equal(index.grids.at(-1).name, GRID_ORDER.filter(n => fs.existsSync(dataUrl(`harmonic-${n}.json`))).at(-1));
 assert.equal(harmonicResponse('/api/harmonic/index.json', bundle, frameResponse).headers.get('cache-control'), 'no-cache');
 assert.ok(canInflate());
 for (const e of index.grids) {
  const source = fs.readFileSync(dataUrl(`harmonic-${e.name}.bin`)), meta = JSON.parse(fs.readFileSync(dataUrl(`harmonic-${e.name}.json`)));
  const servedMeta = await harmonicResponse(e.meta, bundle, frameResponse).json();
  assert.deepEqual([...decodeRuns(servedMeta.wetRuns, servedMeta.wetCount)], meta.wetIds);
  const g = emptyGrid(servedMeta, e);
  let gzBytes = 0, tiles = 0;
  for (let t = 0; t < g.ntx * g.nty; t++) {
   if (!g.tileLists[t].length) { assert.equal(e.tiles[t], undefined); continue; }
   const url = `${e.tileBase}.t${t}.gz`, r = harmonicResponse(url, bundle, frameResponse);
   assert.equal(r.status, 200); assert.equal(r.headers.get('content-encoding'), null);
   assert.equal(r.headers.get('content-type'), 'application/octet-stream'); assert.match(r.headers.get('cache-control'), /immutable/);
   const gz = await r.arrayBuffer(); assert.ok(isGzip(gz)); gzBytes += gz.byteLength; tiles++;
   const raw = await inflate(gz);
   // the Worker-inflated .bin copy (for browsers without DecompressionStream) has the same bytes
   assert.deepEqual(Buffer.from(await harmonicResponse(`${e.tileBase}.t${t}.bin`, bundle, frameResponse).arrayBuffer()), Buffer.from(raw));
   applyTile(g, t, new Int16Array(raw));
  }
  assert.equal(tiles, Object.keys(e.tiles).length);
  assert.deepEqual(Buffer.from(g.coef.buffer), source, e.name + ' coefficients');
  assert.deepEqual(Buffer.from(g.depthDm.buffer), depthBytes(meta.depth), e.name + ' depth');
  assert.ok(g.cellReady.every(x => x === 1));
  assert.ok(gzBytes < source.length / 3, e.name + ' tiles should be much smaller than the raw grid');
 }
 assert.equal(harmonicResponse('/api/harmonic/outer-000000000000.t0.gz', bundle, frameResponse).status, 404);
 assert.equal(harmonicResponse('/api/other', bundle, frameResponse), null);
});
test('content hash changes when the coefficients change', () => {
 const meta = {name: 'x', nx: 2, ny: 1, lat0: 35, lon0: 139, dlat: .01, dlon: .01, dxM: 50, ...CONST, wetIds: [0, 1], depth: [5, 6]};
 const a = packGrid(meta, Buffer.alloc(24), 'inner'), b = packGrid(meta, Buffer.alloc(24, 1), 'inner');
 assert.notEqual(a.entry.tileBase, b.entry.tileBase);
 assert.throws(() => packGrid(meta, Buffer.alloc(10), 'inner'), /bin length/);
 assert.throws(() => packGrid({...meta, wetIds: [1, 0]}, Buffer.alloc(24), 'inner'), /ascend/);
});
test('tile delta coding survives int16 wrap-around and large depths', () => {
 const stride = 2, cells = [0, 1, 2, 3], coef = Int16Array.from([32767, -32768, -32768, 32767, 0, 1, 32767, -1]);
 const depth = Uint16Array.from([0, 65535, 30000, 1]);
 const enc = encodeTile(coef, depth, stride, cells), c2 = new Int16Array(coef.length), d2 = new Uint16Array(depth.length);
 decodeTile(enc, c2, d2, stride, cells);
 assert.deepEqual([...c2], [...coef]); assert.deepEqual([...d2], [...depth]);
});
test('cells of tiles that are not loaded yet report pending, never a coarser value', () => {
 const meta = {nx: 40, ny: 1, lat0: 35, lon0: 139, dlat: .001, dlon: .001, dxM: 50, ...CONST, wetRuns: [0, 40], wetCount: 40};
 const g = emptyGrid(meta, {name: 'inner'}); updateField(g, jstSlotTime('2026-11-01', 17));
 assert.equal(g.ntx, 2);
 assert.equal(sampleCurrents([g], 35, 139.005).reason, 'pending');
 applyTile(g, 0, encodeTile(new Int16Array(40 * g.stride).fill(100), new Uint16Array(40).fill(50), g.stride, g.tileLists[0])); updateField(g, jstSlotTime('2026-11-01', 17));
 assert.ok(Number.isFinite(sampleCurrents([g], 35, 139.005).speed));
 assert.equal(sampleCurrents([g], 35, 139.035).reason, 'pending');
 g.tileState[1] = 3; assert.equal(sampleCurrents([g], 35, 139.035).reason, 'failed');
});

