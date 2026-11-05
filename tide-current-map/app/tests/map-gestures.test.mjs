import test from 'node:test';
import assert from 'node:assert/strict';
import {installMapGestureBoundary} from '../map-gestures.js';
function setup(){
 const doc=new EventTarget(),inside={},outside={};
 const map={contains:node=>node===inside||node===map};
 const remove=installMapGestureBoundary(map,doc);
 const touch=(identifier,target=inside)=>({identifier,target});
 const send=(type,touches=[],changedTouches=touches,target=outside)=>{
  const event=new Event(type,{cancelable:true});
  Object.assign(event,{touches,changedTouches});Object.defineProperty(event,'target',{value:target});
  event.stopPropagation=()=>{throw Error('Map SDK events must keep propagating');};
  doc.dispatchEvent(event);return event.defaultPrevented;
 };
 return {touch,send,inside,outside,remove};
}
test('map multi-touch cancels page zoom while single-finger events keep propagating',()=>{
 const h=setup(),a=h.touch(1),b=h.touch(2);
 assert.equal(h.send('touchstart',[a],[a]),false);
 assert.equal(h.send('touchstart',[a,b],[b]),true);
 assert.equal(h.send('touchmove',[a,b],[]),true);
 h.send('touchend',[],[a,b]);
 assert.equal(h.send('touchmove',[h.touch(3,h.outside),h.touch(4,h.outside)],[]),false);
 h.remove();
});
test('a second finger outside the map cannot turn an active map gesture into page zoom',()=>{
 const h=setup(),a=h.touch(1),b=h.touch(2,h.outside);
 h.send('touchstart',[a],[a]);assert.equal(h.send('touchstart',[a,b],[b]),true);
 assert.equal(h.send('gesturechange'),true);
 h.send('touchcancel',[],[a,b]);assert.equal(h.send('gesturechange'),false);
 h.remove();
});
test('Safari gesture events are blocked only on the map, with outside page zoom retained',()=>{
 const h=setup();
 for(const type of ['gesturestart','gesturechange','gestureend']){
  assert.equal(h.send(type,[],[],h.inside),true);
  assert.equal(h.send(type,[],[],h.outside),false);
 }
 h.remove();assert.equal(h.send('gesturechange',[],[],h.inside),false);
});
