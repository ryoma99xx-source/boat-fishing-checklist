// Geographic viewing envelope, not a promise of current-prediction coverage.
export const VIEW_AREA={south:34.85,north:35.99,west:139.48,east:141.0};
export const REGIONS={
 inner:{name:'湾奥',lat:35.61,lon:139.90,zoom:11},
 katsuyama:{name:'勝山沖',lat:35.113,lon:139.805,zoom:13},
 misaki:{name:'三崎沖',lat:35.13,lon:139.615,zoom:13},
 west:{name:'三浦半島西岸',lat:35.27,lon:139.555,zoom:12},
 uchibo:{name:'内房（館山）',lat:35.0,lon:139.83,zoom:12},
 katsuura:{name:'外房（勝浦）',lat:35.12,lon:140.32,zoom:12},
 kujukuri:{name:'九十九里沖',lat:35.45,lon:140.55,zoom:11},
 choshi:{name:'銚子沖',lat:35.70,lon:140.92,zoom:12}
};
export function contains(bounds,p){return Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&p.lat>=bounds.south&&p.lat<=bounds.north&&p.lon>=bounds.west&&p.lon<=bounds.east;}
export function modelBounds(g){return {south:g.lat0+g.dlat*.5,north:g.lat0+g.dlat*(g.n-1.5),west:g.lon0+g.dlon*.5,east:g.lon0+g.dlon*(g.n-1.5)};}
function world(lat,lon){const s=Math.sin(lat*Math.PI/180);return {x:(lon+180)/360*256,y:(.5-Math.log((1+s)/(1-s))/(4*Math.PI))*256};}
export function fitArea(bounds,width,height,padding=44){
 const nw=world(bounds.north,bounds.west),se=world(bounds.south,bounds.east),x=(nw.x+se.x)/2,y=(nw.y+se.y)/2;
 const zoom=Math.max(8,Math.min(18,Math.floor(Math.min(Math.log2(Math.max(64,width-2*padding)/(se.x-nw.x)),Math.log2(Math.max(64,height-2*padding)/(se.y-nw.y))))));
 return {center:{lat:Math.atan(Math.sinh(Math.PI*(1-2*y/256)))*180/Math.PI,lon:x/256*360-180},zoom};
}
