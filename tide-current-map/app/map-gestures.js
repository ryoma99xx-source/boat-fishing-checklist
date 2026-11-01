// Keep a gesture that starts on the map from magnifying the entire page.
// Never stop propagation: Google's own touch handlers must still receive it.
export function installMapGestureBoundary(map, doc = document) {
 const mapTouches = new Set();
 const options = {capture:true,passive:false};
 const prevent = event => { if (event.cancelable) event.preventDefault(); };
 const multiTouch = event => {
  if (mapTouches.size && event.touches.length > 1) prevent(event);
 };
 const start = event => {
  for (const touch of event.changedTouches) {
   if (map.contains(touch.target)) mapTouches.add(touch.identifier);
  }
  multiTouch(event);
 };
 const end = event => {
  for (const touch of event.changedTouches) mapTouches.delete(touch.identifier);
 };
 const gesture = event => {
  if (mapTouches.size || map.contains(event.target)) prevent(event);
 };
 const handlers = {touchstart:start,touchmove:multiTouch,touchend:end,touchcancel:end,gesturestart:gesture,gesturechange:gesture,gestureend:gesture};
 for (const [type, handler] of Object.entries(handlers)) doc.addEventListener(type, handler, options);
 return () => {
  for (const [type, handler] of Object.entries(handlers)) doc.removeEventListener(type, handler, options);
  mapTouches.clear();
 };
}
