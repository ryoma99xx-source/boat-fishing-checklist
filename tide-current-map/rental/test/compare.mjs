#!/usr/bin/env node
// Compares the rental build (static files + PHP) with the original Worker, route by route.
//
//   node tide-current-map/rental/test/compare.mjs <app-dir> [--browser <screenshot.png>] [--no-apache] [--keep]
//
// 1. Builds the Worker exactly as the app does (scripts/build.mjs, in a temporary copy of the
//    app) and runs its fetch handler in-process for reference responses.
// 2. Builds the rental site, serves it with `php -S` (router.php emulates the .htaccess) and,
//    when Apache + mod_php are installed, also with Apache using the real .htaccess files on a
//    deliberately unfriendly config (.gz mapped to Content-Encoding, DEFLATE on).
// 3. For every route: same status, content type, cache/security headers, byte-identical body
//    (/api/* JSON compared parsed). No live 海上保安庁/気象庁 requests are made.
// 4. --browser: loads the site in Playwright Chromium against php -S and saves a screenshot.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import zlib from 'node:zlib';
import {spawn, execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {buildRental} from '../build-rental.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const appDir = path.resolve(args.find(a => !a.startsWith('--') && args[args.indexOf(a) - 1] !== '--browser') || '');
const shot = args.includes('--browser') ? path.resolve(args[args.indexOf('--browser') + 1]) : null;
if (!fs.existsSync(path.join(appDir, 'scripts/build.mjs'))) { console.error('usage: compare.mjs <app-dir> [--browser shot.png] [--no-apache] [--keep]'); process.exit(2); }

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'tide-rental-'));
fs.chmodSync(tmp, 0o755);
const cleanup = [];
process.on('exit', () => { for (const f of cleanup.reverse()) try { f(); } catch {} if (!args.includes('--keep')) fs.rmSync(tmp, {recursive: true, force: true}); });
process.on('SIGINT', () => process.exit(130));

// ---------- reference Worker ----------
const workerSrc = path.join(tmp, 'app');
fs.cpSync(appDir, workerSrc, {recursive: true, filter: s => !/[\\/](dist|node_modules|\.git)$/.test(s)});
fs.mkdirSync(path.join(workerSrc, '.openai'), {recursive: true});
fs.writeFileSync(path.join(workerSrc, '.openai/hosting.json'), JSON.stringify({project_id: 'dummy', static: {}}));
execFileSync(process.execPath, ['scripts/build.mjs'], {cwd: workerSrc, stdio: 'ignore'});
const worker = (await import(pathToFileURL(path.join(workerSrc, 'dist/server/index.js')).href)).default;
const ENV = {GOOGLE_MAPS_BROWSER_KEY: 'TEST-KEY', GOOGLE_MAPS_ENABLED: 'true'};
const realFetch = globalThis.fetch;
globalThis.fetch = async url => { throw Error('test must not reach upstream: ' + url); };

async function workerGet(p, headers = {}, method = 'GET', host = 'tide-current-map.cutlassfish.tokyo') {
 const r = await worker.fetch(new Request('https://' + host + p, {method, headers}), ENV, {});
 return {status: r.status, headers: Object.fromEntries([...r.headers].map(([k, v]) => [k.toLowerCase(), v])), body: Buffer.from(await r.arrayBuffer())};
}

// ---------- rental build ----------
const out = path.join(tmp, 'site');
const info = await buildRental(appDir, out);
fs.writeFileSync(path.join(out, 'api/map-config/config.php'), "<?php\nreturn array('GOOGLE_MAPS_BROWSER_KEY' => 'TEST-KEY', 'GOOGLE_MAPS_ENABLED' => 'true');\n");
execFileSync('chmod', ['-R', 'a+rX', out]);

function get(port, p, headers = {}, method = 'GET') {
 return new Promise((resolve, reject) => {
  const req = http.request({host: '127.0.0.1', port, path: p, method, headers: {Host: 'tide-current-map.cutlassfish.tokyo', 'X-Forwarded-Proto': 'https', ...headers}, agent: false}, res => {
   const chunks = []; res.on('data', c => chunks.push(c));
   res.on('end', () => resolve({status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks)}));
  });
  req.on('error', reject); req.setTimeout(20000, () => req.destroy(Error('timeout ' + p))); req.end();
 });
}
async function waitPort(port) {
 for (let i = 0; i < 100; i++) { try { await get(port, '/index.html'); return; } catch { await new Promise(r => setTimeout(r, 100)); } }
 throw Error('server on ' + port + ' did not start');
}
function start(cmd, argv, opts) {
 const p = spawn(cmd, argv, {stdio: ['ignore', 'ignore', 'pipe'], ...opts});
 let err = ''; p.stderr.on('data', d => { err += d; });
 cleanup.push(() => p.kill('SIGTERM'));
 return {proc: p, err: () => err};
}

// ---------- routes ----------
const index = JSON.parse(fs.readFileSync(path.join(out, 'api/harmonic/index.json'), 'utf8'));
const html = fs.readFileSync(path.join(out, 'index.html'), 'utf8');
const staticRoutes = ['/', '/index.html', '/app.js', '/app.js?v=' + info.revision, '/app.css', '/app.css?v=' + info.revision, '/geometry.js', '/coverage.js', '/chart.js',
 '/tide.js', '/clock.js', '/google-guard.js', '/map-gestures.js', '/harmonic.js', '/currents.js', '/spots.js', '/flow-layer.js',
 '/favicon.ico', '/favicon-32.png', '/apple-touch-icon.png', '/icon-192.png', '/icon-512.png?v=' + info.iconRevision, '/site.webmanifest', '/brand-logo.png',
 '/coastal-map.json', '/overview-map.json', '/overview-map.webp', '/coastal-map.webp'];
const harmonicRoutes = ['/api/harmonic/index.json'];
const gzRoutes = [];
for (const g of index.grids) {
 harmonicRoutes.push(g.meta);
 const ts = Object.keys(g.tiles).map(Number).sort((a, b) => a - b), pick = [ts[0], ts[Math.floor(ts.length / 2)], ts.at(-1)];
 for (const t of new Set(pick)) { harmonicRoutes.push(g.tileBase + '.t' + t + '.gz'); gzRoutes.push(g.tileBase + '.t' + t + '.gz'); }
 harmonicRoutes.push(g.tileBase + '.t' + ts[1] + '.bin');
 let missing = 0; while (g.tiles[missing] !== undefined) missing++;
 harmonicRoutes.push(g.tileBase + '.t' + missing + '.gz', g.tileBase + '.t' + missing + '.bin');
}
const notFound = ['/nope', '/app.html', '/data/TK-2026.txt', '/api/', '/api/harmonic/', '/api/harmonic', '/api/harmonic/nope.bin', '/api/harmonic/nope.json',
 '/api/current/', '/api/current/index.php', '/api/map-config/config.php', '/api/_lib/common.php', '/api/_lib/tide/TK-2026.txt', '/api/_lib/stations.json',
 '/.htaccess', '/api/harmonic/.htaccess', '/cache/', '/_errors/404.php', '/app.js/', '/index.php'];
const apiRoutes = ['/api/tide?date=2026-11-03&station=TK&v=2', '/api/tide?date=2026-11-03&station=Z1&v=2', '/api/tide?date=2026-06-15&station=CS&v=2',
 '/api/tide?date=2026-12-31&station=MR&v=2', '/api/tide?date=2026-01-01&station=TT', '/api/tide?date=2026-03-01&station=ZF', '/api/tide?date=2026-05-01',
 '/api/tide?date=2026-05-01&station=', '/api/tide?date=2026-05-01&station=TK&station=XX', '/api/tide?date=2026-11-03&hour=%2023',
 '/api/current?date=2026-10-24&hour=10', '/api/current?date=2026-10-24&hour=8', '/api/current?date=2026-10-24&hour=+9', '/api/current?date=2026-10-24&hour=1e1',
 '/api/current?date=2026-10-24&hour=12.0', '/api/current?date=2026-10-24&hour=0x0b', '/api/current?hour=10&date=2026-10-24&date=2020-01-01',
 // invalid → 400
 '/api/current', '/api/current?date=2026-02-30&hour=1', '/api/current?date=2026-1-01&hour=1', '/api/current?date=2026-10-24&hour=24',
 '/api/current?date=2026-10-24&hour=-1', '/api/current?date=2026-10-24&hour=abc', '/api/current?date=2026-10-24&hour=1.5', '/api/current?date=1899-12-31&hour=1',
 '/api/current?date=2101-01-01&hour=1', '/api/current?date=2026-10-24%0A&hour=1', '/api/current?date=%EF%BC%92026-10-24&hour=1', '/api/tide?date=2026-11-03&station=XX',
 '/api/tide?date=2026-11-03&station=tk', '/api/tide?date=2026-11-03&hour=x&station=XX', '/api/tide?date=20261103'];
const mapCases = [
 {name: 'same-origin GET', headers: {}},
 {name: 'same-origin fetch headers', headers: {'Sec-Fetch-Site': 'same-origin', Referer: 'https://tide-current-map.cutlassfish.tokyo/?x=1'}},
 {name: 'foreign Origin', headers: {Origin: 'https://evil.example'}},
 {name: 'same Origin', headers: {Origin: 'https://tide-current-map.cutlassfish.tokyo'}},
 {name: 'cross-site', headers: {'Sec-Fetch-Site': 'cross-site'}},
 {name: 'foreign Referer', headers: {Referer: 'https://evil.example/page'}},
 {name: 'bad Referer', headers: {Referer: 'not a url'}},
 {name: 'POST', headers: {}, method: 'POST'},
 {name: 'other host', headers: {}, host: 'evil.example'},
];

let pass = 0, fail = 0;
const failures = [];
function check(label, ok, detail) { if (ok) pass++; else { fail++; failures.push(label + (detail ? ' — ' + detail : '')); } }
const H = ['content-type', 'cache-control', 'x-content-type-options', 'referrer-policy'];
const norm = v => v === undefined || v === null ? null : String(v).replace(/;\s*/g, '; ').toLowerCase();

async function compareServer(label, port, {gzipProbe}) {
 const before = pass + fail;
 for (const p of [...staticRoutes, ...harmonicRoutes, ...notFound]) {
  if (process.env.TRACE) console.log(label, p);
  const [w, r] = await Promise.all([workerGet(p), get(port, p)]);
  check(`${label} ${p} status`, w.status === r.status, `${w.status} vs ${r.status}`);
  if (w.status === 404 && r.status === 404) { check(`${label} ${p} 404 body`, r.body.toString() === 'Not found' && norm(r.headers['content-type']) === norm(w.headers['content-type']), r.body.toString().slice(0, 80) + ' ' + r.headers['content-type']); continue; }
  for (const h of H) check(`${label} ${p} ${h}`, norm(w.headers[h]) === norm(r.headers[h]), `${w.headers[h]} vs ${r.headers[h]}`);
  check(`${label} ${p} no content-encoding`, !r.headers['content-encoding'], r.headers['content-encoding']);
  check(`${label} ${p} body`, w.body.equals(r.body), `${w.body.length} vs ${r.body.length} bytes`);
 }
 for (const p of apiRoutes) {
  if (process.env.TRACE) console.log(label, p);
  const [w, r] = await Promise.all([workerGet(p), get(port, p)]);
  check(`${label} ${p} status`, w.status === r.status, `${w.status} vs ${r.status}: ${r.body.toString().slice(0, 200)}`);
  // The Worker drops Cache-Control when it answers from its in-memory memo (a repeat of the
  // same date/hour/station); the first answer carries public, max-age=3600, which PHP always sends.
  if (w.status === 200 && !w.headers['cache-control']) w.headers['cache-control'] = 'public, max-age=3600';
  for (const h of ['content-type', 'cache-control']) check(`${label} ${p} ${h}`, norm(w.headers[h]) === norm(r.headers[h]), `${w.headers[h]} vs ${r.headers[h]}`);
  let a, b; try { a = JSON.parse(w.body); b = JSON.parse(r.body); } catch (e) { check(`${label} ${p} json`, false, e.message + ' ' + r.body.toString().slice(0, 200)); continue; }
  check(`${label} ${p} json`, JSON.stringify(a) === JSON.stringify(b), JSON.stringify(a).slice(0, 120) + ' vs ' + JSON.stringify(b).slice(0, 120));
  if (p.startsWith('/api/current?date=2026-10-24&hour=10')) check(`${label} ${p} bytes`, w.body.equals(r.body));
 }
 for (const c of mapCases) {
  const w = await workerGet('/api/map-config', c.headers, c.method, c.host);
  const r = await get(port, '/api/map-config', {...c.headers, ...(c.host ? {Host: c.host} : {})}, c.method);
  check(`${label} map-config ${c.name} status`, w.status === r.status);
  for (const h of ['content-type', 'cache-control', 'x-content-type-options']) check(`${label} map-config ${c.name} ${h}`, norm(w.headers[h]) === norm(r.headers[h]), `${w.headers[h]} vs ${r.headers[h]}`);
  check(`${label} map-config ${c.name} json`, w.body.toString() === r.body.toString(), w.body + ' vs ' + r.body);
 }
 // Staging origin is allowed on the rental server (the Worker only knows production).
 const stg = await get(port, '/api/map-config', {Host: 'tide-stg.cutlassfish.tokyo', Referer: 'https://tide-stg.cutlassfish.tokyo/'});
 check(`${label} map-config staging origin`, stg.body.toString() === '{"provider":"google","apiKey":"TEST-KEY"}', stg.body.toString());
 const plain = await get(port, '/api/map-config', {'X-Forwarded-Proto': 'http'});
 check(`${label} map-config plain http`, plain.body.toString() === '{"provider":"standard"}', plain.body.toString());
 if (gzipProbe) for (const p of gzRoutes.slice(0, 3)) {
  // Even when the client accepts gzip, the tile must arrive as the same raw gzip bytes.
  const r = await get(port, p, {'Accept-Encoding': 'gzip, deflate'}), w = await workerGet(p);
  const body = r.headers['content-encoding'] === 'gzip' ? zlib.gunzipSync(r.body) : r.body;
  check(`${label} ${p} with Accept-Encoding`, w.body.equals(body) && !/gzip/.test(r.headers['content-type'] || ''), `encoding=${r.headers['content-encoding']} type=${r.headers['content-type']}`);
 }
 console.log(`${label}: ${pass + fail - before} checks`);
}

// ---------- php -S ----------
const phpPort = 18000 + Math.floor(Math.random() * 1000);
const php = start('php', ['-S', '127.0.0.1:' + phpPort, '-t', out, path.join(HERE, 'router.php')]);
await waitPort(phpPort);
await compareServer('php -S', phpPort, {gzipProbe: true});
const routeCount = staticRoutes.length + harmonicRoutes.length + notFound.length + apiRoutes.length + mapCases.length + 2;

// ---------- Apache + real .htaccess (optional) ----------
const apacheBin = ['/usr/sbin/apache2', '/usr/sbin/httpd'].find(f => fs.existsSync(f));
const modDir = ['/usr/lib/apache2/modules', '/usr/lib64/httpd/modules'].find(f => fs.existsSync(f));
const libphp = modDir && fs.readdirSync(modDir).find(f => /^libphp.*\.so$/.test(f));
if (args.includes('--no-apache') || !apacheBin || !libphp) console.log('Apache: skipped' + (args.includes('--no-apache') ? '' : ' (apache2 or mod_php not installed)'));
else {
 const port = phpPort + 1000, run = path.join(tmp, 'apache');
 fs.mkdirSync(run, {recursive: true});
 const mods = ['mpm_prefork', 'authz_core', 'mime', 'dir', 'rewrite', 'headers', 'env', 'deflate', 'filter', 'setenvif', 'alias'];
 fs.writeFileSync(path.join(run, 'httpd.conf'), [
  'ServerName localhost', `Listen 127.0.0.1:${port}`, `PidFile ${run}/httpd.pid`, `ErrorLog ${run}/error.log`, 'LogLevel warn', `DefaultRuntimeDir ${run}`,
  ...mods.map(m => `LoadModule ${m}_module ${modDir}/mod_${m}.so`), `LoadModule php_module ${modDir}/${libphp}`,
  'User www-data', 'Group www-data', 'TypesConfig /etc/mime.types',
  // A deliberately unfriendly shared-host setup: .gz announced as Content-Encoding, DEFLATE on.
  'AddEncoding x-gzip .gz', 'AddType application/x-gzip .gz', 'AddDefaultCharset UTF-8',
  'AddOutputFilterByType DEFLATE text/html text/css text/javascript application/json application/octet-stream application/x-gzip',
  `DocumentRoot ${out}`, `<Directory ${out}>`, '  AllowOverride All', '  Require all granted', '</Directory>',
  '<FilesMatch "\\.php$">', '  SetHandler application/x-httpd-php', '</FilesMatch>',
 ].join('\n'));
 const ap = start(apacheBin, ['-X', '-f', path.join(run, 'httpd.conf')], {env: {...process.env, APACHE_RUN_DIR: run}});
 try { await waitPort(port); } catch (e) { console.log(ap.err()); throw e; }
 await compareServer('Apache', port, {gzipProbe: true});
 // Without mod_rewrite-style rewrites the API still answers through the directory index.
 const r = await get(port, '/api/current/?date=2026-10-24&hour=10');
 check('Apache /api/current/ (directory index) — 404 by design via .htaccess', r.status === 404);
}

// ---------- browser ----------
if (shot) {
 globalThis.fetch = realFetch;
 const require = createRequire(import.meta.url);
 const {chromium} = require('playwright');
 const browser = await chromium.launch();
 const page = await browser.newPage({viewport: {width: 1280, height: 900}});
 const errors = [], requests = [], bad = [];
 page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
 page.on('pageerror', e => errors.push('pageerror: ' + e.message));
 page.on('response', r => { const u = new URL(r.url()); if (u.port === String(phpPort)) { requests.push(u.pathname + u.search); if (r.status() >= 400) bad.push(r.status() + ' ' + u.pathname); } });
 await page.goto(`http://127.0.0.1:${phpPort}/`, {waitUntil: 'networkidle', timeout: 60000});
 await page.waitForTimeout(6000);
 const canvases = await page.evaluate(() => [...document.querySelectorAll('canvas')].map(c => {
  let lit = 0; try { const ctx = c.getContext('2d'); if (ctx && c.width && c.height) { const d = ctx.getImageData(0, 0, c.width, c.height).data; for (let i = 3; i < d.length; i += 4 * 97) if (d[i]) lit++; } } catch {}
  return {w: c.width, h: c.height, lit};
 }));
 const tilesLoaded = requests.filter(r => /^\/api\/harmonic\/.+\.t\d+\.gz$/.test(r)).length;
 const mapTiles = await page.evaluate(() => document.querySelectorAll('img').length);
 // Particles move: two screenshots of the page taken 700 ms apart differ (canvases with map
 // tiles from 地理院 are cross-origin, so they cannot be read back directly).
 const s1 = await page.screenshot(); await page.waitForTimeout(700); const s2 = await page.screenshot();
 const diff = !s1.equals(s2);
 await page.screenshot({path: shot});
 await browser.close();
 console.log(`Browser: console errors ${errors.length}, failed same-origin requests ${bad.length}, harmonic tiles loaded ${tilesLoaded}, canvases ${JSON.stringify(canvases)}, images ${mapTiles}, animation changes ${diff}`);
 if (errors.length) console.log('  ' + errors.join('\n  '));
 if (bad.length) console.log('  ' + bad.join('\n  '));
 check('browser: no console errors', errors.length === 0, errors.join(' | '));
 check('browser: no failed same-origin requests', bad.length === 0, bad.join(' | '));
 check('browser: harmonic tiles loaded', tilesLoaded > 0);
 check('browser: flow canvas animates', diff === true);
 console.log('Screenshot: ' + shot);
}

// SEO: same title / description / canonical as the Worker's HTML.
const t = s => (s.match(/<title>[^<]*<\/title>/) || [''])[0], d = s => (s.match(/<meta name="description"[^>]*>/) || [''])[0], c = s => (s.match(/<link rel="canonical"[^>]*>/) || ['(none)'])[0];
const wHtml = (await workerGet('/')).body.toString();
check('SEO title/description/canonical', t(wHtml) === t(html) && d(wHtml) === d(html) && c(wHtml) === c(html));
console.log(`SEO: ${t(html)} | canonical ${c(html)}`);

console.log(`\nRoutes per server: ${routeCount}; checks passed ${pass}, failed ${fail}`);
if (fail) { console.log('FAILURES:\n  ' + failures.join('\n  ')); process.exit(1); }
process.exit(0); // ends the php -S / Apache children (see the exit handler)
