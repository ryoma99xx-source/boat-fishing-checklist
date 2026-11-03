// Harmonic tidal current synthesis (port of scripts/tidelib.py, UTC Greenwich convention).
const RAD = Math.PI / 180;
const RATES = [14.4920521, 0.5490165, 0.0410686, 0.0046418, 0.0022064, 0.0000020];
const EPOCH = Date.UTC(2000, 0, 1, 12);

export function hoursSinceEpoch(ms) { return (ms - EPOCH) / 3600000; }

function astro(t) {
  const T = t / (24 * 36525);
  const s = 218.3164477 + 481267.88123421 * T;
  const h = 280.46646 + 36000.76983 * T;
  const p = 83.3532465 + 4069.0137287 * T;
  const N = 125.04452 - 1934.136261 * T;
  const p1 = 282.93735 + 1.71946 * T;
  const ut = (((t + 12) % 24) + 24) % 24;
  return [15 * ut + 180 + h - s, s, h, p, -N, p1, N];
}

function nodal(family, N) {
  const n = N * RAD, c = Math.cos, s = Math.sin;
  switch (family) {
    case 'one': return [1, 0];
    case 'M2': return [1.0004 - .0373 * c(n) + .0002 * c(2 * n), -2.14 * s(n)];
    case 'O1': return [1.0089 + .1871 * c(n) - .0147 * c(2 * n) + .0014 * c(3 * n), 10.8 * s(n) - 1.34 * s(2 * n) + .19 * s(3 * n)];
    case 'K1': return [1.0060 + .1150 * c(n) - .0088 * c(2 * n) + .0006 * c(3 * n), -8.86 * s(n) + .68 * s(2 * n) - .07 * s(3 * n)];
    case 'K2': return [1.0241 + .2863 * c(n) + .0083 * c(2 * n) - .0015 * c(3 * n), -17.74 * s(n) + .68 * s(2 * n) - .04 * s(3 * n)];
    case 'J1': return [1.0129 + .1676 * c(n) - .0170 * c(2 * n) + .0016 * c(3 * n), -12.94 * s(n) + 1.34 * s(2 * n) - .19 * s(3 * n)];
    case 'OO1': return [1.1027 + .6504 * c(n) + .0317 * c(2 * n) - .0014 * c(3 * n), -36.68 * s(n) + 4.02 * s(2 * n) - .57 * s(3 * n)];
    case 'Mm': return [1 - .13 * c(n) + .0013 * c(2 * n), 0];
  }
  const [fm, um] = nodal('M2', N);
  if (family === 'M4') return [fm * fm, 2 * um];
  if (family === 'M6') return [fm ** 3, 3 * um];
  if (family === 'M3') return [fm ** 1.5, 1.5 * um];
  if (family === 'MK3') { const [fk, uk] = nodal('K1', N); return [fm * fk, um + uk]; }
  throw new Error('unknown nodal family ' + family);
}

// Returns {f:[...], cos:[...], sin:[...]} for the metadata constituents at a JS time (ms).
export function factors(meta, ms) {
  const t = hoursSinceEpoch(ms);
  const a = astro(t), N = a[6];
  const n = meta.constituents.length, f = new Float64Array(n), cs = new Float64Array(n), sn = new Float64Array(n);
  for (let j = 0; j < n; j++) {
    const d = meta.doodson[j];
    let V = meta.phaseOffsetDeg[j];
    for (let k = 0; k < 6; k++) V += d[k] * a[k];
    const [fj, uj] = nodal(meta.nodal[j], N);
    const arg = (V + uj) * RAD;
    f[j] = fj; cs[j] = fj * Math.cos(arg); sn[j] = fj * Math.sin(arg);
  }
  return { f, cos: cs, sin: sn };
}

// coef: Int16Array laid out per meta.layout. Returns Float32Array [u0,v0,u1,v1,...] in m/s.
export function synthesize(meta, coef, ms, out) {
  const n = meta.constituents.length, stride = 2 + 4 * n, cells = coef.length / stride;
  const { cos, sin } = factors(meta, ms);
  const res = out || new Float32Array(cells * 2);
  for (let i = 0; i < cells; i++) {
    const o = i * stride;
    let u = coef[o], v = coef[o + 1];
    for (let j = 0; j < n; j++) {
      const k = o + 2 + 4 * j;
      u += coef[k] * cos[j] + coef[k + 1] * sin[j];
      v += coef[k + 2] * cos[j] + coef[k + 3] * sin[j];
    }
    res[2 * i] = u / 1000; res[2 * i + 1] = v / 1000;
  }
  return res;
}

// Single cell (index in wetIds order).
export function synthesizeCell(meta, coef, index, ms) {
  const n = meta.constituents.length, stride = 2 + 4 * n, o = index * stride;
  const { cos, sin } = factors(meta, ms);
  let u = coef[o], v = coef[o + 1];
  for (let j = 0; j < n; j++) {
    const k = o + 2 + 4 * j;
    u += coef[k] * cos[j] + coef[k + 1] * sin[j];
    v += coef[k + 2] * cos[j] + coef[k + 3] * sin[j];
  }
  return [u / 1000, v / 1000];
}

// Only the listed cells (wet-cell indices); fac from factors(meta, ms).
export function synthesizeCells(meta, coef, fac, out, cells) {
  const n = meta.constituents.length, stride = 2 + 4 * n, {cos, sin} = fac;
  for (const i of cells) {
    const o = i * stride;
    let u = coef[o], v = coef[o + 1];
    for (let j = 0; j < n; j++) {
      const k = o + 2 + 4 * j;
      u += coef[k] * cos[j] + coef[k + 1] * sin[j];
      v += coef[k + 2] * cos[j] + coef[k + 3] * sin[j];
    }
    out[2 * i] = u / 1000; out[2 * i + 1] = v / 1000;
  }
}
