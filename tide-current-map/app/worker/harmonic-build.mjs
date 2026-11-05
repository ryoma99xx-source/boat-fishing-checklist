// Build-time packing of the harmonic current grids (Node only, not bundled).
// Coefficients and depth are split into delta-encoded tiles (currents.js); wetIds become runs.
import fs from 'node:fs';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {encodeRuns, tileCells, encodeTile, TILE} from '../currents.js';

export const GRID_ORDER = ['inner', 'mid', 'outer', 'uchibo', 'boso']; // first grid containing a point decides. The bay model (outer) is tuned to the bay tide gauges, so it outranks the 200 m inner-Boso grid inside its box

export function depthBytes(depth) {
 const out = new Uint16Array(depth.length);
 for (let i = 0; i < depth.length; i++) out[i] = Math.max(0, Math.min(65535, Math.round(depth[i] * 10)));
 return Buffer.from(out.buffer);
}

export function packGrid(meta, bin, name) {
 const ids = meta.wetIds, stride = 2 + 4 * meta.constituents.length;
 for (let i = 1; i < ids.length; i++) if (!(ids[i] > ids[i - 1])) throw Error(`harmonic-${name}: wetIds must ascend`);
 if (ids.length && (ids[0] < 0 || ids.at(-1) >= meta.nx * meta.ny)) throw Error(`harmonic-${name}: wetIds out of grid`);
 if (bin.length !== ids.length * stride * 2) throw Error(`harmonic-${name}: bin length ${bin.length} != ${ids.length * stride * 2}`);
 if (!Array.isArray(meta.depth) || meta.depth.length !== ids.length) throw Error(`harmonic-${name}: depth length mismatch`);
 const {wetIds, depth, ...rest} = meta;
 const served = JSON.stringify({...rest, grid: name, wetCount: ids.length, wetRuns: encodeRuns(ids)});
 const depthRaw = depthBytes(depth);
 const hash = createHash('sha256').update(served).update(bin).update(depthRaw).digest('hex').slice(0, 12);
 const base = `/api/harmonic/${name}-${hash}`;
 // Tiles: only the blocks the view needs are downloaded (see currents.js). Stored gzipped and
 // served as-is; the browser inflates them (DecompressionStream) or the Worker does (<tile>.bin).
 const coef = new Int16Array(bin.buffer.slice(bin.byteOffset, bin.byteOffset + bin.length));
 const depthDm = new Uint16Array(depthRaw.buffer.slice(depthRaw.byteOffset, depthRaw.byteOffset + depthRaw.length));
 const {ntx, nty, lists} = tileCells(ids, meta.nx, meta.ny);
 const files = {[base + '.json']: {type: 'json', text: served}}, tiles = {};
 let tileBytes = 0;
 lists.forEach((cells, t) => {
  if (!cells.length) return;
  const enc = encodeTile(coef, depthDm, stride, cells), gz = gzipSync(Buffer.from(enc.buffer), {level: 9});
  files[`${base}.t${t}.gz`] = {type: 'gz', gz: gz.toString('base64')}; tiles[t] = gz.length; tileBytes += gz.length;
 });
 return {entry: {name, label: meta.label || name, dxM: meta.dxM, nx: meta.nx, ny: meta.ny, lat0: meta.lat0, lon0: meta.lon0, dlat: meta.dlat, dlon: meta.dlon,
   wetCount: ids.length, meta: base + '.json', metaData: JSON.parse(served), tileBase: base, tileSize: TILE, ntx, nty, tiles, tileBytes, coefBytes: bin.length}, files};
}

export function packHarmonic(dir = 'data') {
 const grids = [], files = {};
 for (const name of GRID_ORDER) {
  const json = `${dir}/harmonic-${name}.json`, bin = `${dir}/harmonic-${name}.bin`;
  if (!fs.existsSync(json) || !fs.existsSync(bin)) continue;
  const packed = packGrid(JSON.parse(fs.readFileSync(json, 'utf8')), fs.readFileSync(bin), name);
  grids.push(packed.entry); Object.assign(files, packed.files);
 }
 const validationPath = `${dir}/model-validation.json`;
 const validation = fs.existsSync(validationPath) ? JSON.parse(fs.readFileSync(validationPath, 'utf8')) : null;
 return {index: JSON.stringify({version: 1, grids, validation}), files};
}
