// Animated particle layer for a frozen current field (one selected time).
// Screen-space: the field is resampled onto a coarse pixel grid after each view change,
// particles advect through it and respawn on land / outside / old age.
const KT = 1.94384;
// Displayed particle speed (px/s) grows with sqrt(kt) so 0.1–0.3 kt still visibly moves.
export function screenSpeed(kt) { return 8 + 30 * Math.sqrt(Math.max(0, kt)); }
export function particleCount(width, height, waterFraction) {
 const base = Math.max(500, Math.min(1300, Math.round(width * height / 255)));
 return Math.max(150, Math.round(base * Math.min(1, Math.max(0, waterFraction))));
}
// Dark navy -> blue -> cyan -> green by speed (kt). Returns [r,g,b,a].
const STOPS = [[0, [10, 30, 80, 120]], [.3, [20, 80, 185, 150]], [1, [20, 175, 210, 165]], [2, [50, 205, 130, 175]], [3, [120, 225, 110, 185]]];
export function speedColor(kt) {
 if (kt <= 0) return STOPS[0][1];
 for (let i = 1; i < STOPS.length; i++) if (kt <= STOPS[i][0]) {
  const [k0, c0] = STOPS[i - 1], [k1, c1] = STOPS[i], t = (kt - k0) / (k1 - k0);
  return c0.map((v, j) => Math.round(v + (c1[j] - v) * t));
 }
 return STOPS.at(-1)[1];
}

export function createFlowLayer({fieldCanvas, trailCanvas, size, unproject, sample, win = globalThis}) {
 const raf = typeof win.requestAnimationFrame === 'function' ? win.requestAnimationFrame.bind(win) : null;
 const reduced = !!win.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
 const S = {enabled: false, interacting: false, dirty: true, lastChange: 0, running: false, frames: 0, rebuilds: 0, last: 0,
  w: 0, h: 0, dpr: 1, step: 4, gw: 0, gh: 0, u: null, v: null, water: null, waterCount: 0, px: null, py: null, age: null, life: null, n: 0};
 const uv = [0, 0];
 const now = () => (win.performance?.now ? win.performance.now() : Date.now());

 function ctxOf(canvas, clear = true) {
  const c = canvas.getContext('2d');
  if (!c) return null;
  if (canvas.width !== Math.round(S.w * S.dpr) || canvas.height !== Math.round(S.h * S.dpr)) { canvas.width = Math.round(S.w * S.dpr); canvas.height = Math.round(S.h * S.dpr); }
  c.setTransform?.(S.dpr, 0, 0, S.dpr, 0, 0);
  if (clear) c.clearRect(0, 0, S.w, S.h);
  return c;
 }
 function clear() {
  for (const canvas of [fieldCanvas, trailCanvas]) { const c = canvas.getContext('2d'); c?.setTransform?.(1, 0, 0, 1, 0, 0); c?.clearRect(0, 0, canvas.width, canvas.height); }
 }

 function rebuild() {
  const {width, height} = size();
  S.w = width; S.h = height; S.dpr = win.devicePixelRatio || 1; S.dirty = false; S.rebuilds++;
  S.step = width * height > 500000 ? 6 : 4;
  const gw = S.gw = Math.ceil(width / S.step) + 1, gh = S.gh = Math.ceil(height / S.step) + 1;
  const u = S.u = new Float32Array(gw * gh), v = S.v = new Float32Array(gw * gh), water = new Int32Array(gw * gh);
  // North-up maps: longitude depends on x only, latitude on y only.
  const lon = new Float64Array(gw), lat = new Float64Array(gh);
  for (let i = 0; i < gw; i++) lon[i] = unproject(i * S.step, 0).lon;
  for (let j = 0; j < gh; j++) lat[j] = unproject(0, j * S.step).lat;
  let count = 0;
  for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) {
   const k = j * gw + i, r = sample(lat[j], lon[i], uv);
   if (r) { u[k] = r[0]; v[k] = r[1]; water[count++] = k; } else { u[k] = NaN; v[k] = NaN; }
  }
  S.water = water; S.waterCount = count;
  drawField();
  const n = S.n = count ? particleCount(width, height, count / (gw * gh)) : 0;
  S.px = new Float32Array(n); S.py = new Float32Array(n); S.age = new Float32Array(n); S.life = new Float32Array(n);
  for (let p = 0; p < n; p++) { spawn(p); S.age[p] = Math.random() * S.life[p]; }
  ctxOf(trailCanvas);
 }

 function drawField() {
  const c = ctxOf(fieldCanvas);
  if (!c || !S.waterCount || typeof c.createImageData !== 'function') return;
  const doc = fieldCanvas.ownerDocument, off = doc?.createElement?.('canvas');
  if (!off) return;
  off.width = S.gw; off.height = S.gh;
  const oc = off.getContext('2d'), img = oc?.createImageData?.(S.gw, S.gh);
  if (!img) return;
  for (let k = 0; k < S.gw * S.gh; k++) {
   if (Number.isNaN(S.u[k])) continue;
   const col = speedColor(Math.hypot(S.u[k], S.v[k]) * KT), o = k * 4;
   img.data[o] = col[0]; img.data[o + 1] = col[1]; img.data[o + 2] = col[2]; img.data[o + 3] = col[3];
  }
  oc.putImageData(img, 0, 0);
  c.imageSmoothingEnabled = true;
  c.drawImage(off, 0, 0, S.gw, S.gh, 0, 0, S.gw * S.step, S.gh * S.step);
 }

 function spawn(p) {
  const k = S.water[(Math.random() * S.waterCount) | 0], i = k % S.gw, j = (k / S.gw) | 0;
  S.px[p] = (i + Math.random() - .5) * S.step; S.py[p] = (j + Math.random() - .5) * S.step;
  S.age[p] = 0; S.life[p] = 4 + Math.random() * 6;
 }

 // Bilinear velocity on the pixel grid. Dry corners are left out and the weights renormalised,
 // so streaks follow the shore; null when the nearest node is land or the point is outside.
 function velocity(x, y) {
  const fx = x / S.step, fy = y / S.step, i = Math.floor(fx), j = Math.floor(fy);
  if (i < 0 || j < 0 || i >= S.gw - 1 || j >= S.gh - 1) return null;
  const k = j * S.gw + i, tx = fx - i, ty = fy - j, U = S.u, V = S.v;
  const near = k + (tx > .5 ? 1 : 0) + (ty > .5 ? S.gw : 0);
  if (Number.isNaN(U[near])) return null;
  let u = 0, v = 0, w = 0;
  const add = (idx, wt) => { if (!Number.isNaN(U[idx])) { u += U[idx] * wt; v += V[idx] * wt; w += wt; } };
  add(k, (1 - tx) * (1 - ty)); add(k + 1, tx * (1 - ty)); add(k + S.gw, (1 - tx) * ty); add(k + S.gw + 1, tx * ty);
  if (w <= 1e-9) return null;
  uv[0] = u / w; uv[1] = v / w;
  return uv;
 }

 const BUCKETS = [['rgba(170,225,250,.62)', .3], ['rgba(210,242,255,.75)', 1], ['rgba(255,255,255,.9)', Infinity]];
 function stepParticles(c, dt) {
  const paths = BUCKETS.map(() => []);
  for (let p = 0; p < S.n; p++) {
   S.age[p] += dt;
   const x = S.px[p], y = S.py[p], vel = S.age[p] > S.life[p] ? null : velocity(x, y);
   if (!vel) { spawn(p); continue; }
   const mps = Math.hypot(vel[0], vel[1]), kt = mps * KT;
   if (mps < 1e-6) continue;
   const pxs = screenSpeed(kt) * dt / mps, nx = x + vel[0] * pxs, ny = y - vel[1] * pxs;
   if (!velocity(nx, ny)) { spawn(p); continue; }
   S.px[p] = nx; S.py[p] = ny;
   paths[kt < BUCKETS[0][1] ? 0 : kt < BUCKETS[1][1] ? 1 : 2].push(x, y, nx, ny);
  }
  c.lineWidth = 1; c.lineCap = 'round';
  BUCKETS.forEach(([color], b) => {
   const a = paths[b]; if (!a.length) return;
   c.beginPath();
   for (let i = 0; i < a.length; i += 4) { c.moveTo(a[i], a[i + 1]); c.lineTo(a[i + 2], a[i + 3]); }
   c.strokeStyle = color; c.stroke();
  });
 }

 function frame(t) {
  S.running = false;
  if (!S.enabled || S.interacting || win.document?.hidden) return;
  if (S.dirty) {
   if (now() - S.lastChange < 120) { schedule(); return; }
   rebuild();
   if (reduced) { staticSnapshot(); return; }
  }
  if (!S.n) return;
  const dt = Math.min(.05, S.last ? (t - S.last) / 1000 : 1 / 60); S.last = t;
  const c = trailCanvas.getContext('2d');
  c.globalCompositeOperation = 'destination-out';
  c.fillStyle = `rgba(0,0,0,${1 - Math.pow(.94, dt * 60)})`; c.fillRect(0, 0, S.w, S.h);
  c.globalCompositeOperation = 'source-over';
  stepParticles(c, dt); S.frames++;
  schedule();
 }
 function staticSnapshot() {
  const c = trailCanvas.getContext('2d');
  for (let i = 0; i < 25; i++) stepParticles(c, 1 / 30);
 }
 function schedule() {
  if (S.running || !raf || !S.enabled) return;
  S.running = true; raf(t => frame(t));
 }

 win.document?.addEventListener?.('visibilitychange', () => { S.last = 0; if (!win.document.hidden) schedule(); });

 return {
  // Call whenever the view (pan/zoom/size) or the field changed: trails are cleared.
  invalidate() { S.dirty = true; S.lastChange = now(); S.last = 0; clear(); schedule(); },
  setInteracting(on) { if (S.interacting === !!on) return; S.interacting = !!on; if (on) { clear(); S.dirty = true; } else { S.lastChange = now(); S.last = 0; schedule(); } },
  setEnabled(on) { S.enabled = !!on; if (!on) { clear(); S.dirty = true; } else { S.dirty = true; schedule(); } },
  stats() { return {enabled: S.enabled, frames: S.frames, rebuilds: S.rebuilds, particles: S.n, water: S.waterCount, interacting: S.interacting, running: S.running}; }
 };
}
