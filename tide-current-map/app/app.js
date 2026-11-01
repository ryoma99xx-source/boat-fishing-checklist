import {TIDE_POINTS,nearestTideStation,prepareTide,tideAt,tideMarkup} from '/tide.js';
import {distanceKm,facing,compass,relativeFlow,rad} from '/geometry.js';
import {cellAt,anchorWeights,flowAt,interpolateBoundary} from '/coastal.js';
import {extract} from '/chart.js';
import {prepareExperiment,experimentBounds,sampleExperiment} from '/experiment.js';
import {VIEW_AREA,REGIONS,contains,modelBounds,fitArea} from '/coverage.js';
import {getJstSelection} from '/clock.js';
import {claimGoogleMapLoad} from '/google-guard.js';
import {installMapGestureBoundary} from '/map-gestures.js';
const $=id=>document.getElementById(id),OBS={lat:35.279,lon:139.708};
const EXPERIMENT_DATE='2026-10-24';
const initialTime=getJstSelection(Date.now());
const S={mode:initialTime.date===EXPERIMENT_DATE?'experiment':'local',date:initialTime.date,slot:initialTime.slot,pin:{...OBS},home:{...OBS},center:{...OBS},zoom:14,model:null,weights:null,frames:[],boundary:null,loading:false,compare:false,google:null,projection:null,location:null};
try{const p=JSON.parse(localStorage.getItem('shio-pin'));if(p&&contains(VIEW_AREA,p))S.pin=S.home=S.center=p;}catch{}
let localModelReady=null,experimentMetaRequest=null;
let generation=0,playing=false,playTimer,debounce,toastTimer,mapImage=null,mapReady=false,overviewImage=null,overviewReady=false;
const currentCache=new Map(),tiles=new Map(),tideCache=new Map();
let tideData=null,tideKey='',tideGeneration=0;
let experimentMeta=null,experimentVector=null;const experimentCache=new Map();
const color=s=>s<.2?'#537b83':s<.5?'#117f91':s<1?'#007f78':s<2?'#a86922':'#a3492d';
function toast(message){$('toast').textContent=message;$('toast').style.display='block';clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').style.display='none',4500);}
function setStatus(t){$('status').textContent=t+(/失敗/.test(t)?' · タップで再取得':'');}
async function resource(url,format='json',timeout=15000){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
 try{const r=await fetch(url,{signal:controller.signal});if(!r.ok){let message='データを取得できません ('+r.status+')';try{message=(await r.json()).error||message;}catch{}const error=Error(message);error.status=r.status;throw error;}if(format==='buffer')return await r.arrayBuffer();if(!r.headers.get('content-type')?.includes('application/json'))throw Error('データの代わりに別の画面が返されました。アプリを開き直してください。');return await r.json();}
 catch(e){if(controller.signal.aborted)throw Error('通信が時間切れになりました。地図左上の状態表示をタップして再取得できます。');throw e;}
 finally{clearTimeout(timer);}
}
$('status').onclick=()=>{stop();clearTimeout(debounce);if(S.model||S.mode==='experiment')void load();else void init();};
function world(lat,lon,z=S.zoom){const n=256*2**z,s=Math.sin(rad(Math.max(-85,Math.min(85,lat))));return {x:(lon+180)/360*n,y:(.5-Math.log((1+s)/(1-s))/(4*Math.PI))*n};}
function inverse(x,y,z=S.zoom){const n=256*2**z;return {lon:x/n*360-180,lat:Math.atan(Math.sinh(Math.PI*(1-2*y/n)))*180/Math.PI};}
function project(lat,lon){if(S.projection){const p=S.projection.fromLatLngToContainerPixel(new google.maps.LatLng(lat,lon));return {x:p.x,y:p.y};}const p=world(lat,lon),c=world(S.center.lat,S.center.lon);return {x:p.x-c.x+$('map').clientWidth/2,y:p.y-c.y+$('map').clientHeight/2};}
function unproject(x,y){const c=world(S.center.lat,S.center.lon);return inverse(x+c.x-$('map').clientWidth/2,y+c.y-$('map').clientHeight/2);}
function canvas(id){const el=$(id),dpr=devicePixelRatio||1,w=$('map').clientWidth,h=$('map').clientHeight;if(el.width!==w*dpr||el.height!==h*dpr){el.width=w*dpr;el.height=h*dpr;}const c=el.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);return c;}
function tile(x,y,z){const key=z+'/'+x+'/'+y;if(tiles.has(key))return tiles.get(key);const t={ok:false,im:new Image()};t.im.onload=()=>{t.ok=true;drawBase();};t.im.src='https://cyberjapandata.gsi.go.jp/xyz/std/'+key+'.png';tiles.set(key,t);if(tiles.size>200)tiles.delete(tiles.keys().next().value);return t;}
function drawBase(){if(S.google)return;const c=canvas('base'),w=$('map').clientWidth,h=$('map').clientHeight,center=world(S.center.lat,S.center.lon),left=center.x-w/2,top=center.y-h/2;c.fillStyle='#bed2ff';c.fillRect(0,0,w,h);
 const ov=S.overview,ovk=ov?2**(S.zoom-ov.z):0;
 if(overviewReady&&ov)c.drawImage(overviewImage,ov.x*256*ovk-left,ov.y*256*ovk-top,ov.w*ovk,ov.h*ovk);
 if(mapReady&&S.model){const m=S.model.map,k=2**(S.zoom-m.z);c.drawImage(mapImage,m.x*256*k-left,m.y*256*k-top,m.w*k,m.h*k);}
 const m=S.model?.map,k=m?2**(S.zoom-m.z):0,within=m&&left>=m.x*256*k&&top>=m.y*256*k&&left+w<=(m.x*256+m.w)*k&&top+h<=(m.y*256+m.h)*k;
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
 if(outer.x>0&&outer.y>100&&outer.x<w-170&&outer.y<h-50)label(c,outer.x+125,outer.y+19,'表示対象：湾奥〜勝山沖・三崎');
 $('modelCoverageKey').hidden=S.mode==='official';const activeBounds=S.mode==='official'?null:S.mode==='experiment'&&experimentMeta?experimentBounds(experimentMeta):S.model?modelBounds(S.model):null;if(activeBounds){const inner=rectangle(activeBounds,'#00816b',[6,4]);if(inner.w>135&&inner.h>65&&inner.x>0&&inner.x<w-160&&inner.y>120&&inner.y<h-90)label(c,inner.x+95,inner.y+18,S.mode==='experiment'?'緑破線：潮汐試験の範囲':'緑破線：沿岸参考計算');}
 c.restore();
 for(const key of ['inner','katsuyama','misaki']){const r=REGIONS[key],p=project(r.lat,r.lon);if(p.x<35||p.x>w-35||p.y<115||p.y>h-70)continue;dot(c,p.x,p.y,3,'#236ab5');label(c,p.x,p.y+19,r.name);}
}
function drawOverlay(){const c=canvas('arrows'),w=$('map').clientWidth,h=$('map').clientHeight;c.save();c.beginPath();c.rect(0,0,w,Math.max(0,h-(S.google?28:0)));c.clip();drawCoverage(c,w,h);
 if(S.mode==='local'&&S.model&&S.weights){const g=S.model,p0=project(g.lat0,g.lon0),p1=project(g.lat0,g.lon0+g.dlon),px=Math.abs(p1.x-p0.x),step=Math.max(1,Math.ceil(49/px));
  for(let y=1;y<g.n-1;y+=step)for(let x=1;x<g.n-1;x+=step){const cell=g.cells[y*g.n+x];if(!cell||cell[5]<120)continue;const lat=g.lat0+y*g.dlat,lon=g.lon0+x*g.dlon,p=project(lat,lon);if(p.x<10||p.x>w-10||p.y<10||p.y>h-10)continue;const f=flowAt(g,lat,lon,S.weights);arrow(c,p.x,p.y,f.bearing,f.speed,23+Math.min(f.speed,2)*3);}
 }else if(S.mode==='experiment'&&experimentMeta&&experimentVector){const g=experimentMeta,p0=project(g.lat0,g.lon0),p1=project(g.lat0,g.lon0+g.dlon),step=Math.max(1,Math.ceil(49/Math.max(.01,Math.abs(p1.x-p0.x))));
  for(let y=1;y<g.ny-1;y+=step)for(let x=1;x<g.nx-1;x+=step){const i=g.index[y*g.nx+x];if(i<0)continue;const lat=g.lat0+y*g.dlat,lon=g.lon0+x*g.dlon;if(!contains(VIEW_AREA,{lat,lon}))continue;const p=project(lat,lon);if(p.x<10||p.x>w-10||p.y<10||p.y>h-10)continue;const f=sampleExperiment(g,experimentVector,lat,lon);arrow(c,p.x,p.y,f.bearing,f.speed,23+Math.min(f.speed,2)*3);}
 }else if(S.mode==='official'&&S.frames[0])for(const s of S.frames[0].stations){const p=project(s.lat,s.lon);if(p.x<0||p.x>w||p.y<0||p.y>h)continue;if(s.bearing!=null)arrow(c,p.x,p.y,s.bearing,s.speed,30);else dot(c,p.x,p.y,4,'#637b80');}
 if(S.mode==='local'){const cape=project(35.256,139.745);if(cape.x>20&&cape.x<w-20&&cape.y>60&&cape.y<h-60){dot(c,cape.x,cape.y,5,'#a87926');label(c,cape.x,cape.y+25,'観音崎：渦・反流は未計算');}}
 const atCurrent=S.location&&distanceKm(S.pin,S.location)<.01;
 if(S.location&&!atCurrent){const p=project(S.location.lat,S.location.lon);if(p.x>0&&p.x<w&&p.y>0&&p.y<h){dot(c,p.x,p.y,8,'#ffffff');dot(c,p.x,p.y,5,'#279cff');}}
 const p=project(S.pin.lat,S.pin.lon);if(p.x>-50&&p.x<w+50&&p.y>-50&&p.y<h+50){dot(c,p.x,p.y,17,'#ffffffdd');c.strokeStyle='#153c43';c.lineWidth=2;c.beginPath();c.arc(p.x,p.y,17,0,Math.PI*2);c.stroke();dot(c,p.x,p.y,5,atCurrent?'#279cff':'#153c43');
  if(S.compare&&S.date==='2026-10-24'){arrow(c,p.x+35,p.y-25,112.5,1,46,true);label(c,p.x,p.y+32,'朝の観察：右奥 → 左手前');}
  else label(c,p.x,p.y+32,atCurrent?'現在地':'選択地点');
 }
 const pixels=80,meters=156543.03392*Math.cos(rad(S.center.lat))/2**S.zoom*pixels;const nice=meters>1000?Math.round(meters/1000)+' km':Math.round(meters/50)*50+' m';$('scale').textContent=nice;$('scale').style.width=pixels+'px';c.restore();
}
function label(c,x,y,t){c.font='500 10px sans-serif';const tw=c.measureText(t).width;c.fillStyle='#fff';c.beginPath();c.roundRect(x-tw/2-8,y-12,tw+16,23,4);c.fill();c.fillStyle='#153c43';c.fillText(t,x-tw/2,y+3);}
function draw(){drawBase();drawOverlay();}
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
$('region').onchange=e=>{const key=e.target.value;if(key==='all')showCoverage();else if(key==='home'){S.pin={...S.home};go(S.home,14);updatePoint();}else if(REGIONS[key]){const r=REGIONS[key];go(r,r.zoom);S.pin={lat:r.lat,lon:r.lon};updatePoint();drawOverlay();if(S.mode==='local'&&pointFlow().reason==='outside')toast('この日付の広域計算は未対応です。10/24の事例なら湾全体を確認できます。');}e.target.value='';};
function zoom(n){if(S.google){S.google.setZoom(Math.max(8,Math.min(20,S.google.getZoom()+n)));return;}S.zoom=Math.max(8,Math.min(18,S.zoom+n));draw();}
new ResizeObserver(draw).observe($('map'));$('cape').onclick=()=>{if(S.mode==='official')setMode('coastal');go({lat:35.268,lon:139.727},13);toast(S.mode==='experiment'?'観音崎を含む試験計算です。岬周辺の流れや反転時刻は実測未検証です。':'観音崎の渦・反流は研究で報告されています。この定常参考モデルは渦を再現しません。');};$('zoomIn').onclick=()=>zoom(1);$('zoomOut').onclick=()=>zoom(-1);$('home').onclick=()=>{S.pin={...S.home};go(S.home,14);updatePoint();};$('fullMap').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await $('map').requestFullscreen();}catch{toast('このブラウザは全画面表示に対応していません。');}};
const pointers=new Map();let drag=null,pinch=null;
installMapGestureBoundary($('map'),document);
$('map').addEventListener('pointerdown',e=>{if(S.google||e.target.closest('button'))return;pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});$('map').setPointerCapture(e.pointerId);if(pointers.size===1)drag={x:e.clientX,y:e.clientY,center:world(S.center.lat,S.center.lon),moved:false};if(pointers.size===2){const p=[...pointers.values()];pinch={distance:Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y),zoom:S.zoom};if(drag)drag.moved=true;}});
$('map').addEventListener('pointermove',e=>{if(!pointers.has(e.pointerId))return;pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});if(pointers.size===2&&pinch){const p=[...pointers.values()],d=Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y);const z=Math.max(8,Math.min(18,pinch.zoom+Math.round(Math.log2(d/pinch.distance))));if(z!==S.zoom){S.zoom=z;draw();}return;}if(drag&&!pinch){const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>6)drag.moved=true;if(drag.moved){S.center=inverse(drag.center.x-dx,drag.center.y-dy);draw();}}});
$('map').addEventListener('pointerup',e=>{if(!pointers.has(e.pointerId))return;const click=pointers.size===1&&drag&&!drag.moved&&!pinch;pointers.delete(e.pointerId);if(click){const r=$('map').getBoundingClientRect();selectPoint(unproject(e.clientX-r.left,e.clientY-r.top));}if(pointers.size===0){drag=null;pinch=null;}});
$('map').addEventListener('pointercancel',()=>{pointers.clear();drag=null;pinch=null;});$('map').addEventListener('wheel',e=>{if(S.google)return;e.preventDefault();zoom(e.deltaY<0?1:-1);},{passive:false});
function selectPoint(p){S.pin=p;updatePoint();drawOverlay();}
function nearestOfficial(){if(!S.frames[0])return null;return S.frames[0].stations.reduce((a,b)=>!a||distanceKm(S.pin,b)<distanceKm(S.pin,a)?b:a,null);}
function pointFlow(){if(!contains(VIEW_AREA,S.pin))return {reason:'view-outside'};if(S.mode==='experiment')return experimentMeta?sampleExperiment(experimentMeta,experimentVector,S.pin.lat,S.pin.lon):{reason:'loading'};if(S.mode==='local')return S.model?flowAt(S.model,S.pin.lat,S.pin.lon,S.weights):{};return nearestOfficial()||{};}
function updatePoint(){const f=pointFlow(),face=facing($('heading').value,$('seat').value);$('coordinates').textContent=S.pin.lat.toFixed(5)+'°N, '+S.pin.lon.toFixed(5)+'°E';$('googleLink').href='https://www.google.com/maps/search/?api=1&query='+S.pin.lat+','+S.pin.lon;$('pointName').textContent=S.location&&distanceKm(S.pin,S.location)<.01?'現在地':distanceKm(S.pin,S.home)<.08?(distanceKm(S.home,OBS)<.05?'新安浦沖（参考位置）':'保存した釣り位置'):'タップした地点';$('face').textContent='正面：'+compass(face)+' '+face.toFixed(1)+'°';
 updatePeek(f);updateTide();const official=S.mode==='official';$('reference').textContent=official?'沖合の公式推算':S.mode==='experiment'?'潮汐試験・未検証':'未検証の参考値';$('speedUnit').textContent=official?'推算 kn':S.mode==='experiment'?'試験 kn':'参考 kn';$('cell').textContent=official?'毎正時の原図':f.lat!=null?(f.cellSize||100)+'mセル中心まで 約'+Math.round(distanceKm(S.pin,f)*1000)+'m':'計算セル '+(S.mode==='experiment'?250:100)+'m';
 if(f.bearing==null||(S.mode==='local'&&!S.weights)){$('direction').textContent='表示できません';$('speed').textContent='—';$('flowArrow').style.visibility='hidden';$('shore').textContent='岸まで —';$('depth').textContent='水深 —';$('relative').textContent='この地点の流向は表示できません';let reason=f.reason==='view-outside'?'アプリの表示対象範囲外':S.loading?'データを取得中':!S.weights&&S.mode==='local'?'沖合データを取得できません':f.reason==='land'?'陸地または水際の計算対象外':f.reason==='depth'?(S.mode==='experiment'?'浅場または計算対象外の水域':'この岸際は水深データが不足'):f.reason==='outside'?'表示エリア内・沿岸計算は未対応':f.reason==='loading'?'潮流データを取得できません':'流向を読み取れません';$('flowType').textContent=reason;$('pointNote').textContent=f.reason==='view-outside'?'青枠がアプリの表示対象です。「対象範囲」で湾奥〜勝山沖・三崎周辺を全体表示できます。':f.reason==='outside'?'この日付の広域計算は未対応です。日付を2026年10月24日にすると、湾全体の時間変化計算を確認できます。「沖合の公式推算」では近い公式地点を比較できます。':f.reason==='depth'?(S.mode==='experiment'?'この試験計算は水深3m以上の固定した海域が対象です。浅瀬の干出・冠水は計算しません。':'公開水深データではこの岸際を解像できません。隣の沖合の値を、この地点の値として代用しません。'):f.reason==='loading'?'この海域は計算対象内です。データの取得に失敗しました。地図左上の状態表示をタップして再取得してください。':'数値の取得後に表示します。陸地・水深が不足した場所には矢印を出しません。';return;}
 $('direction').textContent=f.speed<.04?'ほぼ停止':compass(f.bearing)+'へ';$('flowArrow').style.visibility=f.speed<.04?'hidden':'visible';$('flowArrow').style.transform='rotate('+f.bearing+'deg)';$('speed').textContent=f.speed.toFixed(1);$('relative').textContent=relativeFlow(f.bearing,face,f.speed);
 if(official){$('shore').textContent='選択位置から '+distanceKm(S.pin,f).toFixed(1)+' km';$('depth').textContent='沖合の推算点';$('flowType').textContent='最寄りの公式地点の流れ';$('pointNote').textContent='表示位置の岸際を計算した値ではありません。公式推算図の最寄り地点を表示しています。';}
 else{$('shore').textContent='岸まで 約'+(f.shore>=1000?(f.shore/1000).toFixed(1)+' km':Math.round(f.shore)+' m');$('depth').textContent='元水深 約'+Math.round(f.depth)+' m';$('flowType').textContent=f.shoreType;$('pointNote').textContent=S.mode==='experiment'?'10月24日の潮位で駆動した250m格子の試験計算です。新しい地形は約50m間隔ですが、流速・渦は実測未検証。台船周り、狭い港内、二枚潮は対象外です。':(f.shore<300?'水際に近く、水深と岸線の粗さの影響が特に大きい場所です。':'')+'計算格子100mは精度100mを意味しません。元水深は約50m間隔。原典の精度は場所により異なります。台船・細かい堤防・渦・二枚潮は対象外です。';if(distanceKm(S.pin,OBS)<.05)$('pointNote').textContent+=' 当日の実測は60〜65mです。この概算位置の計算水深と差があり、位置と地形の不確かさが残ります。';}
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
$('tideChart').onclick=e=>{if(!tideData)return;const r=$('tideChart').getBoundingClientRect(),h=Math.max(0,Math.min(24,(e.clientX-r.left-36)/(r.width-51)*24));stop();S.slot=Math.max(0,Math.min(S.mode==='experiment'?48:46,Math.round(h*2)));if(S.mode==='official')S.slot=Math.floor(S.slot/2)*2;void load();};
new ResizeObserver(drawTide).observe($('tideChart'));
function refreshTideClock(){drawTide();setTimeout(refreshTideClock,60000);}setTimeout(refreshTideClock,60000);
$('menuButton').onclick=()=>{const open=$('siteMenu').hidden;$('siteMenu').hidden=!open;$('menuButton').setAttribute('aria-expanded',String(open));};
document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('siteMenu').hidden=true;$('menuButton').setAttribute('aria-expanded','false');}});
$('heading').onchange=updatePoint;$('seat').onchange=updatePoint;$('savePoint').onclick=()=>{S.home={...S.pin};try{localStorage.setItem('shio-pin',JSON.stringify(S.home));}catch{}toast('このブラウザの釣り位置として保存しました。');updatePoint();};
function updateTime(){$('date').value=S.date;const hour=Math.floor(S.slot/2),half=S.slot%2;$('time').textContent=String(hour).padStart(2,'0')+':'+(half?'30':'00');$('slider').value=S.slot;$('timeDetail').textContent=S.mode==='experiment'?'30分ごとの潮汐試験 / JST':S.mode==='local'&&half?'沖合流を30分補間 / JST':'毎正時の公式推算 / JST';document.querySelectorAll('[data-time]').forEach(b=>b.classList.toggle('active',+b.dataset.time===S.slot));drawTide();}
async function loadExperimentMeta(){
 if(experimentMeta)return true;if(experimentMetaRequest)return experimentMetaRequest;
 experimentMetaRequest=(async()=>{try{const meta=await resource('/api/experiment/meta');if(meta.date!==EXPERIMENT_DATE)throw Error('事例計算の日付が一致しません');experimentMeta=prepareExperiment(meta);return true;}catch{return false;}})();
 try{return await experimentMetaRequest;}finally{experimentMetaRequest=null;}
}
async function loadExperiment(){
 const id=++generation,slot=S.slot;S.frames=[];experimentVector=null;S.loading=true;updateTime();updatePoint();drawOverlay();setStatus('潮汐試験を取得中…');$('boundaryInfo').textContent='油壺・布良の天文潮位で駆動した事例計算';
 try{if(!await loadExperimentMeta())throw Error('10月24日の事例データを取得できません。別の計算へ自動的に置き換えません。');if(id!==generation)return;let vector=experimentCache.get(slot);if(!vector){const bytes=await resource('/api/experiment/frame?index='+slot+'&format=raw2','buffer');if(bytes.byteLength!==experimentMeta.wetIds.length*4)throw Error('潮汐試験データの長さが不正です');vector=new Int16Array(bytes);experimentCache.set(slot,vector);}if(id!==generation)return;experimentVector=vector;S.loading=false;setStatus('10/24 潮汐試験 / 実測未検証');$('boundaryInfo').textContent='250m格子 · 油壺・布良の潮位 · 48時間の助走計算';updatePoint();drawOverlay();}
 catch(e){if(id!==generation)return;S.loading=false;experimentVector=null;updatePoint();drawOverlay();setStatus('潮汐試験の取得失敗');$('boundaryInfo').textContent='試験データを取得できません。再度時刻を選んでください。';toast(e.message);}
}
async function frame(hour){const key=S.date+'/'+hour;if(currentCache.has(key))return currentCache.get(key);const data=await resource('/api/current?date='+S.date+'&hour='+hour,'json',30000);const parsed=await extract(data);currentCache.set(key,parsed);if(currentCache.size>60)currentCache.delete(currentCache.keys().next().value);return parsed;}
function applyBoundary(){S.weights=null;S.boundary=null;if(!S.model||!S.frames[0])return;const anchor=d=>d.stations.find(s=>s.x===S.model.anchor.x&&s.y===S.model.anchor.y);const a=anchor(S.frames[0]),b=S.frames[1]?anchor(S.frames[1]):null;S.boundary=interpolateBoundary(a,b,S.slot%2?.5:0);if(S.boundary)S.weights=anchorWeights(S.model,S.boundary.u,S.boundary.v);}
async function load(){if(S.mode!=='official')S.mode=S.date===EXPERIMENT_DATE?'experiment':'local';syncModeUi();if(S.mode==='experiment')return loadExperiment();const id=++generation;S.frames=[];S.weights=null;S.boundary=null;S.loading=true;updateTime();updatePoint();drawOverlay();setStatus('沖合データを取得中…');$('boundaryInfo').textContent='沖合の公式推算を取得中';try{const h=Math.floor(S.slot/2),parent=S.mode==='local'&&!S.model?localModelReady:Promise.resolve(),[,frames]=await Promise.all([parent,Promise.all([frame(h),...(S.slot%2&&S.mode==='local'?[frame(h+1)]:[])])]);if(S.mode==='local'&&!S.model)throw Error('沿岸地形データを取得できません');if(id!==generation)return;S.frames=frames;applyBoundary();S.loading=false;setStatus(S.mode==='local'?'沿岸参考モデル / 実測未検証':'海上保安庁 / 公式推算');$('boundaryInfo').textContent=S.mode==='local'?'基準：観察位置の約2.6km東の公式点'+(S.slot%2?'（前後1時間を補間）':''):'毎正時の41地点。岸際の局所流ではありません。';updatePoint();drawOverlay();}catch(e){if(id!==generation)return;S.loading=false;S.frames=[];S.weights=null;updatePoint();drawOverlay();setStatus('データ取得失敗');$('boundaryInfo').textContent='取得できませんでした。時刻を選び直すか再取得してください。';toast(e.message);}}
function stop(){playing=false;clearTimeout(playTimer);$('play').textContent='▶';$('play').setAttribute('aria-label','時間を再生');}
async function advance(){if(!playing)return;if(S.slot>=(S.mode==='experiment'?48:46)){stop();return;}S.slot++;await load();if(playing&&(S.mode==='experiment'?!!experimentVector:!!S.frames.length))playTimer=setTimeout(advance,1800);else stop();}
$('play').onclick=()=>{if(playing){stop();return;}if(S.loading)return;if(S.slot>=(S.mode==='experiment'?48:46))S.slot=-1;playing=true;$('play').textContent='Ⅱ';$('play').setAttribute('aria-label','再生停止');advance();};
$('slider').oninput=e=>{stop();S.slot=+e.target.value;++generation;S.frames=[];S.weights=null;experimentVector=null;S.loading=true;updateTime();updatePoint();drawOverlay();clearTimeout(debounce);debounce=setTimeout(load,250);};
$('date').onchange=e=>{if(!e.target.value)return;stop();S.date=e.target.value;load();};function shiftDay(n){const d=new Date(S.date+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);S.date=d.toISOString().slice(0,10);$('date').value=S.date;stop();load();}$('prevDay').onclick=()=>shiftDay(-1);$('nextDay').onclick=()=>shiftDay(1);
function showToday(){const now=getJstSelection(Date.now());stop();S.date=now.date;S.slot=S.mode==='official'?Math.floor(now.slot/2)*2:now.slot;$('date').value=S.date;if(S.mode==='official')void load();else setMode('coastal');}
$('today').onclick=showToday;
window.addEventListener?.('pageshow',e=>{if(e.persisted)showToday();});
let accessDate=initialTime.date;
document.addEventListener('visibilitychange',()=>{const now=getJstSelection(Date.now());if(document.visibilityState==='visible'&&now.date!==accessDate){accessDate=now.date;showToday();}});
for(const b of document.querySelectorAll('[data-time]'))b.onclick=()=>{stop();S.slot=+b.dataset.time;load();};
function syncModeUi(){
 const mode=S.mode,last=mode==='experiment'?48:46;S.slot=Math.min(S.slot,last);$('slider').max=last;$('lastTick').textContent=mode==='experiment'?'24時':'23時';
 for(const id of ['date','prevDay','nextDay'])$(id).disabled=false;
 $('coastalMode').classList.toggle('active',mode!=='official');$('officialMode').classList.toggle('active',mode==='official');$('caseDate').hidden=mode!=='local';
 $('modelMethod').textContent=mode==='experiment'?'使用中：時間変化計算 / 2026年10月24日 / 250m格子':mode==='local'?'使用中：地形参考計算 / 新安浦周辺 / 100m格子':'使用中：海上保安庁の沖合41地点';
 $('modeDescription').textContent=mode==='local'?'この日付は新安浦周辺の地形参考を表示します。広域の時間変化計算は10/24の事例で確認できます。':mode==='experiment'?'選択した日付の湾全体の時間変化計算です。実測流速で未検証の事例計算です。':'選択位置に近い沖合の推算点を表示します。岸際の局所流や実測値ではありません。';
 $('arrowKind').textContent=mode==='local'?'実線：100m地形参考':mode==='experiment'?'実線：250m時間変化計算':'公式図の流向・流速';
 $('mapGuide').textContent=mode==='official'?'公式推算は沖合の41地点。タップで近い地点を比較':'海の上をタップして、その場所の流れを確認';
 $('modelNotice').textContent=mode==='experiment'?'潮流モデル：2026年10月24日の時間変化を250m格子で計算した事例です。100mの参考計算と数値を混ぜていません。流速・反流・渦は実測未検証。風・河川・二枚潮、台船や狭い港内は対象外です。':mode==='local'?'潮流モデル：この日付は新安浦・猿島・馬堀周辺の100m格子の定常参考計算です。広域の時間変化計算はまだ対応していません。計算格子は予報精度を意味せず、渦の発生・残留は計算しません。':'海上保安庁の公式潮流推算図から読み取った沖合の流れです。岸際をピンポイントに予測した値ではありません。';
}
function setMode(view){stop();clearTimeout(debounce);clearTimeout(toastTimer);$('toast').style.display='none';S.mode=view==='official'?'official':S.date===EXPERIMENT_DATE?'experiment':'local';if(S.mode==='official'){S.slot=Math.floor(S.slot/2)*2;showCoverage();}void load();}
$('coastalMode').onclick=()=>setMode('coastal');$('caseDate').onclick=()=>{S.date=EXPERIMENT_DATE;$('date').value=S.date;setMode('coastal');};$('officialMode').onclick=()=>setMode('official');$('observe').onclick=()=>{S.compare=!S.compare;$('observation').hidden=!S.compare;drawOverlay();};
function modal(title,html){$('modalTitle').textContent=title;$('modalBody').innerHTML=html;$('modal').showModal();}$('close').onclick=()=>$('modal').close();$('modal').onclick=e=>{if(e.target===$('modal')){const r=$('modal').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('modal').close();}};
$('about').onclick=()=>modal('水深データと計算の範囲',`<p class="notice">表示値は実測で検証されていません。100m・250mの格子は、その大きさでの予報精度を保証しません。</p><h3>新しく取得した水深</h3><p>防災科学技術研究所のGtTM（Naotaka CHIKASADA, 2020）から東京湾・三浦半島周辺を抽出しました。2秒角、約50m間隔の数値地形です。内閣府の津波用地形などを統合したもので、原典年代・元測量の密度・基準面に差があります。台船や現在の堤防を正確に表すものではありません。</p><p><a href="https://kiyuu.bosai.go.jp/GtTM/" target="_blank" rel="noopener">GtTM 配布元・ライセンス ↗</a> / <a href="https://doi.org/10.17598/NIED.0021" target="_blank" rel="noopener">DOI ↗</a><br>CC BY 4.0。範囲抽出、再配列、計算格子への補間を行っています。<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">ライセンス ↗</a></p><h3>沿岸参考計算</h3><p>新安浦・猿島・馬堀周辺の100m格子で、岸を通過しない定常ポテンシャル流を計算します。沖合の公式推算に合わせた参考値です。この方式は渦の発生・残留を再現しません。</p><h3>10月24日の潮汐試験</h3><p>試験データが利用できる場合は、湾奥〜勝山・三崎を含む250m格子で、自由水面、移流、粘性、底面抵抗、地球自転を扱う計算を表示します。油壺・布良の気象庁天文潮位を境界に与えています。固定した海陸境界と線形化した連続式を使い、干出・冠水、風、河川、成層、二枚潮、細かな港内は含みません。観察に合わせて係数を調整していません。</p><p>これは当日の事例計算で、任意の日付の実用的な局所流予報ではありません。水位比較が合っても流速・渦の精度を確認したことにはなりません。</p>${experimentMeta?'<p>境界には使わなかった東京の天文潮位との比較：24時間・30分刻みの水位RMSE 約'+(experimentMeta.report.tokyoAstronomicalTideRMSEM*100).toFixed(1)+'cm。これは天文潮位同士の整合性の確認で、実測潮位や実測流速との検証ではありません。</p>':''}<h3>青枠と緑枠</h3><p>青枠は地図表示の範囲、緑破線は選んだ計算方式の対象範囲です。陸地・浅すぎる場所・欠測域には値を出しません。</p><h3>公式潮流と観音崎の研究</h3><p><a href="${S.frames[0]?.source||'https://www1.kaiho.mlit.go.jp/TIDE/pred2/CurrPred/iCurrPred.htm'}" target="_blank" rel="noopener">海上保安庁 潮流推算 ↗</a><br><a href="https://www.pari.go.jp/PDF/no1276.pdf" target="_blank" rel="noopener">港湾空港技術研究所資料1276（観音崎の潮汐渦・残差流）↗</a></p><p>航海目的には海上保安庁刊行の潮汐表をご使用ください。</p>`);
function updatePeek(f){
 const valid=f.bearing!=null&&(S.mode!=='local'||!!S.weights);
 $('peekFlow').textContent=valid?(f.speed<.04?'ほぼ停止':compass(f.bearing)+'へ')+' · '+f.speed.toFixed(1)+' kn':f.reason==='outside'?'この海域の沿岸計算は未対応':f.reason==='view-outside'?'表示対象範囲外':S.loading?'データ取得中…':f.reason==='loading'?'潮流データを取得できません':'この地点は表示対象外';
 $('peekNote').textContent=S.loading?'データ取得中':S.mode==='official'?'最寄りの沖合推算点の値':S.mode==='experiment'?'10/24 自由水面の潮汐試験 · 未検証':'沿岸の参考計算 · 実測未検証';
 $('peekArrow').textContent=valid?(f.speed<.04?'·':'↑'):'—';$('peekArrow').style.transform=valid?'rotate('+f.bearing+'deg)':'';
}
$('pointPeek').onclick=()=>$('inspector').scrollIntoView({behavior:'smooth',block:'center'});
let googlePromise=null,googleScript=null,googleKey='',googleOverlay=null,googleListeners=[],rejectGoogle=null,googleSession=0,googleConnectPromise=null;
const storeRemove=(store,key)=>{try{store.removeItem(key);}catch{}};
function useStandard(){
 ++googleSession;
 if(S.google){const c=S.google.getCenter();if(c)S.center={lat:c.lat(),lon:c.lng()};S.zoom=Math.round(S.google.getZoom());}
 if(googleOverlay){googleOverlay.setMap(null);googleOverlay=null;}
 for(const l of googleListeners)l.remove();googleListeners=[];
 S.google=null;S.projection=null;document.body.classList.remove('google');
 $('googleMap').replaceChildren();
 $('mapCredit').textContent='地理院タイル（標準地図） / 水深 NIED GtTM · CC BY 4.0';
 $('gestureHelp').textContent='二本指で拡大縮小 · タップで地点選択';
 draw();
}
function openSettings(){
 modal('地点を座標で指定',`<p>緯度・経度を入力して、確認したい海上の地点へ移動できます。</p>
 <div class="point-grid"><label>北緯<input id="lat" type="number" step=".00001" value="${S.pin.lat.toFixed(5)}"></label><label>東経<input id="lon" type="number" step=".00001" value="${S.pin.lon.toFixed(5)}"></label></div><p id="settingsMessage" role="status"></p><button id="setCoordinates" class="primary">この地点を表示</button><button id="reset">初期位置に戻す</button>`);
 $('setCoordinates').onclick=()=>{const p={lat:+$('lat').value,lon:+$('lon').value};if(!Number.isFinite(p.lat)||!Number.isFinite(p.lon)||!contains(VIEW_AREA,p)){$('settingsMessage').textContent='青枠内（湾奥〜勝山沖・三崎周辺）の緯度・経度を入力してください。';return;}selectPoint(p);go(p,15);$('modal').close();};
 $('reset').onclick=()=>{selectPoint({...OBS});go(OBS,14);$('modal').close();};
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
 overlay.onAdd=()=>{};overlay.onRemove=()=>{};overlay.draw=()=>{if(session===googleSession&&S.google===map){S.projection=overlay.getProjection();drawOverlay();}};overlay.setMap(map);
 googleListeners.push(map.addListener('click',e=>{if(e.latLng)selectPoint({lat:e.latLng.lat(),lon:e.latLng.lng()});}));
 googleListeners.push(map.addListener('idle',()=>{if(S.google!==map)return;const c=map.getCenter();S.center={lat:c.lat(),lon:c.lng()};S.zoom=map.getZoom();drawOverlay();}));
 await new Promise((resolve,reject)=>{let done=false;const finish=error=>{if(done)return;done=true;clearTimeout(timeout);rejectGoogle=null;error?reject(error):resolve();};rejectGoogle=e=>finish(e);const timeout=setTimeout(()=>finish(Error('地図の表示を確認できませんでした。')),15000);googleListeners.push(map.addListener('tilesloaded',()=>finish()));});
 if(session!==googleSession)throw Error('地図の切り替えを取り消しました。');
 $('mapCredit').textContent='Google Maps / 流れ SHIO（沿岸参考計算） / 水深 NIED GtTM · CC BY 4.0';
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
 localModelReady=(async()=>{S.model=await resource('/api/coastal-model');mapImage=new Image();mapImage.onload=()=>{mapReady=true;drawBase();};mapImage.src='/coastal-map.webp';draw();return S.model;})();
 const overviewTask=(async()=>{try{S.overview=await resource('/overview-map.json');overviewImage=new Image();overviewImage.onload=()=>{overviewReady=true;drawBase();};overviewImage.src='/overview-map.webp';}catch{ /* Live map tiles remain independent. */ }})();
 await Promise.allSettled([localModelReady,overviewTask,load(),restoreGoogle()]);
}
init();
