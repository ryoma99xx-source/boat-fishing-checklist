export const rad=d=>d*Math.PI/180;
export const normalize=d=>(d%360+360)%360;
export function distanceKm(a,b){const dl=rad(b.lon-a.lon),dp=rad(b.lat-a.lat);const x=Math.sin(dp/2)**2+Math.cos(rad(a.lat))*Math.cos(rad(b.lat))*Math.sin(dl/2)**2;return 6371*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));}
export function facing(heading,seat){return normalize(+heading+({port:-90,starboard:90,bow:0,stern:180}[seat]||0));}
export function compass(b){return ['北','北北東','北東','東北東','東','東南東','南東','南南東','南','南南西','南西','西南西','西','西北西','北西','北北西'][Math.round(normalize(b)/22.5)%16];}
export function relativeFlow(bearing,face,speed){if(speed<.2)return '弱い流れ・向きの読み取りに注意';const x=Math.cos(rad(bearing-face)),y=Math.sin(rad(bearing-face));if(Math.abs(x)>.5)return x>0?'手前から奥へ、払い出す向き':'奥から手前へ、向かってくる';return y>0?'正面を横切り、右へ流れる':'正面を横切り、左へ流れる';}
// Digitize only the supplied chart's arrow shape. This is not a hydrodynamic model.
export function shapeBearing(points){const n=points.length;if(n<10)return null;const cx=points.reduce((s,p)=>s+p[0],0)/n,cy=points.reduce((s,p)=>s+p[1],0)/n;let xx=0,xy=0,yy=0;for(const [x,y] of points){xx+=(x-cx)**2;xy+=(x-cx)*(y-cy);yy+=(y-cy)**2;}let a=.5*Math.atan2(2*xy,xx-yy);let skew=0;for(const [x,y]of points)skew+=((x-cx)*Math.cos(a)+(y-cy)*Math.sin(a))**3;if(skew>0)a+=Math.PI;return normalize(a*180/Math.PI+90);}
export function chartCoordinate(x,y){return {lat:35+(631-y)/840,lon:139.5+(x-30)/675};}
export function tidePhase(hours,hour){if(!hours||hours[hour]==null)return null;const a=hours[Math.max(0,hour-1)],b=hours[Math.min(23,hour+1)];if(a==null||b==null)return null;const slope=b-a;return Math.abs(slope)<4?'満干潮の付近':slope>0?'潮位は上昇中':'潮位は下降中';}
