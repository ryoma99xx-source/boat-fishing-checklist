import {TIDE_POINTS,nearestTideStation,prepareTide,tideAt,tideMarkup} from '/tide.js';
import {distanceKm,facing,compass,relativeFlow,rad} from '/geometry.js';
import {extract} from '/chart.js';
import {VIEW_AREA,REGIONS,contains,fitArea} from '/coverage.js';
import {getJstSelection} from '/clock.js';
import {claimGoogleMapLoad} from '/google-guard.js';
import {installMapGestureBoundary} from '/map-gestures.js';
import {updateField,sampleCurrents,velocityAt,gridBounds,gridFor,jstSlotTime,canInflate,inflate,emptyGrid,applyTile,tileAt} from '/currents.js';
import {SPOTS,REFERENCE_POINTS,spotCentroid} from '/spots.js';
import {createFlowLayer} from '/flow-layer.js';
// START: initial map centre and default fishing position (新安浦沖).
const $=id=>document.getElementById(id),START={lat:35.279,lon:139.708};
const initialTime=getJstSelection(Date.now());
const S={mode:'model',date:initialTime.date,slot:initialTime.slot,pin:{...START},home:{...START},center:{...START},zoom:14,coastalMap:null,fieldKey:null,frames:[],compareFrame:null,loading:false,google:null,projection:null,location:null};
try{const p=JSON.parse(localStorage.getItem('shio-pin'));if(p&&contains(VIEW_AREA,p))S.pin=S.home=S.center=p;}catch{}
const H={grids:null,index:null,request:null};
let generation=0,playing=false,playTimer,debounce,toastTimer,mapImage=null,mapReady=false,overviewImage=null,overviewReady=false;
const currentCache=new Map(),tiles=new Map(),tideCache=new Map();
let tideData=null,tideKey='',tideGeneration=0;
const color=s=>s<.2?'#537b83':s<.5?'#117f91':s<1?'#007f78':s<2?'#a86922':'#a3492d';
function toast(message){$('toast').textContent=message;$('toast').style.display='block';clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').style.display='none',4500);}
function setStatus(t){$('status').textContent=t+(/失敗/.test(t)?' · タップで再取得':'');}
async function resource(url,format='json',timeout=15000){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
 try{const r=await fetch(url,{signal:controller.signal});if(!r.ok){let message='データを取得できません ('+r.status+')';try{message=(await r.json()).error||message;}catch{}const error=Error(message);error.status=r.status;throw error;}if(format==='buffer')return await r.arrayBuffer();if(!r.headers.get('content-type')?.includes('application/json'))throw Error('データの代わりに別の画面が返されました。アプリを開き直してください。');return await r.json();}
 catch(e){if(controller.signal.aborted)throw Error('通信が時間切れになりました。地図左上の状態表示をタップして再取得できます。');throw e;}
 finally{clearTimeout(timer);}
}
$('status').onclick=()=>{stop();clearTimeout(debounce);void load();};
function world(lat,lon,z=S.zoom){const n=256*2**z,s=Math.sin(rad(Math.max(-85,Math.min(85,lat))));return {x:(lon+180)/360*n,y:(.5-Math.log((1+s)/(1-s))/(4*Math.PI))*n};}
function inverse(x,y,z=S.zoom){const n=256*2**z;return {lon:x/n*360-180,lat:Math.atan(Math.sinh(Math.PI*(1-2*y/n)))*180/Math.PI};}
function project(lat,lon){if(S.projection){const p=S.projection.fromLatLngToContainerPixel(new google.maps.LatLng(lat,lon));return {x:p.x,y:p.y};}const p=world(lat,lon),c=world(S.center.lat,S.center.lon);return {x:p.x-c.x+$('map').clientWidth/2,y:p.y-c.y+$('map').clientHeight/2};}
function unproject(x,y){const c=world(S.center.lat,S.center.lon);return inverse(x+c.x-$('map').clientWidth/2,y+c.y-$('map').clientHeight/2);}
// Inverse of project() for any north-up Web Mercator view (standard tiles or Google OverlayView).
function screenToLatLon(x,y){const m=lat=>Math.log(Math.tan(Math.PI/4+rad(lat)/2)),a=project(35,139),b=project(36,140),lon=139+(x-a.x)/(b.x-a.x),my=m(35)+(y-a.y)/(b.y-a.y)*(m(36)-m(35));return {lat:(2*Math.atan(Math.exp(my))-Math.PI/2)*180/Math.PI,lon};}
// Modes: 'model' (own tidal model), 'official' (JCG chart), 'compare' (both on one map).
function usesModel(){return S.mode==='model'||S.mode==='compare';}
function hourly(){return S.mode!=='model';}
function fieldReady(){return usesModel()&&!!H.grids&&S.fieldKey===S.date+'/'+S.slot;}
function modelSample(lat,lon){if(!contains(VIEW_AREA,{lat,lon}))return {reason:'view-outside'};if(!H.grids||!fieldReady())return {reason:'loading'};return sampleCurrents(H.grids,lat,lon);}
const flow=createFlowLayer({fieldCanvas:$('flowField'),trailCanvas:$('flowTrails'),size:()=>({width:$('map').clientWidth,height:$('map').clientHeight}),unproject:screenToLatLon,sample:(lat,lon,out)=>fieldReady()&&contains(VIEW_AREA,{lat,lon})?velocityAt(H.grids,lat,lon,out):null});
globalThis.__flow=flow;
function canvas(id){const el=$(id),dpr=devicePixelRatio||1,w=$('map').clientWidth,h=$('map').clientHeight;if(el.width!==w*dpr||el.height!==h*dpr){el.width=w*dpr;el.height=h*dpr;}const c=el.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);return c;}
function tile(x,y,z){const key=z+'/'+x+'/'+y;if(tiles.has(key))return tiles.get(key);const t={ok:false,im:new Image()};t.im.onload=()=>{t.ok=true;drawBase();};t.im.src='https://cyberjapandata.gsi.go.jp/xyz/pale/'+key+'.png';tiles.set(key,t);if(tiles.size>200)tiles.delete(tiles.keys().next().value);return t;}
function drawBase(){if(S.google)return;const c=canvas('base'),w=$('map').clientWidth,h=$('map').clientHeight,center=world(S.center.lat,S.center.lon),left=center.x-w/2,top=center.y-h/2;c.fillStyle='#bed2ff';c.fillRect(0,0,w,h);
 const ov=S.overview,ovk=ov?2**(S.zoom-ov.z):0;
 if(overviewReady&&ov)c.drawImage(overviewImage,ov.x*256*ovk-left,ov.y*256*ovk-top,ov.w*ovk,ov.h*ovk);
 if(mapReady&&S.coastalMap){const m=S.coastalMap,k=2**(S.zoom-m.z);c.drawImage(mapImage,m.x*256*k-left,m.y*256*k-top,m.w*k,m.h*k);}
 const m=S.coastalMap,k=m?2**(S.zoom-m.z):0,within=m&&left>=m.x*256*k&&top>=m.y*256*k&&left+w<=(m.x*256+m.w)*k&&top+h<=(m.y*256+m.h)*k;
 const overviewCovers=overviewReady&&ov&&S.zoom<=ov.z&&left>=ov.x*256*ovk&&top>=ov.y*256*ovk&&left+w<=(ov.x*256+ov.w)*ovk&&top+h<=(ov.y*256+ov.h)*ovk;
 if((!within&&!overviewCovers)||S.zoom>14)for(let x=Math.floor(left/256);x<=Math.floor((left+w)/256);x++)for(let y=Math.floor(top/256);y<=Math.floor((top+h)/256);y++){const t=tile(x,y,S.zoom);if(t.ok)c.drawImage(t.im,x*256-left,y*256-top,256,256);}
}
function dot(c,x,y,r,fill){c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fillStyle=fill;c.fill();}
function arrow(c,x,y,bearing,speed,length=25,dashed=false){if(speed<.04){dot(c,x,y,2,'#537b83');return;}const a=rad(bearing-90),dx=Math.cos(a),dy=Math.sin(a),half=length/2;
 c.save();c.translate(x,y);c.rotate(a);c.lineCap='round';c.lineJoin='round';c.setLineDash(dashed?[3,3]:[]);c.beginPath();c.moveTo(-half,0);c.lineTo(half,0);c.lineTo(half-7,-5);c.moveTo(half,0);c.lineTo(half-7,5);c.strokeStyle='#ffffffec';c.lineWidth=5;c.stroke();c.strokeStyle=dashed?'#b17d19':color(speed);c.lineWidth=2.6;c.stroke();c.restore();}
function drawCoverage(c,w,h){
 const wide=S.zoom<=12.5;$('coverageLegend').hidden=!wide;
 if(!wide)return;
 function rectangle(bounds,stroke,dash){
  const nw=project(bounds.north,bounds.west),se=project(bounds.south,bounds.east),x=nw.x,y=nw.y,rw=se.x-x,rh=se.y-y;
  c.strokeStyle=stroke;c.lineWidth=2.4;c.setLineDash(dash);c.strokeRect(x,y,rw,rh);c.setLineDash([]);
  return {x,y,w:rw,h:rh};
 }
 c.save();
 const nw=project(VIEW_AREA.north,VIEW_AREA.west),se=project(VIEW_AREA.south,VIEW_AREA.east);
 c.beginPath();c.rect(0,0,w,h);c.rect(nw.x,nw.y,se.x-nw.x,se.y-nw.y);c.fillStyle='#eff2f580';c.fill('evenodd');
 const outer=rectangle(VIEW_AREA,'#236ab5',[]);
 if(outer.x>0&&outer.y>100&&outer.x<w-170&&outer.y<h-50)label(c,outer.x+125,outer.y+19,'表示対象：東京湾〜房総');
 $('modelCoverageKey').hidden=!usesModel();if(usesModel()&&H.grids)for(const g of H.grids){const fine=g.dxM<200,r=rectangle(gridBounds(g),g.dxM<75?'#4fd0a0':g.dxM<200?'#3fb7c9':'#00816b',[6,4]);if(fine&&r.w>110&&r.h>50&&r.x>0&&r.x<w-140&&r.y>120&&r.y<h-90)label(c,r.x+70,r.y+18,g.dxM+'m格子の範囲');}
 c.restore();
 for(const key of ['inner','katsuyama','misaki']){const r=REGIONS[key],p=project(r.lat,r.lon);if(p.x<35||p.x>w-35||p.y<115||p.y>h-70)continue;dot(c,p.x,p.y,3,'#236ab5');label(c,p.x,p.y+19,r.name);}
}
function drawOverlay(){const c=canvas('arrows'),w=$('map').clientWidth,h=$('map').clientHeight;c.save();c.beginPath();c.rect(0,0,w,Math.max(0,h-(S.google?28:0)));c.clip();drawCoverage(c,w,h);
 const official=officialFrame();if(official)drawOfficial(c,w,h,official);
 const taken=usesModel()?drawModelOverlay(c,w,h):[{x:project(S.pin.lat,S.pin.lon).x-20,y:project(S.pin.lat,S.pin.lon).y-20,w:40,h:66},anglerRect(project(S.pin.lat,S.pin.lon))];
 if(official)drawOfficialLabels(c,w,h,official,taken);
 const atCurrent=S.location&&distanceKm(S.pin,S.location)<.01;
 if(S.location&&!atCurrent){const p=project(S.location.lat,S.location.lon);if(p.x>0&&p.x<w&&p.y>0&&p.y<h){dot(c,p.x,p.y,8,'#ffffff');dot(c,p.x,p.y,5,'#279cff');}}
 const p=project(S.pin.lat,S.pin.lon);if(!usesModel()&&p.x>-50&&p.x<w+50&&p.y>-50&&p.y<h+50){dot(c,p.x,p.y,17,'#ffffffdd');c.strokeStyle='#153c43';c.lineWidth=2;c.beginPath();c.arc(p.x,p.y,17,0,Math.PI*2);c.stroke();dot(c,p.x,p.y,5,atCurrent?'#279cff':'#153c43');
  label(c,p.x,p.y+32,atCurrent?'現在地':'選択地点');angler(c,p.x,p.y-2,{ring:atCurrent?'#279cff':'#4fd0d6'});
 }
 const pixels=80,meters=156543.03392*Math.cos(rad(S.center.lat))/2**S.zoom*pixels;const nice=meters>1000?Math.round(meters/1000)+' km':Math.round(meters/50)*50+' m';$('scale').textContent=nice;$('scale').style.width=pixels+'px';c.restore();
}
function label(c,x,y,t){c.font='500 10px sans-serif';const tw=c.measureText(t).width;c.fillStyle='#fff';c.beginPath();c.roundRect(x-tw/2-8,y-12,tw+16,23,4);c.fill();c.fillStyle='#153c43';c.fillText(t,x-tw/2,y+3);}
function pillRect(c,x,y,t,side){c.font='600 11px sans-serif';const tw=c.measureText(t).width,pw=tw+16,ph=22;let px=side==='below'?x-pw/2:x+20,py=side==='below'?y+22:y-ph/2;return {x:px,y:py,w:pw,h:ph,tw};}
function overlaps(a,list){return list.some(b=>a.x<b.x+b.w+3&&a.x+a.w+3>b.x&&a.y<b.y+b.h+3&&a.y+a.h+3>b.y);}
function pill(c,r,t,{stroke='#4fd0d6aa',fill='#08111fe6',color='#fff'}={}){c.font='600 11px sans-serif';c.beginPath();c.roundRect(r.x,r.y,r.w,r.h,11);c.fillStyle=fill;c.fill();c.lineWidth=1;c.strokeStyle=stroke;c.setLineDash([]);c.stroke();c.fillStyle=color;c.fillText(t,r.x+8,r.y+15);}
// Round dark badge with a white arrow toward the flow direction (reference look).
function badge(c,x,y,bearing,{r=13,ring='#ffffffb0',dash=null}={}){
 c.save();c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fillStyle='#08111ff0';c.fill();c.lineWidth=1.6;c.strokeStyle=ring;c.setLineDash(dash||[]);c.stroke();c.setLineDash([]);
 if(bearing==null){dot(c,x,y,2.5,'#c8d6e6');c.restore();return;}
 c.translate(x,y);c.rotate(rad(bearing));c.beginPath();c.moveTo(0,r-5);c.lineTo(0,-r+5);c.moveTo(-4.5,-r+10);c.lineTo(0,-r+5);c.lineTo(4.5,-r+10);c.strokeStyle='#fff';c.lineWidth=2.2;c.lineCap='round';c.lineJoin='round';c.stroke();c.restore();
}
// Angler mark drawn just above the selected point, so "my spot" stands out from reference points.
function angler(c,x,y,{ring='#4fd0d6'}={}){
 const cy=y-33;c.save();
 c.beginPath();c.moveTo(x-5,cy+10);c.lineTo(x,cy+17);c.lineTo(x+5,cy+10);c.closePath();c.fillStyle=ring;c.fill();
 c.beginPath();c.arc(x,cy,13,0,Math.PI*2);c.fillStyle='#f4f8fb';c.fill();c.lineWidth=2;c.strokeStyle=ring;c.stroke();
 c.translate(x,cy);c.strokeStyle='#0d2233';c.fillStyle='#0d2233';c.lineCap='round';c.lineJoin='round';
 c.beginPath();c.arc(-3.2,-5.6,2.4,0,Math.PI*2);c.fill();
 c.lineWidth=2.6;c.beginPath();c.moveTo(-3.6,-2.6);c.lineTo(-4.2,3.4);c.lineTo(-1.2,7.6);c.moveTo(-4.2,3.4);c.lineTo(-6.6,7.6);c.stroke();
 c.lineWidth=1.8;c.beginPath();c.moveTo(-3.6,-1.4);c.lineTo(0.8,0.4);c.stroke();
 c.lineWidth=1.2;c.beginPath();c.moveTo(-1.6,1.6);c.quadraticCurveTo(3.5,-4,8.6,-8.2);c.stroke();
 c.lineWidth=.8;c.beginPath();c.moveTo(8.6,-8.2);c.lineTo(8.6,5.6);c.stroke();
 c.restore();
}
const anglerRect=p=>({x:p.x-14,y:p.y-47,w:28,h:30});
function modelValueText(f){return f.bearing==null?(f.reason==='pending'?'モデル取得中':'モデル値なし'):'モデル'+f.speed.toFixed(1)+'kt';}
// Generic marker list: selected point and fixed reference points (all model values).
function markerList(){
 const list=[],atCurrent=S.location&&distanceKm(S.pin,S.location)<.01,f=pointFlow();
 list.push({kind:'pin',lat:S.pin.lat,lon:S.pin.lon,bearing:f.bearing??null,text:(atCurrent?'現在地 ':'')+modelValueText(f),priority:0});
 for(const r of REFERENCE_POINTS){if(S.zoom<(r.minZoom||12))continue;const v=modelSample(r.lat,r.lon);if(v.bearing==null&&v.reason!=='pending')continue;list.push({kind:'reference',lat:r.lat,lon:r.lon,bearing:v.bearing,text:r.name+' '+modelValueText(v),priority:2});}
 return list;
}
function drawSpots(c,w,h,taken){
 if(S.zoom<12)return;
 const labels=[];
 for(const spot of SPOTS){
  const pts=spot.polygon.map(([lat,lon])=>project(lat,lon));
  if(pts.every(p=>p.x<0)||pts.every(p=>p.x>w)||pts.every(p=>p.y<0)||pts.every(p=>p.y>h))continue;
  c.beginPath();pts.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.closePath();
  c.fillStyle='#ff5a8a26';c.fill();c.setLineDash([6,4]);c.lineWidth=1.8;c.strokeStyle='#ff6f96';c.stroke();c.setLineDash([]);
  const cen=spotCentroid(spot),ct=project(cen.lat,cen.lon),bottom=Math.max(...pts.map(p=>p.y));labels.push({ct,below:{x:ct.x,y:bottom+15},text:spot.label});
 }
 for(const {ct,below,text} of labels){c.font='600 11px sans-serif';const tw=c.measureText(text).width;for(const at of [below,ct]){const r={x:at.x-tw/2-8,y:at.y-11,w:tw+16,h:22};if(r.x<4||r.x+r.w>w-58||r.y<4||r.y+r.h>h-4||overlaps(r,taken))continue;taken.push(r);pill(c,r,text,{stroke:'#ff6f96',fill:'#2a0d1be0',color:'#ffd3df'});break;}}
}
function drawModelOverlay(c,w,h){
 const markers=markerList().map(m=>({...m,p:project(m.lat,m.lon)})).filter(m=>m.p.x>-30&&m.p.x<w+30&&m.p.y>-30&&m.p.y<h+30);
 const ui=uiRects(),taken=[],placed=[],usable=w-58;
 for(const m of markers.sort((a,b)=>a.priority-b.priority)){
  if(m.kind==='reference'&&placed.some(o=>Math.hypot(o.p.x-m.p.x,o.p.y-m.p.y)<34))continue;
  const left=m.p.x+20+pillRect(c,0,0,m.text,'right').w>usable,r=pillRect(c,m.p.x,m.p.y,m.text,'right');if(left)r.x=m.p.x-20-r.w;
  if(m.kind==='reference'&&(overlaps(r,taken)||overlaps(r,ui)||r.x<2||r.x+r.w>usable))continue;
  taken.push(r,{x:m.p.x-15,y:m.p.y-15,w:30,h:30});if(m.kind==='pin')taken.push(anglerRect(m.p));placed.push({...m,r});
 }
 drawSpots(c,w,h,taken.concat(ui));
 for(const m of placed.sort((a,b)=>b.priority-a.priority)){badge(c,m.p.x,m.p.y,m.bearing,m.kind==='pin'?{r:15,ring:'#4fd0d6'}:{});pill(c,m.r,m.text,m.kind==='pin'?{stroke:'#4fd0d6'}:{stroke:'#ffffff66'});if(m.kind==='pin')angler(c,m.p.x,m.p.y,{ring:S.location&&distanceKm(S.pin,S.location)<.01?'#279cff':'#4fd0d6'});}
 return taken;
}
// Official JCG chart on the same map. Image pixel (x,y) -> lat = 35 + (631 - y)/840, lon = 139.5 + (x - 30)/675
// (linear graticule of the published chart). Drawn in horizontal strips so latitude follows Web Mercator.
// Measured: with the linear graticule the chart's coastline sits ~0.4 km south and ~0.3 km east of the
// GtTM/GSI coastline (median over 3,700 coastline pixels; consistent with the old Tokyo Datum offset).
// Shifting by this constant brings the median coastline distance from ~170 m to ~70 m.
const JCG_SHIFT={lat:.0036,lon:-.0033};
const jcgPoint=s=>({lat:s.lat+JCG_SHIFT.lat,lon:s.lon+JCG_SHIFT.lon});
function officialFrame(){return S.mode==='official'?S.frames[0]:S.mode==='compare'?S.compareFrame:null;}
function drawOfficial(c,w,h,frame){
 // Chart coastline, stretched with the chart's graticule; only where the stretch stays small enough to read.
 const src=frame.overlay;
 if(src&&S.zoom<=11){const lonOf=x=>139.5+(x-30)/675+JCG_SHIFT.lon,latOf=y=>35+(631-y)/840+JCG_SHIFT.lat,left=project(35,lonOf(0)).x,right=project(35,lonOf(src.width)).x,step=16;
  c.save();c.imageSmoothingEnabled=true;
  for(let y=0;y<src.height;y+=step){const y1=Math.min(src.height,y+step),top=project(latOf(y),139.5).y,bottom=project(latOf(y1),139.5).y;if(bottom<0||top>h)continue;c.drawImage(src,0,y,src.width,y1-y,left,top,right-left,bottom-top);}
  c.restore();}
 // Arrows: the published arrow pixels at their native size, placed at each station's georeferenced position.
 c.save();if(S.mode==='compare')c.globalAlpha=.9;
 for(const s of frame.stations){const q=jcgPoint(s),p=project(q.lat,q.lon);if(p.x<-40||p.x>w+40||p.y<-40||p.y>h+40)continue;
  if(s.sprite)c.drawImage(s.sprite,Math.round(p.x+s.minx-s.x),Math.round(p.y+s.miny-s.y));else if(s.bearing!=null)arrow(c,p.x,p.y,s.bearing,s.speed,30);else{dot(c,p.x,p.y,4.5,'#ffffff');dot(c,p.x,p.y,3,'#78849a');}}
 c.restore();
}
// Map UI boxes (switch, chips, buttons, legend) so labels are not hidden underneath them.
function uiRects(){
 const m=$('map').getBoundingClientRect(),out=[];
 for(const sel of ['.map-modes','.map-top','#mapGuide','#gestureHelp','.map-controls','#pointPeek','#coverageLegend','.map-bottom']){
  const el=$('map').querySelector?.(sel);if(!el||el.hidden)continue;const r=el.getBoundingClientRect();if(!r.width)continue;out.push({x:r.left-m.left,y:r.top-m.top,w:r.width,h:r.height});
 }
 return out;
}
// Station speed labels (kn, as published), skipped where they would overlap.
function drawOfficialLabels(c,w,h,frame,taken){
 if(S.zoom<10)return;
 const ui=uiRects();c.font='600 10px sans-serif';
 for(const s of [...frame.stations].sort((a,b)=>b.speed-a.speed)){
  const q=jcgPoint(s),p=project(q.lat,q.lon),t=s.speed.toFixed(1)+'kn',tw=c.measureText(t).width,r={x:p.x+(s.sprite?Math.max(10,s.sprite.width/2-2):8),y:p.y-8,w:tw+8,h:16};
  if(r.x<2||r.x+r.w>w-58||r.y<2||r.y+r.h>h-30||overlaps(r,taken)||overlaps(r,ui))continue;taken.push(r);
  c.beginPath();c.roundRect(r.x,r.y,r.w,r.h,8);c.fillStyle='#0a1223d9';c.fill();c.fillStyle='#ffe2b8';c.fillText(t,r.x+4,r.y+12);
 }
}
function draw(){drawBase();drawOverlay();flow.invalidate();loadDetail();}
function go(ll,z=S.zoom){S.center={...ll};S.zoom=z;if(S.google){S.google.setCenter({lat:ll.lat,lng:ll.lon});S.google.setZoom(z);}draw();}
function showCoverage(){const view=fitArea(VIEW_AREA,$('map').clientWidth,$('map').clientHeight,44);go(view.center,view.zoom);}
$('showCoverage').onclick=showCoverage;
const locationButtons=[$('locate'),$('locateMap')];
function setLocating(busy){
 for(const button of locationButtons){
  button.disabled=busy;button.setAttribute('aria-busy',String(busy));
  const label=button.querySelector('.location-caption');
  if(label)label.textContent=busy?'取得中':'現在地';else button.textContent=busy?'取得中…':'◎ 現在地';
 }
}
function locateCurrentPosition(){
 if(locationButtons.some(button=>button.disabled))return;
 if(!navigator.geolocation){toast('このブラウザでは現在地を取得できません。SafariやChromeで開いてお試しください。');return;}
 setLocating(true);
 const finish=()=>setLocating(false);
 const failed=error=>{finish();toast(error.code===1?'位置情報が許可されていません。ブラウザの位置情報を許可して、もう一度お試しください。':error.code===3?'現在地の取得が時間切れになりました。もう一度お試しください。':'現在地を取得できませんでした。電波や位置情報の設定を確認してお試しください。');};
 try{navigator.geolocation.getCurrentPosition(position=>{
  finish();const p={lat:position.coords.latitude,lon:position.coords.longitude};
  if(!Number.isFinite(p.lat)||!Number.isFinite(p.lon)||Math.abs(p.lat)>85||Math.abs(p.lon)>180){toast('現在地の座標を読み取れませんでした。もう一度お試しください。');return;}
  S.location={...p,accuracy:position.coords.accuracy};selectPoint(p);go(p,15);
  const outside=!contains(VIEW_AREA,p);
  toast(outside?'現在地へ移動しました。この場所は潮流の表示対象範囲外です。':position.coords.accuracy>200?'現在地へ移動しました。取得した位置の誤差が大きいため、地図上でも位置を確認してください。':'現在地へ移動しました。');
 },failed,{enableHighAccuracy:true,timeout:15000,maximumAge:0});}catch{failed({});}
}
for(const button of locationButtons)button.onclick=locateCurrentPosition;
$('region').onchange=e=>{const key=e.target.value;if(key==='all')showCoverage();else if(key==='home'){S.pin={...S.home};go(S.home,14);updatePoint();}else if(REGIONS[key]){const r=REGIONS[key];go(r,r.zoom);S.pin={lat:r.lat,lon:r.lon};updatePoint();drawOverlay();}e.target.value='';};
function zoom(n){if(S.google){S.google.setZoom(Math.max(8,Math.min(20,S.google.getZoom()+n)));return;}S.zoom=Math.max(8,Math.min(18,S.zoom+n));draw();}
new ResizeObserver(draw).observe($('map'));$('cape').onclick=()=>{go({lat:35.268,lon:139.727},13);toast(S.mode==='official'?'観音崎周辺の沖合推算点を表示しています。':'観音崎周辺の潮汐渦は研究で報告されています。モデルの渦や反転時刻は実測未検証です。');};$('zoomIn').onclick=()=>zoom(1);$('zoomOut').onclick=()=>zoom(-1);$('home').onclick=()=>{S.pin={...S.home};go(S.home,14);updatePoint();};$('fullMap').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await $('map').requestFullscreen();}catch{toast('このブラウザは全画面表示に対応していません。');}};
const pointers=new Map();let drag=null,pinch=null;
installMapGestureBoundary($('map'),document);
$('map').addEventListener('pointerdown',e=>{if(S.google||e.target.closest('button'))return;pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});$('map').setPointerCapture(e.pointerId);if(pointers.size===1)drag={x:e.clientX,y:e.clientY,center:world(S.center.lat,S.center.lon),moved:false};if(pointers.size===2){const p=[...pointers.values()];pinch={distance:Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y),zoom:S.zoom};if(drag)drag.moved=true;}});
$('map').addEventListener('pointermove',e=>{if(!pointers.has(e.pointerId))return;pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});if(pointers.size===2&&pinch){const p=[...pointers.values()],d=Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y);const z=Math.max(8,Math.min(18,pinch.zoom+Math.round(Math.log2(d/pinch.distance))));flow.setInteracting(true);if(z!==S.zoom){S.zoom=z;draw();}return;}if(drag&&!pinch){const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>6)drag.moved=true;if(drag.moved){flow.setInteracting(true);S.center=inverse(drag.center.x-dx,drag.center.y-dy);draw();}}});
$('map').addEventListener('pointerup',e=>{if(!pointers.has(e.pointerId))return;const click=pointers.size===1&&drag&&!drag.moved&&!pinch;pointers.delete(e.pointerId);if(click){const r=$('map').getBoundingClientRect();selectPoint(unproject(e.clientX-r.left,e.clientY-r.top));}if(pointers.size===0){drag=null;pinch=null;flow.setInteracting(false);}});
$('map').addEventListener('pointercancel',()=>{pointers.clear();drag=null;pinch=null;flow.setInteracting(false);});$('map').addEventListener('wheel',e=>{if(S.google)return;e.preventDefault();zoom(e.deltaY<0?1:-1);},{passive:false});
function selectPoint(p){S.pin=p;updatePoint();drawOverlay();loadDetail();}
function nearestOfficial(){if(!S.frames[0])return null;const best=S.frames[0].stations.reduce((a,b)=>!a||distanceKm(S.pin,jcgPoint(b))<distanceKm(S.pin,jcgPoint(a))?b:a,null);return best&&{...best,...jcgPoint(best)};}
function pointFlow(){if(!contains(VIEW_AREA,S.pin))return {reason:'view-outside'};if(usesModel())return modelSample(S.pin.lat,S.pin.lon);return nearestOfficial()||{};}
const AREA_NAME=dx=>dx<75?'横須賀沿岸':dx<150?'東京湾中部':dx<225?'内房':dx<400?'東京湾':'房総（外房・内房）';
function gridName(f){return f.cellSize+'m格子（'+AREA_NAME(f.cellSize)+'）';}
const MODEL_LIMITS='潮汐のみの水深平均モデルです。風・河川・密度流・黒潮の影響・二枚潮・干出は含みません。格子間隔は精度ではありません。実測未検証。';
const SOTOBO_NOTE='外房・九十九里・銚子沖は黒潮や沖合の海流の影響が大きく、潮汐だけのこの計算とは実際の流れが大きく違うことがあります。';
function updatePoint(){const f=pointFlow(),face=facing($('heading').value,$('seat').value),official=S.mode==='official';$('coordinates').textContent=S.pin.lat.toFixed(5)+'°N, '+S.pin.lon.toFixed(5)+'°E';$('googleLink').href='https://www.google.com/maps/search/?api=1&query='+S.pin.lat+','+S.pin.lon;$('pointName').textContent=S.location&&distanceKm(S.pin,S.location)<.01?'現在地':distanceKm(S.pin,S.home)<.08?(distanceKm(S.home,START)<.05?'新安浦沖（参考位置）':'保存した釣り位置'):'タップした地点';$('face').textContent='正面：'+compass(face)+' '+face.toFixed(1)+'°';
 updatePeek(f);updateTide();$('reference').textContent=official?'海上保安庁 推算':'自作モデル・実測未検証';$('speedUnit').textContent=official?'推算 kn':'モデル kt';$('cell').textContent=official?'毎正時の原図':f.cellSize?'計算格子 '+f.cellSize+'m'+(f.lat!=null?' · セル中心まで約'+Math.round(distanceKm(S.pin,f)*1000)+'m':''):'計算格子 50m / 250m';
 if(f.bearing==null){$('direction').textContent='表示できません';$('speed').textContent='—';$('flowArrow').style.visibility='hidden';$('shore').textContent='岸まで —';$('depth').textContent='水深 —';$('relative').textContent='この地点の流向は表示できません';
  const failed=f.reason==='loading'&&!S.loading&&usesModel();
  $('flowType').textContent=f.reason==='pending'?f.cellSize+'m格子のデータを取得中':f.reason==='failed'?f.cellSize+'m格子のデータを取得できません':f.reason==='view-outside'?'アプリの表示対象範囲外':S.loading?'データを取得中':failed?'潮流データを取得できません':f.reason==='land'?'陸地または浅場（計算対象外）':f.reason==='outside'?'潮流モデルの計算範囲外':'流向を読み取れません';
  $('pointNote').textContent=f.reason==='pending'?AREA_NAME(f.cellSize)+'の細かい格子を読み込んでいます。粗い格子の値では代用しません。':f.reason==='failed'?AREA_NAME(f.cellSize)+'の'+f.cellSize+'m格子を取得できませんでした。地図左上の状態表示をタップして再取得してください。粗い格子の値では代用しません。':f.reason==='view-outside'?'青枠がアプリの表示対象です。「対象範囲」で湾奥〜勝山沖・三崎周辺を全体表示できます。':failed?'潮流モデルのデータを取得できませんでした。地図左上の状態表示をタップして再取得してください。別の計算で代用しません。':f.reason==='land'?'この地点は陸地、または水深が浅く計算していないセルです。近くの海の値をこの地点の値として代用しません。':f.reason==='outside'?'50m・250mどちらの計算範囲にも入っていません。値は表示しません。':'数値の取得後に表示します。陸地・計算範囲外には矢印を出しません。';return;}
 $('direction').textContent=f.speed<.04?'ほぼ停止':compass(f.bearing)+'へ';$('flowArrow').style.visibility=f.speed<.04?'hidden':'visible';$('flowArrow').style.transform='rotate('+f.bearing+'deg)';$('speed').textContent=f.speed.toFixed(1);$('relative').textContent=relativeFlow(f.bearing,face,f.speed);
 if(official){$('shore').textContent='選択位置から '+distanceKm(S.pin,f).toFixed(1)+' km';$('depth').textContent='沖合の推算点';$('flowType').textContent='最寄りの公式地点の流れ';$('pointNote').textContent='表示位置の岸際を計算した値ではありません。公式推算図の最寄り地点を表示しています。';}
 else{$('shore').textContent=f.shore==null?'岸まで 2km以上':'岸まで 約'+(f.shore>=1000?(f.shore/1000).toFixed(1)+' km':Math.round(f.shore/10)*10+' m');$('depth').textContent=f.depth!=null?'モデル水深 約'+Math.round(f.depth)+' m':'水深 —';$('flowType').textContent=f.shoreType;$('pointNote').textContent=gridName(f)+'の値。'+(f.lon>140.05&&f.lat<35.3||f.lon>140.3?SOTOBO_NOTE:'')+MODEL_LIMITS+(f.shore!=null&&f.shore<150?' 岸に近く、地形の粗さの影響が特に大きい場所です。':'');}
}
function selectedTideStation(){const code=$('tideStation').value;return TIDE_POINTS[code]?code:nearestTideStation(S.pin);}
function updateTide(){const code=selectedTideStation(),key=S.date+'/'+code;if(key!==tideKey){tideKey=key;void loadTide(code,key);}else drawTide();}
async function loadTide(code=selectedTideStation(),key=S.date+'/'+code,force=false){
 const id=++tideGeneration,date=S.date;tideData=null;$('tideChart').hidden=true;$('tideRetry').hidden=true;$('tideMessage').hidden=false;$('tideMessage').textContent=TIDE_POINTS[code].name+'の潮位表を取得中…';$('tideHeight').innerHTML='— <small>cm</small>';$('tidePhase').textContent='データ取得中';$('tideStationNote').textContent='';$('tideEvents').innerHTML='';
 try{let data=!force&&tideCache.get(key);if(!data){const raw=await resource('/api/tide?date='+date+'&station='+code+'&v=2');if(raw.code!==code||raw.date!==date||!Array.isArray(raw.hours))throw Error('潮位表の地点または日付を確認できません');data=prepareTide(raw);if(!data.segments.length)throw Error('この日の潮位データがありません');tideCache.set(key,data);if(tideCache.size>45)tideCache.delete(tideCache.keys().next().value);}if(id!==tideGeneration)return;tideData=data;$('tideMessage').hidden=true;$('tideChart').hidden=false;$('tideSource').href=data.source;drawTide();}
 catch(e){if(id!==tideGeneration)return;$('tideMessage').textContent='潮位表を取得できませんでした。'+e.message;$('tideRetry').hidden=false;$('tidePhase').textContent='取得できません';}
}
function drawTide(){
 if(!tideData||tideData.date!==S.date)return;const now=new Date(Date.now()+9*3600000),sameDay=now.toISOString().slice(0,10)===S.date,realHour=now.getUTCHours()+now.getUTCMinutes()/60,selected=S.slot/2,value=tideAt(tideData,selected);
 $('tideChart').innerHTML=tideMarkup(tideData,selected,$('tideChart').clientWidth||700,230,sameDay?realHour:null);$('tideNowLegend').hidden=!sameDay;
 $('tideHeight').innerHTML=value?Math.round(value.height)+' <small>cm</small>':'— <small>cm</small>';$('tidePhase').textContent=!value?'この時刻は欠測':Math.abs(value.slope)<2?'潮位の変化が小さい':value.slope>0?'上げ潮（潮位上昇）':'下げ潮（潮位下降）';
 const near=distanceKm(S.pin,TIDE_POINTS[tideData.code]);$('tideStationNote').textContent='参考地点：'+tideData.station+' / 選択位置から約'+near.toFixed(1)+'km';
 const all=[...(tideData.events||[]),...(tideData.nextDayEvents||[])];$('tideEvents').innerHTML=['high','low'].map(type=>{const e=all.find(e=>e.type===type&&e.hour>=selected);return '<span><small>次の'+(type==='high'?'満潮':'干潮')+'</small><b>'+(e?(e.hour>=24?'翌日 ':'')+e.time+' <em>'+e.height+'cm</em>':'データなし')+'</b></span>'}).join('');
}
$('tideStation').onchange=()=>{tideKey='';updateTide();};$('tideRetry').onclick=()=>{const code=selectedTideStation(),key=S.date+'/'+code;tideKey=key;void loadTide(code,key,true);};
$('tideChart').onclick=e=>{if(!tideData)return;const r=$('tideChart').getBoundingClientRect(),h=Math.max(0,Math.min(24,(e.clientX-r.left-36)/(r.width-51)*24));stop();S.slot=Math.max(0,Math.min(lastSlot(),Math.round(h*2)));if(hourly())S.slot=Math.floor(S.slot/2)*2;void load();};
new ResizeObserver(drawTide).observe($('tideChart'));
function refreshTideClock(){drawTide();setTimeout(refreshTideClock,60000);}setTimeout(refreshTideClock,60000);
$('menuButton').onclick=()=>{const open=$('siteMenu').hidden;$('siteMenu').hidden=!open;$('menuButton').setAttribute('aria-expanded',String(open));};
document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('siteMenu').hidden=true;$('menuButton').setAttribute('aria-expanded','false');}});
$('heading').onchange=updatePoint;$('seat').onchange=updatePoint;$('savePoint').onclick=()=>{S.home={...S.pin};try{localStorage.setItem('shio-pin',JSON.stringify(S.home));}catch{}toast('このブラウザの釣り位置として保存しました。');updatePoint();};
function lastSlot(){return hourly()?46:48;}
function updateTime(){$('date').value=S.date;const hour=Math.floor(S.slot/2),half=S.slot%2;$('time').textContent=String(hour).padStart(2,'0')+':'+(half?'30':'00');$('slider').value=S.slot;$('timeDetail').textContent=S.mode==='official'?'毎正時の公式推算 / JST':S.mode==='compare'?'毎正時で比較 / JST':'30分ごと・潮汐の調和合成 / JST';document.querySelectorAll('[data-time]').forEach(b=>b.classList.toggle('active',+b.dataset.time===S.slot));drawTide();}
// Harmonic grids: index -> per-grid meta, coefficients and depth (content-hashed URLs).
// The coarsest grid (last) loads first; finer grids (50 m inner, ~7 MB) load lazily when the view reaches them.
// Tiled harmonic grids: index -> small per-grid meta -> only the 32x32-cell tiles the view needs.
async function tileBytes(e,t){if(canInflate()){try{return await inflate(await resource(e.tileBase+'.t'+t+'.gz','buffer',30000));}catch{}}return await resource(e.tileBase+'.t'+t+'.bin','buffer',30000);}
async function loadHarmonicData(){
 if(H.grids)return H.grids;if(H.request)return H.request;
 H.request=(async()=>{
  const index=await resource('/api/harmonic/index.json');if(!Array.isArray(index.grids)||!index.grids.length)throw Error('潮流モデルのデータがありません');
  // grid metadata comes inline with the index (one round trip less); the separate file stays as a fallback
  const metas=await Promise.all(index.grids.map(e=>e.metaData||resource(e.meta)));
  H.index=index;H.grids=metas.map((m,i)=>emptyGrid(m,index.grids[i]));renderValidation();syncModeUi();return H.grids;
 })();
 try{return await H.request;}finally{H.request=null;}
}
function refreshModel(){if(!usesModel())return;updatePoint();drawOverlay();flow.invalidate();}
let refreshQueued=false;
function queueRefresh(){if(refreshQueued)return;refreshQueued=true;(typeof requestAnimationFrame==='function'?requestAnimationFrame:f=>setTimeout(f,16))(()=>{refreshQueued=false;if(S.fieldKey){const ms=jstSlotTime(S.date,S.slot);for(const g of H.grids||[])updateField(g,ms);}refreshModel();});}
// Tiles needed for the visible map and the selected point: for sample points across the view, the
// first grid containing the point decides (same rule as the display), and its tile is requested.
function neededTiles(){
 const need=new Map(),w=$('map').clientWidth,h=$('map').clientHeight,N=16;
 const add=(lat,lon)=>{if(!contains(VIEW_AREA,{lat,lon}))return;const g=gridFor(H.grids,lat,lon);if(!g)return;const t=tileAt(g,lat,lon);if(t>=0&&g.tileState[t]!==2)need.set(g.entry.name+':'+t,[g,t]);};
 for(let j=0;j<=N;j++)for(let i=0;i<=N;i++){const p=screenToLatLon(i*w/N,j*h/N);add(p.lat,p.lon);}
 add(S.pin.lat,S.pin.lon);
 const a=screenToLatLon(0,0),z=screenToLatLon(w,h);
 for(const r of REFERENCE_POINTS)if(S.zoom>=(r.minZoom||12)&&r.lat<=a.lat&&r.lat>=z.lat&&r.lon>=a.lon&&r.lon<=z.lon)add(r.lat,r.lon);
 return [...need.values()];
}
let tileFailures=0;
function loadDetail(retry=false){
 if(!H.grids||!usesModel())return;if(retry)tileFailures=0;
 for(const [g,t] of neededTiles()){
  const st=g.tileState[t];if(st===1||(st===3&&!retry))continue;
  g.tileState[t]=1;
  tileBytes(g.entry,t).then(buf=>{applyTile(g,t,new Int16Array(buf));queueRefresh();if(usesModel()&&S.fieldKey&&tileFailures===0)setStatus('潮流モデル（潮汐のみ）/ 実測未検証');})
   .catch(e=>{g.tileState[t]=3;tileFailures++;refreshModel();if(usesModel()){setStatus(g.dxM+'m格子の取得失敗（タップで再取得）');toast(e.message);}});
 }
}
function gridSummary(){return H.grids?H.grids.map(g=>g.dxM+'m（'+AREA_NAME(g.dxM)+'）').join('＋'):'50m・100m・250m格子';}
async function loadModel(){
 const id=++generation;S.frames=[];const key=S.date+'/'+S.slot;
 if(!H.grids){S.loading=true;S.fieldKey=null;updateTime();updatePoint();drawOverlay();flow.setEnabled(false);setStatus('潮流モデルを取得中…');$('boundaryInfo').textContent='潮汐の調和定数を取得中';}
 try{
  const grids=await loadHarmonicData();if(id!==generation)return;
  const ms=jstSlotTime(S.date,S.slot);for(const g of grids)updateField(g,ms);
  S.fieldKey=key;S.loading=false;updateTime();setStatus('潮流モデル（潮汐のみ）/ 実測未検証');$('boundaryInfo').textContent=gridSummary()+' · 潮汐のみの調和合成';
  updatePoint();drawOverlay();flow.setEnabled(true);flow.invalidate();loadDetail(true);
 }catch(e){if(id!==generation)return;S.loading=false;S.fieldKey=null;flow.setEnabled(false);updatePoint();drawOverlay();setStatus('潮流モデルの取得失敗');$('boundaryInfo').textContent='取得できませんでした。別の計算では代用しません。';toast(e.message);}
}
async function frame(hour){const key=S.date+'/'+hour;if(currentCache.has(key))return currentCache.get(key);const data=await resource('/api/current?date='+S.date+'&hour='+hour,'json',30000);const parsed=await extract(data);currentCache.set(key,parsed);if(currentCache.size>60)currentCache.delete(currentCache.keys().next().value);return parsed;}
let compareGeneration=0;
// JCG chart for the comparison view: fetched independently, so a slow official server never blocks the model.
async function loadCompareFrame(){
 const id=++compareGeneration,hour=Math.floor(S.slot/2),key=S.date+'/'+hour;if(S.compareFrame?.key===key)return;S.compareFrame=null;drawOverlay();
 try{const fr=await frame(hour);if(id!==compareGeneration||S.mode!=='compare')return;S.compareFrame={...fr,key};drawOverlay();}
 catch(e){if(id!==compareGeneration||S.mode!=='compare')return;toast('海上保安庁の推算図を取得できませんでした。'+e.message);}
}
async function load(){syncModeUi();if(S.mode==='compare')void loadCompareFrame();if(usesModel())return loadModel();flow.setEnabled(false);const id=++generation;S.frames=[];S.loading=true;updateTime();updatePoint();drawOverlay();setStatus('沖合データを取得中…');$('boundaryInfo').textContent='沖合の公式推算を取得中';try{const frames=[await frame(Math.floor(S.slot/2))];if(id!==generation)return;S.frames=frames;S.loading=false;setStatus('海上保安庁 / 公式推算');$('boundaryInfo').textContent='毎正時の41地点。岸際の局所流ではありません。';updatePoint();drawOverlay();}catch(e){if(id!==generation)return;S.loading=false;S.frames=[];updatePoint();drawOverlay();setStatus('データ取得失敗');$('boundaryInfo').textContent='取得できませんでした。時刻を選び直すか再取得してください。';toast(e.message);}}
function stop(){playing=false;clearTimeout(playTimer);$('play').textContent='▶';$('play').setAttribute('aria-label','時間を再生');}
function loaded(){return usesModel()?fieldReady():!!S.frames.length;}
async function advance(){if(!playing)return;const step=hourly()?2:1;if(S.slot+step>lastSlot()){stop();return;}S.slot+=step;await load();if(playing&&loaded())playTimer=setTimeout(advance,usesModel()?1200:1800);else stop();}
$('play').onclick=()=>{if(playing){stop();return;}if(S.loading)return;if(S.slot>=lastSlot())S.slot=-(hourly()?2:1);playing=true;$('play').textContent='Ⅱ';$('play').setAttribute('aria-label','再生停止');advance();};
$('slider').oninput=e=>{stop();S.slot=+e.target.value;clearTimeout(debounce);if(usesModel()){void load();return;}++generation;S.frames=[];S.loading=true;updateTime();updatePoint();drawOverlay();debounce=setTimeout(load,250);};
$('date').onchange=e=>{if(!e.target.value)return;stop();S.date=e.target.value;load();};function shiftDay(n){const d=new Date(S.date+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);S.date=d.toISOString().slice(0,10);$('date').value=S.date;stop();load();}$('prevDay').onclick=()=>shiftDay(-1);$('nextDay').onclick=()=>shiftDay(1);
function showToday(){const now=getJstSelection(Date.now());stop();S.date=now.date;S.slot=now.slot;$('date').value=S.date;void load();}
$('today').onclick=showToday;
window.addEventListener?.('pageshow',e=>{if(e.persisted)showToday();});
let accessDate=initialTime.date;
document.addEventListener('visibilitychange',()=>{const now=getJstSelection(Date.now());if(document.visibilityState==='visible'&&now.date!==accessDate){accessDate=now.date;showToday();}});
for(const b of document.querySelectorAll('[data-time]'))b.onclick=()=>{stop();S.slot=+b.dataset.time;load();};
const MODE_TEXT={
 model:{method:()=>'使用中：自作モデル（潮汐の調和合成） / '+gridSummary(),desc:'選んだ日時の潮汐による流れを計算した参考値です（潮汐のみ・実測未検証）。風・河川などの流れは含みません。',kind:'粒子：流れの向き（弱い流れも見えるよう速さを誇張）',guide:'海の上をタップして、その場所の流れを確認'},
 official:{method:()=>'使用中：海上保安庁 潮流推算（沖合41地点・毎正時）',desc:'海上保安庁の潮流推算図を同じ地図に重ねて表示します。岸際の局所流や実測値ではありません。毎正時のみ（30分は前の正時に合わせます）。',kind:'公式図の矢印と流速（kn）',guide:'公式推算は沖合の41地点。タップで近い地点の値'},
 compare:{method:()=>'使用中：自作モデルと海上保安庁 推算図を重ねて比較（毎正時）',desc:'粒子と目印は自作モデル、矢印と「kn」の数字は海上保安庁の推算図です。比較は毎正時のみ。',kind:'粒子：自作モデル ／ 矢印・kn：海上保安庁',guide:'海の上をタップすると自作モデルの値を表示'}
};
const MODEL_NOTICE='自作モデル：潮汐だけで駆動した水深平均の参考計算です（横須賀沿岸50m・東京湾中部100m・東京湾250m格子）。風・河川・密度流・黒潮の影響・二枚潮・干出は含みません。湾口ではフェリーADCP観測（港湾空港技術研究所, 2023）で潮汐以外の流れが潮汐流と同程度あり、実際の流れは大きく異なることがあります。計算範囲外・陸地には値を出しません。';
function syncModeUi(){
 const mode=S.mode,last=lastSlot(),text=MODE_TEXT[mode];if(hourly())S.slot=Math.floor(S.slot/2)*2;S.slot=Math.min(S.slot,last);$('slider').max=last;$('slider').step=hourly()?2:1;$('lastTick').textContent=hourly()?'23時':'24時';
 for(const id of ['date','prevDay','nextDay'])$(id).disabled=false;
 document.body.classList.toggle('flow-on',true);document.body.classList.toggle('mode-official',mode==='official');document.body.classList.toggle('mode-compare',mode==='compare');
 for(const [id,m] of [['coastalMode','model'],['officialMode','official'],['compareMode','compare']]){$(id).classList.toggle('active',mode===m);$(id).setAttribute('aria-pressed',String(mode===m));}
 $('modelMethod').textContent=text.method();$('modeDescription').textContent=text.desc;$('arrowKind').textContent=text.kind;$('mapGuide').textContent=text.guide;
 $('hourNote').hidden=!hourly();
 $('modelNotice').textContent=mode==='official'?'海上保安庁の公式潮流推算図から読み取った沖合の流れを、図の経緯度目盛りに合わせて地図に重ねています。岸際をピンポイントに予測した値ではありません。':MODEL_NOTICE;
}
function setMode(view){stop();clearTimeout(debounce);clearTimeout(toastTimer);$('toast').style.display='none';S.mode=view==='official'?'official':view==='compare'?'compare':'model';if(S.mode!=='compare'){++compareGeneration;S.compareFrame=null;}if(S.mode!=='official')S.frames=[];if(S.mode==='official'&&S.zoom>12)go(S.center,12);void load();}
$('coastalMode').onclick=()=>setMode('coastal');$('officialMode').onclick=()=>setMode('official');$('compareMode').onclick=()=>setMode('compare');
function modal(title,html){$('modalTitle').textContent=title;$('modalBody').innerHTML=html;$('modal').showModal();}$('close').onclick=()=>$('modal').close();$('modal').onclick=e=>{if(e.target===$('modal')){const r=$('modal').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('modal').close();}};
const escapeHtml=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Validation results are added later as data/model-validation.json ({summary, items:[{label,value,note}], updated, source}).
function validationMarkup(){
 const v=H.index?.validation;if(!v)return '<p>実測との比較結果は準備中です。現在の値は実測未検証の参考計算です。</p>';
 let out='';if(v.summary)out+='<p>'+escapeHtml(v.summary)+'</p>';
 if(Array.isArray(v.items))out+='<ul>'+v.items.map(i=>'<li><b>'+escapeHtml(i.label??'')+'</b> '+escapeHtml(i.value??'')+(i.note?' <small>'+escapeHtml(i.note)+'</small>':'')+'</li>').join('')+'</ul>';
 if(!v.summary&&!Array.isArray(v.items))out+='<ul>'+Object.entries(v).filter(([,x])=>x!==null&&typeof x!=='object').map(([k,x])=>'<li><b>'+escapeHtml(k)+'</b> '+escapeHtml(x)+'</li>').join('')+'</ul>';
 if(v.updated||v.source)out+='<p class="validation-meta">'+escapeHtml([v.updated,v.source].filter(Boolean).join(' / '))+'</p>';
 return out;
}
function renderValidation(){$('validation').innerHTML=validationMarkup();}
$('about').onclick=()=>modal('計算方法・出典',`<p class="notice">自作モデルの値は実測で検証されていない参考計算です。50m・100m・250mは計算格子の間隔で、精度を示す数値ではありません。</p><h3>自作モデル（潮汐の調和合成）</h3><p>東京湾全体（250m格子）、その中に入れ子にした東京湾中部（観音崎の内側〜海堡・中ノ瀬・木更津沖、100m格子）と横須賀沿岸（新安浦・猿島・馬堀・観音崎周辺、50m格子）で、水深平均の潮汐流を計算しました。外側の境界には気象庁の天文潮位（油壺・館山・岡田・伊東）に合わせた潮汐を与え、内側の格子は外側の計算の水位で駆動しています。計算した毎時の流れを格子ごとに分潮（M2・S2・K1・O1など12分潮）へ分解しています。ブラウザでは選んだ日時（JST）の流れをこの係数から合成します。</p><p>細かい格子を優先します（50m → 100m → 250m）。細かい格子で陸・浅場の場所は、粗い格子の値で埋めません。どの範囲外にも、陸地や浅すぎて計算していない場所にも値を出しません。</p><p><b>含まないもの：</b>風、河川、密度流（成層）、黒潮の影響、二枚潮、干出・冠水。台船・狭い港内・細かい堤防も表しません。</p><p>湾口では、フェリーに搭載したADCPの観測（港湾空港技術研究所, 2023）で、潮汐以外の流れが潮汐流と同程度の大きさで見られます。実際の流れはこの計算と大きく異なることがあります。</p><h3>実測との比較</h3><div class="validation-body">${validationMarkup()}</div><h3>水深</h3><p>防災科学技術研究所のGtTM（Naotaka CHIKASADA, 2020）から東京湾・三浦半島周辺を抽出しました。2秒角、約50m間隔の数値地形です。原典年代・元測量の密度・基準面は場所により異なります。</p><p><a href="https://kiyuu.bosai.go.jp/GtTM/" target="_blank" rel="noopener">GtTM 配布元・ライセンス ↗</a> / <a href="https://doi.org/10.17598/NIED.0021" target="_blank" rel="noopener">DOI ↗</a><br>CC BY 4.0。範囲抽出、再配列、計算格子への補間を行っています。<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">ライセンス ↗</a></p><h3>地図の表示</h3><p>流れる線（粒子）は選んだ時刻の流れを固定して動かしたもので、弱い流れも見えるよう速さを誇張しています。背景の色は流速（濃紺→青→水色→緑）。赤い破線の釣り場は仮の目安です。</p><h3>海上保安庁 潮流推算の重ね表示</h3><p>公式の推算図（毎正時）を、図の経緯度目盛り（緯度 = 35 + (631 − y)/840、経度 = 139.5 + (x − 30)/675）に合わせて地図に重ねています。この目盛りのままでは公式図の海岸線が実際より南へ約0.4km・東へ約0.3kmずれるため（旧日本測地系程度の差）、その分を補正して表示しています。補正後も100m程度の差は残ります。薄い橙の線（縮小時）は公式図の海岸線です。</p><h3>公式潮流と観音崎の研究</h3><p><a href="${S.frames[0]?.source||'https://www1.kaiho.mlit.go.jp/TIDE/pred2/CurrPred/iCurrPred.htm'}" target="_blank" rel="noopener">海上保安庁 潮流推算 ↗</a><br><a href="https://www.pari.go.jp/PDF/no1276.pdf" target="_blank" rel="noopener">港湾空港技術研究所資料1276（観音崎の潮汐渦・残差流）↗</a><br><a href="https://pari.mpat.go.jp/bdhome/" target="_blank" rel="noopener">港湾空港技術研究所 東京湾フェリーADCP観測 ↗</a><br><a href="https://www.jamstec.go.jp/jcope/vwp/tss500/" target="_blank" rel="noopener">JAMSTEC JCOPE-T（風・海流込みの試験予報）を外部で見る ↗</a></p><p>航海目的には海上保安庁刊行の潮汐表をご使用ください。</p>`);
// 想定の船の向き（参考）: wind >= 3 m/s → bow into the wind; otherwise bow toward the up-current side (潮上).
// Wind comes from Open-Meteo (hourly 10 m wind, no key); without it the boat is drawn from the current alone.
const WIND={cache:new Map(),pending:new Set(),last:null};
function windKey(){return S.date+'|'+S.pin.lat.toFixed(2)+'|'+S.pin.lon.toFixed(2);}
function windAt(){const day=WIND.cache.get(windKey());if(!day||day.error)return day&&day.tries>=3?day:null;const h=Math.min(23,Math.round(S.slot/2));const sp=day.speed[h],dir=day.dir[h];return sp==null||dir==null?{error:true}:{speed:sp,dir};}
function loadWind(){const key=windKey(),had=WIND.cache.get(key);if(WIND.pending.has(key)||had&&!(had.error&&Date.now()-had.at>(had.tries<3?4000:60000)))return;WIND.pending.add(key);
 // A failed forecast is retried a few seconds later (twice), then at most once a minute.
 const fail=()=>{const tries=(had&&had.error?had.tries||1:0)+1;WIND.cache.set(key,{error:true,at:Date.now(),tries});if(tries<3)setTimeout(()=>{if(WIND.last)updatePeek(WIND.last);},4500);};
 const u='https://api.open-meteo.com/v1/forecast?latitude='+S.pin.lat.toFixed(2)+'&longitude='+S.pin.lon.toFixed(2)+'&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms&timezone=Asia%2FTokyo&start_date='+S.date+'&end_date='+S.date;
 Promise.resolve().then(()=>fetch(u)).then(r=>r.ok?r.json():Promise.reject(Error(r.status))).then(j=>{const hr=j&&j.hourly;if(hr&&hr.wind_speed_10m)WIND.cache.set(key,{speed:hr.wind_speed_10m,dir:hr.wind_direction_10m});else fail();})
  .catch(fail).finally(()=>{WIND.pending.delete(key);if(WIND.last)updatePeek(WIND.last);});}
function windText(w){return w&&!w.error?compass(w.dir)+' '+w.speed.toFixed(1)+'m/s':w?'予報なし':'取得中';}
function updateBoat(f){WIND.last=f;const box=$('boatBox');if(!box)return;loadWind();
 const valid=f&&f.bearing!=null,w=windAt(),moving=valid&&f.speed>=.04;let head=null;
 if(w&&!w.error&&w.speed>=3)head=w.dir;
 else if(moving)head=(f.bearing+180)%360;
 const flow=$('bbFlow'),rot=$('bbFlowRot'),boat=$('bbBoat');
 if(flow&&!WIND.built){let g='';for(let y=-88;y<=88;y+=22)for(let x=-77;x<=77;x+=22)g+='<use href="#bbArrow" x="'+(x+(Math.abs(y/22)%2?11:0))+'" y="'+y+'"/>';flow.innerHTML=g;WIND.built=true;}
 if(rot)rot.setAttribute('transform','rotate('+(moving?f.bearing:0)+')');if(flow){flow.style.display=moving?'':'none';flow.style.animationDuration=(moving?Math.max(.7,Math.min(8,2.2/(f.speed+.05))):3).toFixed(2)+'s';}
 if(boat){boat.setAttribute('transform','rotate('+(head==null?0:head)+')');boat.style.opacity=head==null?'.35':'1';}
 const tideTxt=valid?(moving?compass(f.bearing)+'へ '+f.speed.toFixed(1)+(usesModel()?'kt':'kn'):'ほぼ停止'):'—';
 $('boatNote').innerHTML=(head==null?(valid?'潮がほぼ止まり風も弱いため、向きは決まりません':'この地点の流れが出ていません'):'船首 <b>'+compass(head)+'</b>（'+(w&&!w.error&&w.speed>=3?'風上':'潮上')+'）')+'<br>風 '+windText(w)+'<br>潮 '+tideTxt+'<small>風3m/s以上は風上、未満は潮上に船首</small>';}
function updatePeek(f){updateBoat(f);
 const valid=f.bearing!=null,model=usesModel();
 $('peekFlow').textContent=valid?'潮流 '+(f.speed<.04?'ほぼ停止':compass(f.bearing)+'へ')+' · '+f.speed.toFixed(1)+(model?' kt':' kn'):f.reason==='pending'?f.cellSize+'m格子を取得中…':f.reason==='failed'?f.cellSize+'m格子を取得できません':f.reason==='outside'?'潮流モデルの計算範囲外':f.reason==='land'?'陸地・浅場のため値なし':f.reason==='view-outside'?'表示対象範囲外':S.loading?'データ取得中…':f.reason==='loading'?'潮流データを取得できません':'この地点は表示対象外';
 $('peekNote').textContent=S.loading?'データ取得中':!model?'最寄りの沖合推算点の値':valid?'自作モデル '+f.cellSize+'m格子':'自作モデル';
 {const w=windAt();$('peekWind').textContent=w&&!w.error?'風向 '+compass(w.dir)+' · 風速 '+w.speed.toFixed(1)+'m/s':'風向・風速 '+(w?'予報なし':'取得中');}
 $('peekArrow').textContent=valid?(f.speed<.04?'·':'↑'):'—';$('peekArrow').style.transform=valid?'rotate('+f.bearing+'deg)':'';
}
(()=>{const b=$('boatBox'),t=$('boatToggle');if(!b||!t)return;try{if(localStorage.getItem('shio-boatbox')==='min')b.classList.add('min')}catch{}t.onclick=()=>{const m=!b.classList.contains('min');b.classList.toggle('min',m);try{localStorage.setItem('shio-boatbox',m?'min':'open')}catch{}};})();
$('pointPeek').onclick=()=>$('inspector').scrollIntoView({behavior:'smooth',block:'center'});
let googlePromise=null,googleScript=null,googleKey='',googleOverlay=null,googleListeners=[],rejectGoogle=null,googleSession=0,googleConnectPromise=null;
const storeRemove=(store,key)=>{try{store.removeItem(key);}catch{}};
function useStandard(){
 ++googleSession;
 // After a Google auth failure the map may report no center/zoom: keep the last good values.
 if(S.google){const c=S.google.getCenter(),z=Math.round(S.google.getZoom());if(c&&Number.isFinite(c.lat())&&Number.isFinite(c.lng()))S.center={lat:c.lat(),lon:c.lng()};if(Number.isFinite(z))S.zoom=z;}
 if(googleOverlay){googleOverlay.setMap(null);googleOverlay=null;}
 for(const l of googleListeners)l.remove();googleListeners=[];
 S.google=null;S.projection=null;document.body.classList.remove('google');
 $('googleMap').replaceChildren();
 $('mapCredit').textContent='地理院タイル（淡色地図） / 水深 NIED GtTM · CC BY 4.0';
 $('gestureHelp').textContent='二本指で拡大縮小 · タップで地点選択';
 draw();
}
function openSettings(){
 modal('地点を座標で指定',`<p>緯度・経度を入力して、確認したい海上の地点へ移動できます。</p>
 <div class="point-grid"><label>北緯<input id="lat" type="number" step=".00001" value="${S.pin.lat.toFixed(5)}"></label><label>東経<input id="lon" type="number" step=".00001" value="${S.pin.lon.toFixed(5)}"></label></div><p id="settingsMessage" role="status"></p><button id="setCoordinates" class="primary">この地点を表示</button><button id="reset">初期位置に戻す</button>`);
 $('setCoordinates').onclick=()=>{const p={lat:+$('lat').value,lon:+$('lon').value};if(!Number.isFinite(p.lat)||!Number.isFinite(p.lon)||!contains(VIEW_AREA,p)){$('settingsMessage').textContent='青枠内（東京湾〜房総・鹿島灘南部）の緯度・経度を入力してください。';return;}selectPoint(p);go(p,15);$('modal').close();};
 $('reset').onclick=()=>{selectPoint({...START});go(START,14);$('modal').close();};
}
$('settings').onclick=openSettings;
async function loadGoogleLibrary(key){
 if(window.google?.maps?.Map)return;
 if(!googlePromise){
  googleKey=key;
  googlePromise=new Promise((resolve,reject)=>{
   let done=false;const finish=error=>{if(done)return;done=true;clearTimeout(timeout);if(error){googleScript?.remove();googlePromise=null;reject(error);}else resolve();};
   const timeout=setTimeout(()=>finish(Error('地図を読み込めませんでした。')),15000);
   window.shioReady=()=>finish();window.gm_authFailure=()=>{finish(Error('地図を利用できませんでした。'));googleAuthFailed();};
   googleScript=document.createElement('script');
   googleScript.src='https://maps.googleapis.com/maps/api/js?'+new URLSearchParams({key,callback:'shioReady',language:'ja',loading:'async',v:'weekly'});
   googleScript.onerror=()=>finish(Error('地図を読み込めませんでした。'));
   document.head.append(googleScript);
  });
 }
 await googlePromise;
}
function googleAuthFailed(){
 const message='地図を標準表示に切り替えました。';
 if(rejectGoogle){rejectGoogle(Error(message));rejectGoogle=null;}
 useStandard();toast(message);
}
async function useGoogle(key){
 await loadGoogleLibrary(key);useStandard();const session=++googleSession;
 window.gm_authFailure=googleAuthFailed;document.body.classList.add('google');
 const map=new google.maps.Map($('googleMap'),{center:{lat:S.center.lat,lng:S.center.lon},zoom:S.zoom,minZoom:8,maxZoom:20,heading:0,tilt:0,rotateControl:false,zoomControl:false,cameraControl:false,streetViewControl:false,fullscreenControl:false,mapTypeControl:false,styles:[{elementType:'geometry',stylers:[{color:'#0b1623'}]},{elementType:'labels.text.fill',stylers:[{color:'#93a4bd'}]},{elementType:'labels.text.stroke',stylers:[{color:'#06080f'}]},{featureType:'water',elementType:'geometry',stylers:[{color:'#102b3b'}]},{featureType:'road',elementType:'geometry',stylers:[{color:'#26384c'}]},{featureType:'poi',stylers:[{visibility:'off'}]}],gestureHandling:'greedy',clickableIcons:false});
 S.google=map;
 const overlay=new google.maps.OverlayView();googleOverlay=overlay;
 overlay.onAdd=()=>{};overlay.onRemove=()=>{};overlay.draw=()=>{if(session===googleSession&&S.google===map){S.projection=overlay.getProjection();drawOverlay();flow.invalidate();}};overlay.setMap(map);
 googleListeners.push(map.addListener('click',e=>{if(e.latLng)selectPoint({lat:e.latLng.lat(),lon:e.latLng.lng()});}));
 googleListeners.push(map.addListener('idle',()=>{if(S.google!==map)return;const c=map.getCenter(),z=map.getZoom();if(c)S.center={lat:c.lat(),lon:c.lng()};if(Number.isFinite(z))S.zoom=z;flow.setInteracting(false);drawOverlay();flow.invalidate();loadDetail();}));
 googleListeners.push(map.addListener('dragstart',()=>flow.setInteracting(true)),map.addListener('dragend',()=>flow.setInteracting(false)));
 await new Promise((resolve,reject)=>{let done=false;const finish=error=>{if(done)return;done=true;clearTimeout(timeout);rejectGoogle=null;error?reject(error):resolve();};rejectGoogle=e=>finish(e);const timeout=setTimeout(()=>finish(Error('地図の表示を確認できませんでした。')),15000);googleListeners.push(map.addListener('tilesloaded',()=>finish()));});
 if(session!==googleSession)throw Error('地図の切り替えを取り消しました。');
 $('mapCredit').textContent='Google Maps / 流れ SHIO（潮汐モデル） / 水深 NIED GtTM · CC BY 4.0';
 $('gestureHelp').textContent='Googleマップ · 二本指で拡大縮小 · タップで流れを見る';
}
async function connectGoogle(key){
 if(S.google)return;
 if(!googleConnectPromise)googleConnectPromise=(async()=>{
  const claim=()=>{try{return claimGoogleMapLoad(localStorage);}catch{return false;}};
  const allowed=typeof navigator!=='undefined'&&navigator.locks?.request?await navigator.locks.request('shio-google-map-load',claim):claim();
  if(!allowed)return;
  try{await useGoogle(key);}catch(e){useStandard();throw e;}
 })();
 return googleConnectPromise;
}
async function restoreGoogle(){
 for(const storage of [localStorage,sessionStorage])for(const key of ['shio-google-key','shio-google-retry','shio-map-preference'])storeRemove(storage,key);
 try{
  const config=await resource('/api/map-config','json',5000);
  if(config.provider==='google'&&typeof config.apiKey==='string'&&config.apiKey.trim())await connectGoogle(config.apiKey.trim());
 }catch{useStandard();}
}

async function init(){
 S.loading=true;syncModeUi();updateTime();updatePoint();draw();
 // The old static basemap images (0.8 MB) are no longer fetched: live tiles cover every view.
 await Promise.allSettled([load(),restoreGoogle()]);
}
init();
