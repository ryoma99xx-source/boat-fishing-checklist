import {shapeBearing} from '/geometry.js';
export async function extract(d){const img=new Image();img.src=d.image;await img.decode();const c=document.createElement('canvas');c.width=img.width;c.height=img.height;const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(img,0,0);const data=ctx.getImageData(0,0,c.width,c.height).data,w=c.width,h=c.height;const palette=new Map([['106,90,205',1],['0,0,255',2],['153,153,153',3],['0,64,0',4],['255,0,0',5]]);const mask=new Uint8Array(w*h),visited=new Uint8Array(w*h);const X1=d.area==='03'?w-36:478,Y1=d.area==='03'?h-36:610;for(let y=36;y<Y1;y++)for(let x=36;x<X1;x++){if(d.area==='03'?(x>420&&y>220&&y<340):(x>280&&y>380))continue;const i=(y*w+x)*4;const pc=palette.get(data[i]+','+data[i+1]+','+data[i+2]);if(pc)mask[y*w+x]=pc;}
const comps=[];for(let i=0;i<mask.length;i++){if(!mask[i]||visited[i])continue;const q=[i],points=[];visited[i]=1;let minx=w,maxx=0,miny=h,maxy=0;while(q.length){const v=q.pop(),x=v%w,y=Math.floor(v/w);points.push([x,y]);minx=Math.min(minx,x);maxx=Math.max(maxx,x);miny=Math.min(miny,y);maxy=Math.max(maxy,y);for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const z=v+dy*w+dx;if(z>=0&&z<mask.length&&mask[z]===mask[v]&&!visited[z]){visited[z]=1;q.push(z);}}}if(points.length>=12&&maxx-minx<60&&maxy-miny<60)comps.push({points,minx,maxx,miny,maxy});}
for(const s of d.stations){let best=null,min=20;for(const a of comps){const dist=Math.hypot((a.minx+a.maxx)/2-s.x,(a.miny+a.maxy)/2-s.y);if(dist<min){best=a;min=dist;}}s.component=best;if(best)best.uses=(best.uses||0)+1;}
for(const s of d.stations){const comp=s.component;delete s.component;if(!comp||comp.uses>1)continue;const {points,minx,maxx,miny,maxy}=comp;s.sprite=arrowSprite(points,data,w,minx,miny,maxx,maxy);s.minx=minx-2;s.miny=miny-2;s.bearing=shapeBearing(points);}
d.overlay=coastlineCanvas(data,w,h,d.area);const count=d.stations.filter(s=>s.sprite).length;if(count<d.stations.length*.8)throw new Error('公式図の矢印を正しく読み取れませんでした。原図を確認してください。');return d;}

// Official arrow in its published colours (grey lightened for the dark map) with a white halo.
function arrowSprite(points,data,w,minx,miny,maxx,maxy){
 const sw=maxx-minx+5,sh=maxy-miny+5,c=document.createElement('canvas');c.width=sw;c.height=sh;const ctx=c.getContext('2d'),img=ctx.createImageData(sw,sh),o=img.data;
 for(const [x,y] of points)for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++){if(dx*dx+dy*dy>5)continue;const k=((y-miny+2+dy)*sw+(x-minx+2+dx))*4;o[k]=o[k+1]=o[k+2]=255;o[k+3]=Math.max(o[k+3],210);}
 for(const [x,y] of points){const i=(y*w+x)*4,k=((y-miny+2)*sw+(x-minx+2))*4,gray=data[i]===153&&data[i+1]===153;o[k]=gray?120:data[i];o[k+1]=gray?132:data[i+1];o[k+2]=gray?148:data[i+2];o[k+3]=255;}
 ctx.putImageData(img,0,0);return c;
}
// The chart's own coastline (brown lines) as a transparent layer, to check how the chart lines up with the map.
function coastlineCanvas(data,w,h,area){
 const c=document.createElement('canvas');c.width=w;c.height=h;const ctx=c.getContext('2d'),img=ctx.createImageData(w,h),o=img.data;
 const x1=area==='03'?w-36:478,y1=area==='03'?h-36:610;for(let y=36;y<y1;y++)for(let x=36;x<x1;x++){if(area==='03'?(x>420&&y>220&&y<340):(x>280&&y>380))continue;const k=(y*w+x)*4;if(data[k]===139&&data[k+1]===69&&data[k+2]===19){o[k]=255;o[k+1]=170;o[k+2]=90;o[k+3]=200;}}
 ctx.putImageData(img,0,0);return c;
}
