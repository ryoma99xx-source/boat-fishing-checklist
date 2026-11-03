// Serves the harmonic current grids. Binary files are stored gzipped in the bundle and
// returned as their original bytes through frameResponse (hosting owns HTTP compression).
// Content-hashed URLs never change content, so they can be cached for a long time.
export function harmonicResponse(path, bundle, respond = frameResponse) {
 if (!path.startsWith('/api/harmonic/')) return null;
 if (path === '/api/harmonic/index.json') return new Response(bundle.index, {headers: {'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-cache'}});
 let file = Object.hasOwn(bundle.files, path) ? bundle.files[path] : null;
 // <tile>.bin is the inflated form of the stored <tile>.gz (for browsers without DecompressionStream)
 if (!file && path.endsWith('.bin') && Object.hasOwn(bundle.files, path.slice(0, -4) + '.gz')) file = {type: 'bin', gz: bundle.files[path.slice(0, -4) + '.gz'].gz};
 if (!file) return new Response('Not found', {status: 404});
 const cache = 'public, max-age=31536000, immutable';
 if (file.type === 'json') return new Response(file.text, {headers: {'content-type': 'application/json; charset=utf-8', 'cache-control': cache}});
 // Raw gzip bytes, sent as plain binary (no content-encoding) and inflated by the browser itself.
 if (file.type === 'gz') return new Response(Uint8Array.from(atob(file.gz), c => c.charCodeAt(0)), {headers: {'content-type': 'application/octet-stream', 'cache-control': cache}});
 const response = respond(file.gz);
 response.headers.set('cache-control', cache);
 return response;
}
