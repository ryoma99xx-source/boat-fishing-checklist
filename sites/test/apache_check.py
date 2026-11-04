#!/usr/bin/env python3
"""Serve each mirror with a throwaway Apache (AllowOverride FileInfo, like お名前.com RS)
and check every mirrored path: 200, the same media type as the old host, the same bytes,
the expected Cache-Control; plus a few paths that must be 404 (never 500).

    python3 -I sites/test/apache_check.py [reel-line-manager dont-forget-anything tenya-simulator]

The Apache config is deliberately unfriendly, like many shared hosts: .gz mapped to
Content-Encoding, mod_deflate on, Indexes on. Needs apache2 (mod_php is not needed).
"""
import hashlib
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SITES = os.path.dirname(HERE)
MODS = ['mpm_prefork', 'authz_core', 'mime', 'dir', 'rewrite', 'headers', 'env', 'deflate', 'filter', 'setenvif', 'alias', 'autoindex']
EXTRA = {  # path -> (status, location) checks besides the mirrored files
    '*': [('/nope', 404), ('/nope.js', 404), ('/.htaccess', 404), ('/icons/', 404), ('/icons', 404), ('/index.html', 200)],
    'tenya-simulator': [('/versions/1.5.4/', 308), ('/versions', 404), ('/versions/', 404), ('/versions/9.9.9', 404), ('/_next/static/', 404),
                        ('/_next/static/.htaccess', 404), ('/data/', 404), ('/versions/1.5.4.html', 200)],
}


def expected_cache(sub, path):
    if path.startswith('/_next/static/'):
        return 'public, max-age=31536000, immutable'
    name = path.rsplit('/', 1)[-1]
    if path.endswith(('/', '.html')) or path.startswith('/versions/') or name in ('service-worker.js', 'manifest.json') and sub != 'tenya-simulator':
        return 'no-cache'
    if sub == 'dragon-counter' and name in ('sw.js', 'catalog-extra.json', 'manifest.webmanifest', 'robots.txt'):
        return 'no-cache'
    return 'public, max-age=86400'


def get(port, path):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=20)
    c.request('GET', path, headers={'Accept-Encoding': 'gzip', 'Host': 'localhost'})
    r = c.getresponse()
    body = r.read()
    c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, body


def run(sub, port):
    tmp = tempfile.mkdtemp(prefix='site-apache-', dir='/tmp')
    os.chmod(tmp, 0o755)
    root = os.path.join(tmp, 'public')
    shutil.copytree(os.path.join(SITES, sub, 'public'), root)
    subprocess.run(['chmod', '-R', 'a+rX', tmp], check=True)
    moddir = '/usr/lib/apache2/modules'
    conf = os.path.join(tmp, 'httpd.conf')
    with open(conf, 'w') as f:
        f.write('\n'.join([
            'ServerName localhost', 'Listen 127.0.0.1:%d' % port, 'PidFile %s/httpd.pid' % tmp, 'ErrorLog %s/error.log' % tmp,
            'LogLevel warn', 'DefaultRuntimeDir %s' % tmp, *['LoadModule %s_module %s/mod_%s.so' % (m, moddir, m) for m in MODS],
            'User www-data', 'Group www-data', 'TypesConfig /etc/mime.types', 'DirectoryIndex index.html',
            'AddEncoding x-gzip .gz', 'AddType application/x-gzip .gz', 'AddDefaultCharset UTF-8',
            'AddOutputFilterByType DEFLATE text/html text/css text/javascript application/json application/octet-stream application/x-gzip',
            '<Files ".ht*">', '  Require all denied', '</Files>',
            'DocumentRoot %s' % root, '<Directory %s>' % root, '  Options Indexes FollowSymLinks', '  AllowOverride FileInfo', '  Require all granted', '</Directory>', '']))
    ap = subprocess.Popen(['/usr/sbin/apache2', '-X', '-f', conf], env={**os.environ, 'APACHE_RUN_DIR': tmp}, stderr=subprocess.PIPE)
    for _ in range(100):
        try:
            get(port, '/')
            break
        except OSError:
            time.sleep(0.1)
    ok = bad = 0

    def check(name, cond, detail=''):
        nonlocal ok, bad
        if cond:
            ok += 1
        else:
            bad += 1
            print('  FAIL %s %s' % (name, detail))

    manifest = json.load(open(os.path.join(SITES, sub, 'mirror-manifest.json'), encoding='utf-8'))
    for rec in manifest['files']:
        path = rec['path']
        if path == '/404.html':
            continue
        st, h, body = get(port, path)
        want_type = rec['content_type'].split(';')[0].strip()
        got_type = h.get('content-type', '').split(';')[0].strip()
        check(path + ' status', st == 200, st)
        check(path + ' type', got_type == want_type, '%s (old host: %s)' % (h.get('content-type'), rec['content_type']))
        check(path + ' no Content-Encoding', 'content-encoding' not in h or not path.endswith('.gz'), h.get('content-encoding'))
        if h.get('content-encoding') == 'gzip':
            import gzip
            body = gzip.decompress(body)
        check(path + ' body', hashlib.sha256(body).hexdigest() == rec['sha256'])
        check(path + ' cache', h.get('cache-control') == expected_cache(sub, path), h.get('cache-control'))
    for path, status in EXTRA['*'] + EXTRA.get(sub, []):
        st, h, body = get(port, path)
        # .ht* files are refused by the server config before .htaccess runs (403 is fine too)
        ok_status = (403, 404) if path.endswith('.htaccess') else (status,)
        check(path + ' -> %d' % status, st in ok_status, '%s %s' % (st, h.get('location', '')))
        if status == 404 and st == 404 and sub == 'tenya-simulator':
            check(path + ' 404 page', b'<html' in body[:200].lower() and open(os.path.join(root, '404.html'), 'rb').read() == body)
        if status == 308:
            check(path + ' location', h.get('location', '').endswith(path.rstrip('/')), h.get('location'))
    ap.terminate()
    ap.wait()
    err = open(os.path.join(tmp, 'error.log')).read()
    check('no errors in the Apache log', not any(w in err for w in ('[core:alert]', 'Invalid command', 'not allowed here')), err[-500:])
    shutil.rmtree(tmp, ignore_errors=True)
    print('%s: %d checks passed, %d failed' % (sub, ok, bad))
    return bad


if __name__ == '__main__':
    subs = sys.argv[1:] or ['reel-line-manager', 'dont-forget-anything', 'tenya-simulator']
    sys.exit(1 if sum(run(s, 8301 + i) for i, s in enumerate(subs)) else 0)
