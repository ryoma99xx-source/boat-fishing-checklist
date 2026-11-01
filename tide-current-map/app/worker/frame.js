// Store compact frames in the bundle, but send uncompressed bytes to hosting.
// The hosting proxy owns HTTP compression; an encoded body can be compressed twice.
export function frameResponse(encoded) {
 const compressed=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
 const body=new Response(compressed).body.pipeThrough(new DecompressionStream('gzip'));
 return new Response(body,{headers:{'content-type':'application/octet-stream','cache-control':'public, max-age=3600'}});
}
