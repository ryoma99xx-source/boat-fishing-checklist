#!/usr/bin/env node
// Opens each mirrored site (served locally by serve.py) and the live site in Playwright
// Chromium at 390px wide, clicks around a little, and reports console errors, failed
// same-origin requests and RSC fetches. Screenshots go to <out-dir>.
//
//   node sites/test/browser.mjs <out-dir> [reel-line-manager dont-forget-anything tenya-simulator] [--no-live]
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/opt/node-tools/node_modules/playwright'); }
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const outDir = path.resolve(args[0] || '.');
const sites = args.slice(1).filter(a => !a.startsWith('--'));
const withLive = !args.includes('--no-live');
fs.mkdirSync(outDir, {recursive: true});

// Per-site interactions. `shot(name)` saves a 390px-wide full-page screenshot.
const SCENARIOS = {
  'reel-line-manager': async (page, shot) => {
    await shot('top');
    await clickText(page, 'button', '共有メニューを開く');
    await page.keyboard.press('Escape');
    const name = page.locator('#newReelSection input[type=text], #newReelSection input:not([type])').first();
    if (await name.count()) await name.fill('テスト用リール');
    await clickText(page, 'button', 'リールを新規保存');
    await page.waitForTimeout(800);
    await shot('after-save');
    await page.goto(new URL('help.html', page.url()).href, {waitUntil: 'networkidle'});
    await shot('help');
  },
  'dont-forget-anything': async (page, shot) => {
    await shot('top');
    const box = page.locator('input[type=checkbox]:visible').first();
    if (await box.count()) await box.click();
    await clickText(page, 'button', '☑︎を全部外す');
    await page.goto(new URL('edit.html', page.url()).href, {waitUntil: 'networkidle'});
    await shot('edit');
    await page.goto(new URL('help.html', page.url()).href, {waitUntil: 'networkidle'});
    await shot('help');
  },
  'tenya-simulator': async (page, shot) => {
    await page.waitForFunction(() => !/計算中/.test(document.body.innerText), null, {timeout: 60000}).catch(() => {});
    await shot('top');
    for (const t of ['条件 B', '海況', '詳細', '条件 A', '操作']) await clickText(page, 'button', t);
    await clickLabel(page, 'テンヤを動かす');
    await page.waitForTimeout(3000);
    await clickLabel(page, '1コマ送り');
    await clickText(page, 'button', '海中全景・ラインの形を見る');
    await page.waitForTimeout(1000);
    await shot('after-run');
    await clickLabel(page, '初期位置へ戻る');
    await page.goto(new URL('/versions/1.5.4', page.url()).href, {waitUntil: 'networkidle'});
    await page.waitForTimeout(2000);
    await shot('versions-1.5.4');
    const r = await page.goto(new URL('/nope', page.url()).href, {waitUntil: 'networkidle'});
    log(`    /nope -> ${r.status()}`);
    await shot('not-found');
  },
};

async function clickText(page, sel, text) {
  const el = page.locator(sel, {hasText: text}).filter({visible: true}).first();
  if (await el.count()) { await el.click({timeout: 5000}).catch(e => log('    click failed: ' + text + ' ' + e.message.split('\n')[0])); await page.waitForTimeout(400); }
  else log('    (no visible ' + sel + ' "' + text + '")');
}
async function clickLabel(page, label) {
  const el = page.getByLabel(label, {exact: true}).filter({visible: true}).first();
  if (await el.count()) { await el.click({timeout: 5000}).catch(e => log('    click failed: ' + label + ' ' + e.message.split('\n')[0])); await page.waitForTimeout(400); }
  else log('    (no visible "' + label + '")');
}
function log(s) { console.log(s); }

function serve(dir, port) {
  const p = spawn('python3', ['-I', path.join(HERE, 'serve.py'), dir, String(port)], {stdio: 'ignore'});
  process.on('exit', () => p.kill());
  return new Promise(r => setTimeout(r, 700));
}

async function visit(browser, site, base, label) {
  const origin = new URL(base).origin;
  const ctx = await browser.newContext({viewport: {width: 390, height: 844}, deviceScaleFactor: 1, serviceWorkers: 'block'});
  const page = await ctx.newPage();
  const res = {consoleErrors: [], failedSame: [], failedCross: [], rsc: [], sameOrigin: new Set()};
  page.on('dialog', d => d.dismiss().catch(() => {}));
  page.on('console', m => { if (m.type() === 'error') res.consoleErrors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => res.consoleErrors.push('pageerror: ' + e.message.slice(0, 200)));
  page.on('request', r => { if (/[?&]_rsc=|\.rsc(\?|$)/.test(r.url()) || r.headers()['rsc']) res.rsc.push(r.url()); });
  page.on('requestfailed', r => (new URL(r.url()).origin === origin ? res.failedSame : res.failedCross).push(r.url() + ' ' + (r.failure()?.errorText || '')));
  page.on('response', r => {
    const u = new URL(r.url());
    if (u.origin === origin) res.sameOrigin.add(u.pathname);
    if (r.status() >= 400 && !(u.pathname === '/nope' && r.status() === 404)) (u.origin === origin ? res.failedSame : res.failedCross).push(r.status() + ' ' + r.url());
  });
  await page.goto(base + '/', {waitUntil: 'networkidle', timeout: 60000});
  const shots = [];
  await SCENARIOS[site](page, async name => {
    const f = path.join(outDir, `${site}-${label}-${name}.png`);
    await page.screenshot({path: f, fullPage: true});
    shots.push(f);
  });
  await ctx.close();
  return {...res, shots};
}

const browser = await playwright.chromium.launch(process.env.HTTPS_PROXY ? {proxy: {server: process.env.HTTPS_PROXY, bypass: '127.0.0.1,localhost'}} : {});
let port = 8201, bad = 0;
const summary = {};
for (const site of sites.length ? sites : Object.keys(SCENARIOS)) {
  log('== ' + site);
  await serve(path.join(HERE, '..', site, 'public'), port);
  const targets = [['mirror', 'http://127.0.0.1:' + port++]];
  if (withLive) targets.push(['live', `https://${site}.cutlassfish.tokyo`]);
  for (const [label, base] of targets) {
    const r = await visit(browser, site, base, label);
    log(`  [${label}] console errors: ${r.consoleErrors.length}${r.consoleErrors.length ? '\n    ' + r.consoleErrors.join('\n    ') : ''}`);
    log(`  [${label}] failed same-origin: ${r.failedSame.length}${r.failedSame.length ? '\n    ' + r.failedSame.join('\n    ') : ''}`);
    log(`  [${label}] failed cross-origin (ignored offline): ${r.failedCross.length}${r.failedCross.length ? '\n    ' + r.failedCross.slice(0, 8).join('\n    ') : ''}`);
    log(`  [${label}] RSC fetches: ${r.rsc.length ? r.rsc.join(', ') : 'none'}`);
    log(`  [${label}] same-origin paths requested: ${[...r.sameOrigin].sort().join(' ')}`);
    log(`  [${label}] screenshots: ${r.shots.join(' ')}`);
    if (label === 'mirror' && r.failedSame.length) bad++;
    summary[site + ':' + label] = [...r.sameOrigin];
  }
}
// Every same-origin path the live site served during the session must exist in the mirror.
if (withLive) for (const site of sites.length ? sites : Object.keys(SCENARIOS)) {
  const mirror = new Set(summary[site + ':mirror']);
  const extra = summary[site + ':live'].filter(p => !mirror.has(p) && !p.startsWith('/cdn-cgi/'));
  log(`${site}: paths seen live but not requested from the mirror: ${extra.length ? extra.join(' ') : 'none'}`);
}
await browser.close();
process.exit(bad ? 1 : 0);
