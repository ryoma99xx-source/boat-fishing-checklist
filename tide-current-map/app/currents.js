// Harmonic tidal-current grids: decoding, synthesis and sampling (no DOM).
// Grids are given in priority order (inner 50 m first, then outer 250 m).
import {synthesize, synthesizeCells, factors} from './harmonic.js';

export const MPS_TO_KT = 1.94384;

// Inflate gzip bytes in the browser (DecompressionStream). Bytes that are not gzip (a proxy
// already inflated them) are returned unchanged. Returns an ArrayBuffer.
export const canInflate = () => typeof DecompressionStream === 'function';
export function isGzip(buffer) { const b = new Uint8Array(buffer); return b.length > 2 && b[0] === 0x1f && b[1] === 0x8b; }
export async function inflate(buffer) {
 if (!isGzip(buffer)) return buffer;
 const stream = new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'));
 return await new Response(stream).arrayBuffer();
}

// wetRuns: flat [start0,length0,start1,length1,...] of ascending row-major ids.
export function encodeRuns(ids) {
 const runs = [];
 for (let i = 0; i < ids.length;) {
  let j = i + 1;
  while (j < ids.length && ids[j] === ids[j - 1] + 1) j++;
  runs.push(ids[i], j - i); i = j;
 }
 return runs;
}
export function decodeRuns(runs, count) {
 let total = 0;
 for (let i = 1; i < runs.length; i += 2) total += runs[i];
 if (count != null && total !== count) throw Error('wetRuns length mismatch');
 const ids = new Int32Array(total);
 let k = 0;
 for (let i = 0; i < runs.length; i += 2) for (let j = 0; j < runs[i + 1]; j++) ids[k++] = runs[i] + j;
 return ids;
}

// ---- Tiles -------------------------------------------------------------------------------
// Each grid is split into TILE x TILE cell blocks so the app downloads only what the view needs.
// A tile holds, for its wet cells in ascending row-major order, every coefficient column and the
// depth, stored column by column as int16 differences from the previous cell (fields are smooth,
// so the differences are small and gzip about twice as well as the raw layout).
export const TILE = 32;
export function tileOf(g, id) { const nx = g.nx, ntx = Math.ceil(nx / TILE); return Math.floor(Math.floor(id / nx) / TILE) * ntx + Math.floor((id % nx) / TILE); }
export function tileCells(ids, nx, ny) {
 const ntx = Math.ceil(nx / TILE), nty = Math.ceil(ny / TILE), lists = Array.from({length: ntx * nty}, () => []);
 for (let i = 0; i < ids.length; i++) lists[Math.floor(Math.floor(ids[i] / nx) / TILE) * ntx + Math.floor((ids[i] % nx) / TILE)].push(i);
 return {ntx, nty, lists};
}
// coef: Int16Array (stride per cell), depthDm: Uint16Array; cells: wet-cell indices of one tile.
export function encodeTile(coef, depthDm, stride, cells) {
 const n = cells.length, out = new Int16Array((stride + 1) * n);
 for (let k = 0; k <= stride; k++) {
  let prev = 0;
  for (let j = 0; j < n; j++) {
   const v = k < stride ? coef[cells[j] * stride + k] : (depthDm[cells[j]] << 16 >> 16);
   out[k * n + j] = v - prev; prev = v;
  }
 }
 return out;
}
export function decodeTile(data, coef, depthDm, stride, cells) {
 const n = cells.length;
 if (data.length !== (stride + 1) * n) throw Error('harmonic tile length mismatch');
 const acc = new Int16Array(1);
 for (let k = 0; k <= stride; k++) {
  acc[0] = 0;
  for (let j = 0; j < n; j++) {
   acc[0] += data[k * n + j];
   if (k < stride) coef[cells[j] * stride + k] = acc[0]; else depthDm[cells[j]] = acc[0] & 0xffff;
  }
 }
}
// Grid built from served meta only; tiles are filled in by loadTile. state: 0 none, 1 loading, 2 ready, 3 failed.
export function emptyGrid(meta, entry) {
 const ids = decodeRuns(meta.wetRuns, meta.wetCount), stride = 2 + 4 * meta.constituents.length;
 const g = prepareGrid(meta, new Int16Array(ids.length * stride), new Uint16Array(ids.length));
 const {ntx, nty, lists} = tileCells(ids, meta.nx, meta.ny);
 g.entry = entry; g.stride = stride; g.ntx = ntx; g.nty = nty; g.tileLists = lists;
 g.tileState = new Uint8Array(ntx * nty); g.cellReady = new Uint8Array(ids.length);
 for (let t = 0; t < lists.length; t++) if (!lists[t].length) g.tileState[t] = 2;
 return g;
}
export function applyTile(g, t, data) {
 decodeTile(data, g.coef, g.depthDm, g.stride, g.tileLists[t]);
 for (const i of g.tileLists[t]) g.cellReady[i] = 1;
 g.tileState[t] = 2;
 if (g.fieldTime !== null && g.fac) synthesizeCells(g.meta, g.coef, g.fac, g.field, g.tileLists[t]);
}
export function tileAt(g, lat, lon) {
 const p = locate(g, lat, lon);
 return p ? Math.floor(p.iy / TILE) * g.ntx + Math.floor(p.ix / TILE) : -1;
}
const cellReady = (g, i) => !g.cellReady || g.cellReady[i] === 1;

// meta: served meta (wetRuns or wetIds). coef: Int16Array. depthDm: Uint16Array (optional).
export function prepareGrid(meta, coef, depthDm = null) {
 const ids = meta.wetIds ? Int32Array.from(meta.wetIds) : decodeRuns(meta.wetRuns, meta.wetCount);
 const stride = 2 + 4 * meta.constituents.length;
 if (coef.length !== ids.length * stride) throw Error('harmonic coefficient length mismatch');
 if (depthDm && depthDm.length !== ids.length) throw Error('harmonic depth length mismatch');
 const index = new Int32Array(meta.nx * meta.ny).fill(-1);
 for (let i = 0; i < ids.length; i++) index[ids[i]] = i;
 return {meta, name: meta.name, nx: meta.nx, ny: meta.ny, lat0: meta.lat0, lon0: meta.lon0, dlat: meta.dlat, dlon: meta.dlon,
  dxM: meta.dxM, ids, index, coef, depthDm, wetCount: ids.length, field: new Float32Array(ids.length * 2), fieldTime: null};
}

// Placeholder for a grid listed in the index but not downloaded yet (lazy inner grid).
// It occupies its area so the coarser grid is never substituted there.
export function pendingGrid(entry) {
 return {name: entry.name, nx: entry.nx, ny: entry.ny, lat0: entry.lat0, lon0: entry.lon0, dlat: entry.dlat, dlon: entry.dlon, dxM: entry.dxM, pending: true, failed: false, entry};
}

export function gridBounds(g) {
 return {south: g.lat0 - g.dlat / 2, north: g.lat0 + g.dlat * (g.ny - .5), west: g.lon0 - g.dlon / 2, east: g.lon0 + g.dlon * (g.nx - .5)};
}

// Synthesize the whole field (m/s) for a JS time; cheap, so call on every date/time change.
export function updateField(g, ms) {
 if (g.fieldTime === ms) return g.field;
 if (!g.tileLists) { synthesize(g.meta, g.coef, ms, g.field); g.fieldTime = ms; return g.field; }
 // tiled grid: only tiles already downloaded; later tiles are synthesized on arrival (applyTile)
 g.fac = factors(g.meta, ms);
 for (let t = 0; t < g.tileLists.length; t++) if (g.tileState[t] === 2 && g.tileLists[t].length) synthesizeCells(g.meta, g.coef, g.fac, g.field, g.tileLists[t]);
 g.fieldTime = ms; return g.field;
}

// JST date (YYYY-MM-DD) + 30-minute slot -> epoch ms.
export function jstSlotTime(date, slot) {
 const [y, m, d] = date.split('-').map(Number);
 return Date.UTC(y, m - 1, d, 0, slot * 30) - 9 * 3600000;
}

function locate(g, lat, lon) {
 const fx = (lon - g.lon0) / g.dlon, fy = (lat - g.lat0) / g.dlat;
 if (!(fx >= -.5 && fy >= -.5 && fx <= g.nx - .5 && fy <= g.ny - .5)) return null;
 return {fx, fy, ix: Math.min(g.nx - 1, Math.max(0, Math.round(fx))), iy: Math.min(g.ny - 1, Math.max(0, Math.round(fy)))};
}

// Bilinear velocity [u,v] (m/s) inside one grid; null on dry/outside. Dry corners are left out
// and the remaining weights renormalised; the nearest cell itself must be wet.
export function velocityInGrid(g, lat, lon, out = [0, 0]) {
 if (g.pending) return null;
 const p = locate(g, lat, lon);
 if (!p || g.index[p.iy * g.nx + p.ix] < 0 || !cellReady(g, g.index[p.iy * g.nx + p.ix])) return null;
 const x0 = Math.floor(p.fx), y0 = Math.floor(p.fy), tx = p.fx - x0, ty = p.fy - y0, f = g.field;
 let u = 0, v = 0, w = 0;
 for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) {
  const x = x0 + dx, y = y0 + dy;
  if (x < 0 || y < 0 || x >= g.nx || y >= g.ny) continue;
  const i = g.index[y * g.nx + x];
  if (i < 0 || !cellReady(g, i)) continue;
  const wt = (dx ? tx : 1 - tx) * (dy ? ty : 1 - ty);
  u += f[2 * i] * wt; v += f[2 * i + 1] * wt; w += wt;
 }
 if (w <= 1e-9) return null;
 out[0] = u / w; out[1] = v / w; return out;
}

// The finest grid that contains the point decides: inner land stays land (no coarse substitute).
export function gridFor(grids, lat, lon) {
 for (const g of grids) if (locate(g, lat, lon)) return g;
 return null;
}
export function velocityAt(grids, lat, lon, out = [0, 0]) {
 const g = gridFor(grids, lat, lon);
 return g ? velocityInGrid(g, lat, lon, out) : null;
}

const norm = d => (d % 360 + 360) % 360;
export function sampleCurrents(grids, lat, lon) {
 if (!grids || !grids.length) return {reason: 'loading'};
 const g = gridFor(grids, lat, lon);
 if (!g) return {reason: 'outside'};
 if (g.pending) return {reason: g.failed ? 'failed' : 'pending', grid: g.name, cellSize: g.dxM};
 if (g.fieldTime === null) return {reason: 'loading'};
 const p = locate(g, lat, lon), cell = g.index[p.iy * g.nx + p.ix];
 if (cell < 0) return {reason: 'land', grid: g.name, cellSize: g.dxM};
 if (!cellReady(g, cell)) { const st = g.tileState[tileAt(g, lat, lon)]; return {reason: st === 3 ? 'failed' : 'pending', grid: g.name, cellSize: g.dxM}; }
 const uv = velocityInGrid(g, lat, lon);
 const [u, v] = uv, mps = Math.hypot(u, v);
 const shore = shoreInfo(g, p.ix, p.iy);
 const offshore = mps && shore.nx != null ? -(u * shore.nx + v * shore.ny) / mps : 0;
 return {grid: g.name, cellSize: g.dxM, lat: g.lat0 + p.iy * g.dlat, lon: g.lon0 + p.ix * g.dlon, uMps: u, vMps: v, speedMps: mps,
  speed: mps * MPS_TO_KT, bearing: norm(Math.atan2(u, v) * 180 / Math.PI), depth: g.depthDm ? g.depthDm[cell] / 10 : null,
  shore: shore.distance, shoreType: mps * MPS_TO_KT < .1 ? 'ごく弱い流れ' : shore.nx == null || Math.abs(offshore) < .35 ? '岸に沿う成分が主' : offshore > 0 ? '岸から離れる成分あり' : '岸へ寄る成分あり'};
}

// Distance (m) to the nearest dry cell within ~2 km and the unit vector (east, north) toward it.
export function shoreInfo(g, ix, iy, maxM = 2000) {
 const r = Math.max(1, Math.round(maxM / g.dxM)), cosLat = Math.cos((g.lat0 + iy * g.dlat) * Math.PI / 180);
 const mx = g.dlon * 111320 * cosLat, my = g.dlat * 110540;
 let best = Infinity, bx = 0, by = 0;
 for (let dy = -r; dy <= r; dy++) {
  const y = iy + dy; if (y < 0 || y >= g.ny) continue;
  for (let dx = -r; dx <= r; dx++) {
   const x = ix + dx; if (x < 0 || x >= g.nx || g.index[y * g.nx + x] >= 0) continue;
   const ex = dx * mx, ny = dy * my, d = ex * ex + ny * ny;
   if (d < best) {best = d; bx = ex; by = ny;}
  }
 }
 if (best === Infinity) return {distance: null, nx: null, ny: null};
 const d = Math.sqrt(best);
 return {distance: Math.max(0, d - g.dxM / 2), nx: bx / d, ny: by / d};
}
