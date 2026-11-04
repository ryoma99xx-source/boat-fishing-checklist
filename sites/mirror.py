#!/usr/bin/env python3
"""Mirror the published output of a small static site into sites/<subdomain>/public/.

    python3 -I sites/mirror.py reel-line-manager [dont-forget-anything tenya-simulator ...]

Starts at "/" of https://<subdomain>.cutlassfish.tokyo and follows every same-origin
reference it can find:
  * HTML: src/href/srcset/poster/data-src/content attributes, same-origin <a> pages,
    inline <style> url(...), quoted paths inside inline <script> (RSC payload included)
  * CSS: url(...) and @import
  * JS: quoted "/..." paths with a file extension and relative "./chunk-xxx.js" names
  * web manifests: icons, screenshots, shortcuts, start_url
  * probes: robots.txt, sitemap.xml, favicon.ico, common service worker / manifest names

Probed or guessed paths are kept only when the server really has them (the ChatGPT Sites
hosting answers unknown paths with the index page, so an HTML answer for a non-HTML path,
or the same body as "/" for another path, is treated as "not there").

The only change made to file contents: Cloudflare's injected bot-management snippet
(<script>…__CF$cv$params…/cdn-cgi/challenge-platform…</script>) is removed from HTML,
because /cdn-cgi/ only exists behind Cloudflare. Everything else is saved byte for byte.

The .htaccess files in public/ are written by hand and are left alone by this script
(it overwrites mirrored files but never deletes anything).

Writes sites/<subdomain>/public/... plus sites/<subdomain>/mirror-manifest.json
(path, content type, size, sha256, how it was found, modifications). Python stdlib only.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA = 'cutlassfish-site-mirror/1.0'
DELAY = 0.4  # seconds between requests
HERE = os.path.dirname(os.path.abspath(__file__))

PROBES = ['/robots.txt', '/sitemap.xml', '/favicon.ico', '/manifest.json', '/manifest.webmanifest',
          '/site.webmanifest', '/sw.js', '/service-worker.js', '/apple-touch-icon.png', '/404.html']
ASSET_EXT = r'(?:gz|br|bin|f64|f32|dat|csv|geojson|glb|gltf|pbf|onnx|js|mjs|css|json|webmanifest|png|jpe?g|gif|webp|avif|svg|ico|woff2?|ttf|otf|wasm|mp3|mp4|webm|txt|xml|html|map)'
JS_ABS = re.compile(r'''["'`](/(?!/)[A-Za-z0-9_\-./@~%]+\.[A-Za-z0-9]{1,8})(?:\?[^"'`\s]*)?["'`]''')
JS_REL = re.compile(r'''["'`](\.{1,2}/[A-Za-z0-9_\-./@~%]+\.''' + ASSET_EXT + r''')["'`]''')
JS_BARE = re.compile(r'''["'`]([A-Za-z0-9_\-][A-Za-z0-9_\-./]*\.''' + ASSET_EXT + r''')["'`]''')
ROUTE_PATTERN = re.compile(r'''pattern:[`"'](/[^`"'\[\]:*]*)[`"']''')  # static routes in an app route manifest
CSS_URL = re.compile(r'''url\(\s*["']?([^"')]+?)["']?\s*\)|@import\s+["']([^"']+)["']''')
CF_SNIPPET = re.compile(r'<script>\(function\(\)\{function c\(\)\{var b=a\.contentDocument.*?__CF\$cv\$params.*?</script>', re.S)


class Refs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.assets, self.pages, self.inline = [], [], []
        self._in = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ('src', 'poster', 'data-src'):
            if a.get(k):
                self.assets.append(a[k])
        for k in ('srcset', 'imagesrcset'):
            if a.get(k):
                self.assets += [p.strip().split(' ')[0] for p in a[k].split(',') if p.strip()]
        if tag == 'a' and a.get('href'):
            self.pages.append(a['href'])
        elif tag in ('link', 'area', 'base') and a.get('href'):
            self.assets.append(a['href'])
        if tag == 'meta' and a.get('content', '').startswith('/'):
            self.assets.append(a['content'])
        if tag == 'meta' and (a.get('property') or a.get('name') or '') in ('og:image', 'twitter:image'):
            self.assets.append(a.get('content', ''))
        if a.get('style'):
            self.inline.append(('css', a['style']))
        if tag in ('script', 'style'):
            self._in = 'js' if tag == 'script' else 'css'

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._in = None

    def handle_data(self, data):
        if self._in:
            self.inline.append((self._in, data))


class Mirror:
    def __init__(self, sub):
        self.sub = sub
        self.origin = 'https://%s.cutlassfish.tokyo' % sub
        self.out = os.path.join(HERE, sub, 'public')
        self.seen = {}      # path -> record
        self.misses = {}    # path -> reason (only for paths we were sure about)
        self.queue = []     # (path, found_by, certain)
        self.root_body = None
        self.fallback = None  # True when unknown paths answer 200 with the index page

    # ---------- network ----------
    def fetch(self, path):
        time.sleep(DELAY)
        req = urllib.request.Request(self.origin + path, headers={'User-Agent': UA, 'Accept': '*/*'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.headers.get('Content-Type', ''), r.read()
        except urllib.error.HTTPError as e:
            body = e.read()
            if e.code in (401, 403, 429, 503) or b'challenge-platform' in body[:4000] and e.code >= 400:
                raise SystemExit('BLOCKED or challenged: %s -> HTTP %s. Stopping (not working around it).' % (self.origin + path, e.code))
            return e.code, e.headers.get('Content-Type', ''), body

    # ---------- url handling ----------
    def to_path(self, ref, base):
        ref = (ref or '').strip()
        if not ref or ref.startswith(('#', 'data:', 'blob:', 'javascript:', 'mailto:', 'tel:', 'about:')):
            return None
        u = urllib.parse.urlsplit(urllib.parse.urljoin(self.origin + base, ref))
        if '%s://%s' % (u.scheme, u.netloc) != self.origin:
            return None
        p = urllib.parse.unquote(u.path) or '/'
        if p.startswith('/cdn-cgi/'):
            return None
        return p

    def add(self, ref, base, why, certain=True):
        p = self.to_path(ref, base)
        if p and p not in self.seen and p not in self.misses and all(q[0] != p for q in self.queue):
            self.queue.append((p, why, certain))

    @staticmethod
    def local(path, ctype=''):
        if path.endswith('/'):
            return path.lstrip('/') + 'index.html'
        last = path.rsplit('/', 1)[-1]
        if 'html' in ctype and not last.endswith(('.html', '.htm')):
            # an extension-less page route (e.g. /versions/1.5.4) -> versions/1.5.4.html,
            # served at the original URL by a rewrite in .htaccess
            return path.lstrip('/') + '.html'
        return path.lstrip('/')

    # ---------- parsing ----------
    def scan_js(self, text, base, why):
        for m in ROUTE_PATTERN.finditer(text):
            self.add(m.group(1), '/', why + ' (route manifest)')
        for m in JS_ABS.finditer(text):
            p = m.group(1)
            self.add(p, base, why, certain=p.startswith('/_next/static/') or re.search(r'\.' + ASSET_EXT + '$', p) is not None)
        for m in JS_REL.finditer(text):
            self.add(m.group(1), base, why, certain=False)
        for m in JS_BARE.finditer(text):
            s = m.group(1)
            if '/' in s or re.search(r'-[A-Za-z0-9_]{6,}\.(?:m?js|css)$', s) or s.endswith(('.js', '.css', '.json', '.html', '.png', '.webmanifest')):
                self.add(s, base, why, certain=False)          # relative to the script
                self.add(s, '/', why + ' (doc-relative)', certain=False)

    def scan_css(self, text, base, why):
        for m in CSS_URL.finditer(text):
            self.add(m.group(1) or m.group(2), base, why)

    def parse(self, path, ctype, body):
        why = 'ref from ' + path
        text = body.decode('utf-8', 'replace')
        if 'html' in ctype:
            p = Refs()
            p.feed(text)
            for r in p.assets:
                self.add(r, path, why)
            for r in p.pages:
                self.add(r, path, 'link from ' + path)
            for kind, t in p.inline:
                (self.scan_js if kind == 'js' else self.scan_css)(t, path, why + ' (inline)')
        elif 'css' in ctype:
            self.scan_css(text, path, why)
        elif 'javascript' in ctype:
            self.scan_js(text, path, why)
        elif path.endswith(('.webmanifest', 'manifest.json')) or 'manifest' in ctype:
            try:
                m = json.loads(text)
            except ValueError:
                return
            for k in ('icons', 'screenshots'):
                for i in m.get(k) or []:
                    self.add(i.get('src'), path, why)
            for s in m.get('shortcuts') or []:
                self.add(s.get('url'), path, why)
                for i in s.get('icons') or []:
                    self.add(i.get('src'), path, why)
            if m.get('start_url'):
                self.add(m['start_url'], path, why)

    # ---------- main ----------
    def looks_missing(self, path, status, ctype, body):
        if status != 200:
            return 'HTTP %s' % status
        if path != '/' and body == self.root_body:
            return 'index fallback (same body as /)'
        if self.fallback and 'html' in ctype and not path.endswith(('/', '.html', '.htm')):
            return 'HTML answer for a non-HTML path (index fallback)'
        return None

    def save(self, path, ctype, body, why, mods):
        dest = os.path.join(self.out, self.local(path, ctype))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(body)
        self.seen[path] = {'path': path, 'file': self.local(path, ctype), 'content_type': ctype, 'bytes': len(body),
                           'sha256': hashlib.sha256(body).hexdigest(), 'found_by': why, 'modifications': mods}
        print('  %-62s %s' % (path, ctype), flush=True)
        self.parse(path, ctype, body)

    @staticmethod
    def clean_html(ctype, body, mods):
        if 'html' not in ctype:
            return body
        clean = CF_SNIPPET.sub('', body.decode('utf-8')).encode('utf-8')
        if clean != body:
            mods.append('removed Cloudflare-injected challenge-platform <script> (only works behind Cloudflare)')
        return clean

    def run(self):
        status, ctype, nf_body = self.fetch('/__mirror_not_found_probe__')
        self.fallback = status == 200
        print('  unknown paths answer %s%s' % (status, ' (index fallback)' if self.fallback else ''))
        if status == 404 and 'html' in ctype:
            # The app's own not-found page; kept as 404.html for ErrorDocument.
            mods = ['saved the body of the site\'s 404 response as 404.html']
            self.save('/404.html', ctype, self.clean_html(ctype, nf_body, mods), 'the site\'s 404 response', mods)
        self.queue.append(('/', 'start', True))
        self.queue += [(p, 'probe', False) for p in PROBES]
        while self.queue:
            path, why, certain = self.queue.pop(0)
            if path in self.seen or path in self.misses:
                continue
            status, ctype, body = self.fetch(path)
            mods = []
            if status == 200:
                body = self.clean_html(ctype, body, mods)
            if path == '/':
                self.root_body = body
            miss = self.looks_missing(path, status, ctype, body)
            if miss:
                self.misses[path] = ('%s (%s)' % (miss, why)) if certain else 'probe/guess: ' + miss
                continue
            self.save(path, ctype, body, why, mods)

        real_misses = {k: v for k, v in self.misses.items() if not v.startswith('probe/guess')}
        manifest = {'origin': self.origin, 'user_agent': UA, 'mirrored_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'files': sorted(self.seen.values(), key=lambda r: r['path']),
                    'missing_references': real_misses,
                    'probes_not_present': sorted(k for k, v in self.misses.items() if v.startswith('probe/guess'))}
        with open(os.path.join(HERE, self.sub, 'mirror-manifest.json'), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
            f.write('\n')
        total = sum(r['bytes'] for r in self.seen.values())
        print('%s: %d files, %d bytes; missing references: %s' % (self.sub, len(self.seen), total, real_misses or 'none'))


if __name__ == '__main__':
    subs = sys.argv[1:] or ['reel-line-manager', 'dont-forget-anything', 'tenya-simulator']
    for s in subs:
        print('== ' + s)
        Mirror(s).run()
