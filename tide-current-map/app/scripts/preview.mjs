import http from 'node:http';
const {default:worker}=await import('../dist/server/index.js');
const server=http.createServer(async(req,res)=>{try{const response=await worker.fetch(new Request('http://localhost:4173'+req.url));res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));}catch(e){res.writeHead(500);res.end(e.message);}});
server.listen(4173,'0.0.0.0',()=>console.log('Local: http://localhost:4173'));
