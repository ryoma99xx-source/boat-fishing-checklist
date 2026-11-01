import test from 'node:test';
import assert from 'node:assert/strict';
import {mapConfigResponse} from '../worker/map-config.js';
const origin='https://tide-current-map.cutlassfish.tokyo';
const request=(path='/api/map-config',headers={})=>new Request(origin+path,{headers});
const configured={GOOGLE_MAPS_ENABLED:'true',GOOGLE_MAPS_BROWSER_KEY:' shared-browser-key ',UNRELATED_SECRET:'not-for-the-browser'};

test('the public map works without any operator key or visitor setup',async()=>{
 const response=mapConfigResponse();
 assert.deepEqual(await response.json(),{provider:'standard'});
 assert.equal(response.headers.get('cache-control'),'no-store');
});
test('only the configured browser key is passed to the Google adapter',async()=>{
 const response=mapConfigResponse(configured,request());
 assert.deepEqual(await response.json(),{provider:'google',apiKey:'shared-browser-key'});
 assert.deepEqual(await mapConfigResponse({GOOGLE_MAPS_BROWSER_KEY:'  '}).json(),{provider:'standard'});
});
test('a key alone does not activate Google, and the operator can turn it off',async()=>{
 for(const env of [{GOOGLE_MAPS_BROWSER_KEY:'key'},{...configured,GOOGLE_MAPS_ENABLED:'false'}]) {
  assert.deepEqual(await mapConfigResponse(env,request()).json(),{provider:'standard'});
 }
});
test('the public browser key is only served from the custom app origin',async()=>{
 for(const req of [undefined,new Request('https://another-host.invalid/api/map-config'),request('/api/map-config',{Origin:'https://outside.invalid'}),request('/api/map-config',{'Sec-Fetch-Site':'cross-site'}),request('/api/map-config',{Referer:'https://outside.invalid/page'}),new Request(origin+'/api/map-config',{method:'POST'})]) {
  assert.deepEqual(await mapConfigResponse(configured,req).json(),{provider:'standard'});
 }
 assert.equal((await mapConfigResponse(configured,request('/api/map-config',{Referer:origin+'/',Origin:origin,'Sec-Fetch-Site':'same-origin'})).json()).provider,'google');
});
