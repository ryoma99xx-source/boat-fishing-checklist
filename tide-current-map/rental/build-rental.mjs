#!/usr/bin/env node
// Builds the 東京湾の潮と流れ app as plain files + PHP for a shared rental server
// (Apache/.htaccess + PHP 7.4+, no Node at runtime).
//
//   node tide-current-map/rental/build-rental.mjs <app-dir> <out-dir>
//
// <app-dir> is the app folder (tide-current-map/app on the app branch). Its sources and data
// are read as-is; nothing in it is modified. The output mirrors every route that the app's
// Worker (scripts/build.mjs) serves, byte for byte, at the same URLs.
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {fileURLToPath, pathToFileURL} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

// JS modules served by the Worker (text/javascript; charset=utf-8, no-cache).
export const JS_FILES = ['app.js', 'geometry.js', 'coverage.js', 'chart.js', 'tide.js', 'clock.js', 'google-guard.js', 'map-gestures.js',
 'harmonic.js', 'currents.js', 'spots.js', 'flow-layer.js'];
export const ICON_TYPES = {'favicon.ico': 'image/x-icon', 'favicon-32.png': 'image/png', 'apple-touch-icon.png': 'image/png', 'icon-192.png': 'image/png', 'icon-512.png': 'image/png'};
// Every literal path the Worker routes. A new route in build.mjs makes this build fail
// instead of silently answering 404 on the rental server.
const KNOWN_ROUTES = new Set(['/', '/index.html', '/clock.js', '/google-guard.js', '/map-gestures.js', '/api/map-config', '/site.webmanifest',
 '/brand-logo.png', '/tide.js', '/coastal-map.json', '/overview-map.json', '/overview-map.webp', '/coastal-map.webp', '/api/current', '/api/tide',
 '/app.js', '/geometry.js', '/coverage.js', '/chart.js', '/app.css']);
const KNOWN_MODULES = ['harmonic.js', 'currents.js', 'spots.js', 'flow-layer.js'];
const TIDE_CODES = ['TK', 'Z1', 'MR', 'TT', 'ZF', 'CS'];

function checkRoutes(buildSource) {
 const found = [...buildSource.matchAll(/path(?:===|!==)'([^']+)'/g)].map(m => m[1]);
 const unknown = found.filter(p => !KNOWN_ROUTES.has(p));
 if (unknown.length) throw Error('scripts/build.mjs serves routes this rental build does not know: ' + unknown.join(', '));
 const mod = buildSource.match(/for\(const f of (\[[^\]]*\])\)modules\['\/'\+f\]/);
 if (!mod || JSON.stringify(JSON.parse(mod[1].replaceAll("'", '"'))) !== JSON.stringify(KNOWN_MODULES)) throw Error('scripts/build.mjs module list changed; update build-rental.mjs');
 for (const marker of ["path.startsWith('/api/harmonic/')", 'harmonicResponse(path,HARMONIC)', "html=htmlSource.replace('/app.js','/app.js?v='+revision)"])
  if (!buildSource.includes(marker)) throw Error('scripts/build.mjs changed (' + marker + '); review build-rental.mjs');
}

export async function buildRental(appDir, outDir) {
 appDir = path.resolve(appDir); outDir = path.resolve(outDir);
 const read = f => fs.readFileSync(path.join(appDir, f), 'utf8');
 const data = f => path.join(appDir, 'data', f);
 checkRoutes(read('scripts/build.mjs'));
 if (fs.existsSync(outDir) && fs.readdirSync(outDir).length) throw Error('output directory is not empty: ' + outDir);
 const write = (rel, body) => { const p = path.join(outDir, rel); fs.mkdirSync(path.dirname(p), {recursive: true}); fs.writeFileSync(p, body); };
 const copy = (rel, src) => { const p = path.join(outDir, rel); fs.mkdirSync(path.dirname(p), {recursive: true}); fs.copyFileSync(src, p); };

 // --- same computations as scripts/build.mjs ---
 const js = read('app.js'), css = read('app.css');
 const modules = {}; for (const f of KNOWN_MODULES) modules['/' + f] = read(f);
 const icons = {}; for (const [name, type] of Object.entries(ICON_TYPES)) icons['/' + name] = {type, data: fs.readFileSync(data('site-icons/' + name)).toString('base64')};
 const iconRevision = createHash('sha256').update(JSON.stringify(icons)).digest('hex').slice(0, 12);
 const revision = createHash('sha256').update(js + css + Object.values(modules).join('')).digest('hex').slice(0, 12);
 const html = read('app.html').replace('/app.js', '/app.js?v=' + revision).replace('/app.css', '/app.css?v=' + revision).replaceAll('__ICON_VERSION__', iconRevision);
 const webmanifest = JSON.stringify({id: '/', name: '東京湾の潮と流れ | TIDE & CURRENT MAP', short_name: '潮流マップ', lang: 'ja', start_url: '/', scope: '/', display: 'standalone', background_color: '#06080f', theme_color: '#06080f', icons: [{src: '/icon-192.png?v=' + iconRevision, sizes: '192x192', type: 'image/png', purpose: 'any'}, {src: '/icon-512.png?v=' + iconRevision, sizes: '512x512', type: 'image/png', purpose: 'any'}]});
 const coastalMap = JSON.stringify(JSON.parse(read('data/coastal-model.json')).map);

 write('index.html', html);
 for (const f of JS_FILES) write(f, read(f));
 write('app.css', css);
 write('site.webmanifest', webmanifest);
 for (const name of Object.keys(ICON_TYPES)) copy(name, data('site-icons/' + name));
 copy('brand-logo.png', data('brand-logo.png'));
 write('coastal-map.json', coastalMap);
 write('overview-map.json', read('data/overview-map.json'));
 // The Worker answers these with an empty 200 body when the source image is absent.
 for (const f of ['overview-map.webp', 'coastal-map.webp']) fs.existsSync(data(f)) ? copy(f, data(f)) : write(f, '');

 // --- harmonic grids: packed by the app's own packer (same bytes, same content-hashed URLs) ---
 const {packHarmonic} = await import(pathToFileURL(path.join(appDir, 'worker/harmonic-build.mjs')).href);
 const harmonic = packHarmonic(path.join(appDir, 'data'));
 if (!JSON.parse(harmonic.index).grids.length) throw Error('No harmonic current grid in data/');
 write('api/harmonic/index.json', harmonic.index);
 let tiles = 0;
 for (const [url, file] of Object.entries(harmonic.files)) {
  if (!url.startsWith('/api/harmonic/') || url.includes('..')) throw Error('unexpected harmonic path ' + url);
  const rel = url.slice(1);
  if (file.type === 'json') write(rel, file.text);
  else if (file.type === 'gz') {
   const gz = Buffer.from(file.gz, 'base64');
   write(rel, gz); // raw gzip bytes, served without Content-Encoding (see .htaccess)
   if (rel.endsWith('.gz')) write(rel.slice(0, -3) + '.bin', gunzipSync(gz)); // the Worker's <tile>.bin fallback
   tiles++;
  } else throw Error('unknown harmonic file type ' + file.type);
 }

 // --- API (PHP) ---
 const {TIDE_STATIONS} = await import(pathToFileURL(path.join(appDir, 'worker/api.js')).href);
 const lib = 'api/_lib/';
 write(lib + 'stations.json', JSON.stringify(TIDE_STATIONS));
 for (const code of TIDE_CODES) if (fs.existsSync(data(code + '-2026.txt'))) copy(lib + 'tide/' + code + '-2026.txt', data(code + '-2026.txt'));
 let snapshots = 0;
 for (const f of fs.readdirSync(path.join(appDir, 'data'))) if (f.startsWith('current-')) {
  const d = JSON.parse(fs.readFileSync(data(f), 'utf8'));
  // Key = date + '/' + hour, as the Worker; the body is what Response.json(snapshot) sends.
  write(lib + 'snapshots/' + d.date + '_' + d.hour + '.json', JSON.stringify(d)); snapshots++;
 }
 const tpl = f => fs.readFileSync(path.join(HERE, 'php', f));
 write(lib + 'common.php', tpl('common.php'));
 write(lib + '.htaccess', tpl('deny.htaccess'));
 write('api/current/index.php', tpl('current.php'));
 write('api/tide/index.php', tpl('tide.php'));
 write('api/map-config/index.php', tpl('map-config.php'));
 write('_errors/404.php', tpl('404.php'));
 write('.htaccess', tpl('root.htaccess'));
 write('api/harmonic/.htaccess', tpl('harmonic.htaccess'));
 return {revision, iconRevision, tiles, snapshots, grids: JSON.parse(harmonic.index).grids.map(g => g.name)};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
 const [appDir, outDir] = process.argv.slice(2);
 if (!appDir || !outDir) { console.error('usage: node build-rental.mjs <app-dir> <out-dir>'); process.exit(2); }
 const info = await buildRental(appDir, outDir);
 console.log(`Built rental site in ${path.resolve(outDir)}: revision ${info.revision}, icons ${info.iconRevision}, grids ${info.grids.join(',')}, ${info.tiles} tiles (+.bin), ${info.snapshots} current snapshots`);
}
