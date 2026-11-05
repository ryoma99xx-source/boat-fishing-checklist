import {distanceKm} from './geometry.js';
export const TIDE_POINTS={TK:{name:'東京',lat:35.65,lon:139.766667},Z1:{name:'油壺',lat:35.166667,lon:139.616667},MR:{name:'布良',lat:34.916667,lon:139.833333},TT:{name:'館山',lat:34.983333,lon:139.85},ZF:{name:'勝浦',lat:35.133333,lon:140.25},CS:{name:'銚子漁港',lat:35.75,lon:140.866667}};
export function nearestTideStation(point){return Object.keys(TIDE_POINTS).reduce((a,b)=>distanceKm(point,TIDE_POINTS[a])<=distanceKm(point,TIDE_POINTS[b])?a:b);}
function spline(points){
 const n=points.length,h=[],d=[],m=Array(n).fill(0);for(let i=0;i<n-1;i++){h[i]=points[i+1].x-points[i].x;d[i]=(points[i+1].y-points[i].y)/h[i];}
 if(n===2)m[0]=m[1]=d[0];
 if(n>2){for(let i=1;i<n-1;i++)if(d[i-1]*d[i]>0){const w1=2*h[i]+h[i-1],w2=h[i]+2*h[i-1];m[i]=(w1+w2)/(w1/d[i-1]+w2/d[i]);}
  const endpoint=(a,b,da,db)=>{let v=((2*a+b)*da-a*db)/(a+b);if(v*da<=0)return 0;if(da*db<0&&Math.abs(v)>3*Math.abs(da))v=3*da;return v};m[0]=endpoint(h[0],h[1],d[0],d[1]);m[n-1]=endpoint(h[n-2],h[n-3],d[n-2],d[n-3]);}
 return points.map((p,i)=>({...p,m:m[i]}));
}
export function prepareTide(data){
 const values=data.dayHours||data.hours,segments=[];let run=[];
 function finish(){if(!run.length)return;const start=run[0].x,end=run.at(-1).x;for(const e of data.events||[])if(e.hour>=start&&e.hour<=end&&Number.isFinite(e.height)){const i=run.findIndex(p=>Math.abs(p.x-e.hour)<1e-8),p={x:e.hour,y:e.height};if(i>=0)run[i]=p;else run.push(p)}run.sort((a,b)=>a.x-b.x);segments.push(spline(run));run=[];}
 values.forEach((v,i)=>{if(Number.isFinite(v))run.push({x:i,y:v});else finish()});finish();return {...data,segments};
}
export function tideAt(g,hour){
 const p=g.segments.find(p=>hour>=p[0].x&&hour<=p.at(-1).x);if(!p)return null;if(p.length===1)return {height:p[0].y,slope:0};let i=p.findIndex((v,j)=>j<p.length-1&&hour<=p[j+1].x);if(i<0)i=p.length-2;const a=p[i],b=p[i+1],h=b.x-a.x,t=(hour-a.x)/h;
 const height=(2*t**3-3*t**2+1)*a.y+(t**3-2*t**2+t)*h*a.m+(-2*t**3+3*t**2)*b.y+(t**3-t**2)*h*b.m;
 const slope=(6*t*t-6*t)*(a.y-b.y)/h+(3*t*t-4*t+1)*a.m+(3*t*t-2*t)*b.m;
 return {height,slope};
}
export function tideMarkup(g,hour,width=700,height=230,now=null){
 width=Math.max(260,width);const pad={left:36,right:15,top:29,bottom:32},pw=width-pad.left-pad.right,ph=height-pad.top-pad.bottom,values=g.segments.flat().map(p=>p.y);if(!values.length)return '';
 const lo=Math.floor((Math.min(...values)-10)/20)*20,hi=Math.ceil((Math.max(...values)+10)/20)*20,step=hi-lo>180?50:hi-lo>80?25:20,x=v=>pad.left+v/24*pw,y=v=>pad.top+(hi-v)/(hi-lo)*ph;
 const num=v=>Number(v.toFixed(2)),bottom=pad.top+ph;let out=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${g.date} ${g.station}の天文潮位。グラフをタップすると時刻を選択できます"><defs><linearGradient id="tideFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#4fd0d6" stop-opacity=".3"/><stop offset="100%" stop-color="#4fd0d6" stop-opacity=".015"/></linearGradient></defs>`;
 for(let v=Math.ceil(lo/step)*step;v<=hi;v+=step)out+=`<path d="M${x(0)} ${num(y(v))}H${x(24)}" class="tide-grid"/><text x="${pad.left-8}" y="${num(y(v)+4)}" text-anchor="end" class="tide-axis">${v}</text>`;
 for(const h of [0,4,8,12,16,20,24])out+=`<path d="M${num(x(h))} ${pad.top}V${bottom}" class="tide-grid"/><text x="${num(x(h))}" y="${height-10}" text-anchor="${h===0?'start':h===24?'end':'middle'}" class="tide-axis">${h}時</text>`;
 out+=`<text x="3" y="15" class="tide-axis">cm</text>`;
 for(const p of g.segments){let path=`M${num(x(p[0].x))} ${num(y(p[0].y))}`;for(let i=0;i<p.length-1;i++){const a=p[i],b=p[i+1],h=(b.x-a.x)/3;path+=`C${num(x(a.x+h))} ${num(y(a.y+a.m*h))},${num(x(b.x-h))} ${num(y(b.y-b.m*h))},${num(x(b.x))} ${num(y(b.y))}`;}out+=`<path d="${path}L${num(x(p.at(-1).x))} ${bottom}L${num(x(p[0].x))} ${bottom}Z" fill="url(#tideFill)"/><path d="${path}" class="tide-line"/>`;}
 for(const e of g.events||[]){const px=x(e.hour),py=y(e.height),labelY=e.type==='high'?Math.max(14,py-12):Math.min(height-39,py+22),labelX=Math.max(65,Math.min(width-52,px));out+=`<circle cx="${num(px)}" cy="${num(py)}" r="3.4" class="tide-extreme"/><text x="${num(labelX)}" y="${num(labelY)}" text-anchor="middle" class="tide-event">${e.type==='high'?'満':'干'} ${e.time}</text>`;}
 if(now!==null&&now>=0&&now<=24)out+=`<path d="M${num(x(now))} ${pad.top}V${bottom}" class="tide-now"/>`;
 const selected=tideAt(g,hour);if(selected)out+=`<path d="M${num(x(hour))} ${pad.top}V${bottom}" class="tide-selected"/><circle cx="${num(x(hour))}" cy="${num(y(selected.height))}" r="6" class="tide-cursor"/><text x="${num(Math.max(63,Math.min(width-52,x(hour))))}" y="16" text-anchor="middle" class="tide-selected-label">${String(Math.floor(hour)).padStart(2,'0')}:${hour%1?'30':'00'} 選択</text>`;
 return out+'</svg>';
}
