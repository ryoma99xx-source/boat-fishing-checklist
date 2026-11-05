import {normalize} from './geometry.js';
export function prepareExperiment(meta){const ids=new Int32Array(meta.nx*meta.ny);ids.fill(-1);meta.wetIds.forEach((cell,i)=>ids[cell]=i);return {...meta,index:ids,n:Math.max(meta.nx,meta.ny)};}
export function experimentBounds(g){return {south:g.lat0+g.dlat*.5,north:g.lat0+g.dlat*(g.ny-1.5),west:g.lon0+g.dlon*.5,east:g.lon0+g.dlon*(g.nx-1.5)};}
export function sampleExperiment(g,vector,lat,lon){
 const x=Math.round((lon-g.lon0)/g.dlon),y=Math.round((lat-g.lat0)/g.dlat);if(x<1||y<1||x>=g.nx-1||y>=g.ny-1)return {reason:'outside'};const cell=y*g.nx+x,i=g.index[cell];if(i<0)return {reason:g.mask[cell]===2?'depth':'land'};
 if(!vector)return {reason:'loading'};const u=vector[i*2]*g.velocityScale,v=vector[i*2+1]*g.velocityScale,speed=Math.hypot(u,v)/.514444,bearing=normalize(Math.atan2(u,v)*180/Math.PI),offshore=Math.hypot(u,v)?(u*g.ne[i]+v*g.nn[i])/Math.hypot(u,v):0;
 const left=g.index[cell-1],right=g.index[cell+1],south=g.index[cell-g.nx],north=g.index[cell+g.nx];let vorticity=null;
 if(Math.min(left,right,south,north)>=0)vorticity=((vector[right*2+1]-vector[left*2+1])-(vector[north*2]-vector[south*2]))*g.velocityScale/(2*g.dx);
 return {lat:g.lat0+y*g.dlat,lon:g.lon0+x*g.dlon,speed,bearing,uMps:u,vMps:v,depth:g.depth[i],shore:g.shore[i],cellSize:g.dx,vorticity,shoreType:speed<.1?'ごく弱い流れ':Math.abs(offshore)<.35?'岸に沿う成分が主':offshore>0?'岸から離れる成分あり':'岸へ寄る成分あり'};
}
