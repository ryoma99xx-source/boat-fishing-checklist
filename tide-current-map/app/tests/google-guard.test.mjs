import test from 'node:test';
import assert from 'node:assert/strict';
import {claimGoogleMapLoad} from '../google-guard.js';
function storage(){const items=new Map();return {getItem:k=>items.get(k)??null,setItem:(k,v)=>items.set(k,v)};}
test('repeated reloads stop before another Google load, including across page instances',()=>{
 const store=storage(),now=Date.parse('2026-10-27T00:00:00Z');
 for(let i=0;i<3;i++)assert.equal(claimGoogleMapLoad(store,now+i*100),true);
 assert.equal(claimGoogleMapLoad(store,now+1000),false);
 assert.equal(claimGoogleMapLoad(store,now+60001),true);
});
test('spreading reloads out cannot exceed twenty per rolling hour',()=>{
 const store=storage(),now=Date.parse('2026-10-27T00:00:00Z');
 for(let i=0;i<20;i++)assert.equal(claimGoogleMapLoad(store,now+i*120000),true);
 assert.equal(claimGoogleMapLoad(store,now+40*60000),false);
 assert.equal(claimGoogleMapLoad(store,now+3600001),true);
});
test('unavailable or damaged browser storage keeps the standard map',()=>{
 assert.equal(claimGoogleMapLoad({getItem(){throw Error('blocked')}}),false);
 assert.equal(claimGoogleMapLoad({getItem:()=>null,setItem(){throw Error('full')}}),false);
 assert.equal(claimGoogleMapLoad({getItem:()=>'{broken'}),false);
 assert.equal(claimGoogleMapLoad({getItem:()=>'["invalid"]'}),false);
});
