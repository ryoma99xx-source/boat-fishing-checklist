#!/usr/bin/env python3
"""Serve a mirrored site the way the rental server's .htaccess does (for local checks).

    python3 -I sites/test/serve.py sites/<subdomain>/public 8101

python3 -m http.server plus the two .htaccess behaviours that matter for the apps:
an extension-less page URL (/versions/1.5.4) answers from versions/1.5.4.html, and a
missing path answers 404 with 404.html when the site has one. .htaccess itself is hidden.
"""
import functools
import io
import http.server
import os
import sys


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      '.js': 'text/javascript', '.mjs': 'text/javascript', '.webmanifest': 'application/manifest+json',
                      '.json': 'application/json', '.woff2': 'font/woff2', '.gz': 'application/octet-stream'}

    def send_head(self):
        path = self.path.split('?', 1)[0].split('#', 1)[0]
        local = self.translate_path(path)
        if os.path.basename(local) == '.htaccess':
            self.send_error(404)
            return None
        if not os.path.exists(local) and os.path.isfile(local + '.html'):
            self.path = path + '.html'
        elif not os.path.exists(local):
            nf = os.path.join(self.directory, '404.html')
            if os.path.isfile(nf):
                body = open(nf, 'rb').read()
                self.send_response(404)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                return io.BytesIO(body)
        return super().send_head()

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    root, port = os.path.abspath(sys.argv[1]), int(sys.argv[2])
    http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(Handler, directory=root)).serve_forever()
