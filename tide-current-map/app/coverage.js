// Geographic viewing envelope, not a promise of current-prediction coverage.
const TOKYO_VIEW={south:34.85,north:35.99,west:139.48,east:141.0};
// 海域ごとの表示範囲・移動先・海上保安庁の推算図（01 東京湾 / 03 瀬戸内）。自作モデルは東京湾だけ。
export const AREAS={
 tokyo:{name:'東京湾',all:'東京湾〜房総 全体',jcg:'01',model:true,view:TOKYO_VIEW,labels:['inner','katsuyama','misaki'],stations:['Z1','TK','MR','TT','ZF','CS'],regions:{
  inner:{name:'湾奥',lat:35.61,lon:139.90,zoom:11},
  katsuyama:{name:'勝山沖',lat:35.113,lon:139.805,zoom:13},
  misaki:{name:'三崎沖',lat:35.13,lon:139.615,zoom:13},
  west:{name:'三浦半島西岸',lat:35.27,lon:139.555,zoom:12},
  uchibo:{name:'内房（館山）',lat:35.0,lon:139.83,zoom:12},
  katsuura:{name:'外房（勝浦）',lat:35.12,lon:140.32,zoom:12},
  kujukuri:{name:'九十九里沖',lat:35.45,lon:140.55,zoom:11},
  choshi:{name:'銚子沖',lat:35.70,lon:140.92,zoom:12}}},
 osaka:{name:'大阪湾',all:'大阪湾 全体',jcg:'03',model:false,view:{south:34.10,north:34.78,west:134.75,east:135.50},labels:['bayhead','akashi','sumoto'],stations:['OS','KB','AM','J5','IO','J2','AK','ST','WY'],regions:{
  bayhead:{name:'大阪湾奥（神戸〜大阪沖）',lat:34.60,lon:135.30,zoom:11},
  akashi:{name:'明石海峡',lat:34.615,lon:135.02,zoom:12},
  kishiwada:{name:'泉州沖（岸和田）',lat:34.47,lon:135.28,zoom:12},
  sumoto:{name:'洲本沖',lat:34.34,lon:134.95,zoom:12},
  tomogashima:{name:'友ヶ島水道（紀淡海峡）',lat:34.28,lon:135.03,zoom:12}}}
};
export let AREA='tokyo',VIEW_AREA=TOKYO_VIEW,REGIONS=AREAS.tokyo.regions;
export function setArea(k){if(!AREAS[k])return;AREA=k;VIEW_AREA=AREAS[k].view;REGIONS=AREAS[k].regions;}
export function areaOf(p){for(const k in AREAS)if(contains(AREAS[k].view,p))return k;return null;}
export function contains(bounds,p){return Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&p.lat>=bounds.south&&p.lat<=bounds.north&&p.lon>=bounds.west&&p.lon<=bounds.east;}
export function modelBounds(g){return {south:g.lat0+g.dlat*.5,north:g.lat0+g.dlat*(g.n-1.5),west:g.lon0+g.dlon*.5,east:g.lon0+g.dlon*(g.n-1.5)};}
function world(lat,lon){const s=Math.sin(lat*Math.PI/180);return {x:(lon+180)/360*256,y:(.5-Math.log((1+s)/(1-s))/(4*Math.PI))*256};}
export function fitArea(bounds,width,height,padding=44){
 const nw=world(bounds.north,bounds.west),se=world(bounds.south,bounds.east),x=(nw.x+se.x)/2,y=(nw.y+se.y)/2;
 const zoom=Math.max(8,Math.min(18,Math.floor(Math.min(Math.log2(Math.max(64,width-2*padding)/(se.x-nw.x)),Math.log2(Math.max(64,height-2*padding)/(se.y-nw.y))))));
 return {center:{lat:Math.atan(Math.sinh(Math.PI*(1-2*y/256)))*180/Math.PI,lon:x/256*360-180},zoom};
}
