// Build-time packing of the harmonic current grids (Node only, not bundled).
// The coefficient .bin is gzipped unchanged; the Worker decompresses it and serves the
// original bytes (see frame.js). wetIds become runs; depth becomes uint16 decimetres.
import fs from 'node:fs';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {encodeRuns} from '../currents.js';

export const GRID_ORDER = ['inner', 'mid', 'outer']; // finest first: the first grid containing a point decides

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
 return {entry: {name, label: meta.label || name, dxM: meta.dxM, nx: meta.nx, ny: meta.ny, lat0: meta.lat0, lon0: meta.lon0, dlat: meta.dlat, dlon: meta.dlon, wetCount: ids.length, meta: base + '.json', coef: base + '.bin', depth: base + '.depth.bin', coefBytes: bin.length},
  files: {[base + '.json']: {type: 'json', text: served}, [base + '.bin']: {type: 'bin', gz: gzipSync(bin, {level: 9}).toString('base64')}, [base + '.depth.bin']: {type: 'bin', gz: gzipSync(depthRaw, {level: 9}).toString('base64')}}};
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
