"""Prepare a reproducible, explicitly unvalidated local potential-flow experiment.

Inputs: NIED GtTM (2 arc seconds), GSI standard cartographic tiles for map only.
Solve div(H grad(phi)) = 0 with impermeable land faces and uniform-potential
Dirichlet conditions at open edges. Unit east and north solutions are stored.
This is steady kinematic downscaling, NOT a time-dependent tidal forecast.
"""
import os,json,math,io,urllib.request,concurrent.futures
import numpy as np
from PIL import Image
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import distance_transform_edt,label
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import splu

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(ROOT+'/data/coastal-cache',exist_ok=True)
N=141;DX=100;LAT=35.285;LON=139.72
DLAT=DX/111195;DLON=DX/(111195*math.cos(math.radians(LAT)))
lats=LAT+(np.arange(N)-(N-1)/2)*DLAT
lons=LON+(np.arange(N)-(N-1)/2)*DLON
def world(lat,lon,z=14):
 s=math.sin(math.radians(lat));return (lon+180)/360*256*2**z,(.5-math.log((1+s)/(1-s))/(4*math.pi))*256*2**z
left,bot=world(lats[0],lons[0]);right,top=world(lats[-1],lons[-1])
tx0,tx1=int(left//256),int(right//256);ty0,ty1=int(top//256),int(bot//256)
print('Tiles',tx0,tx1,ty0,ty1,flush=True)
def fetch_tile(pair):
 x,y=pair;p=f'{ROOT}/data/coastal-cache/{x}-{y}.png'
 if not os.path.exists(p):
  u=f'https://cyberjapandata.gsi.go.jp/xyz/std/14/{x}/{y}.png'
  b=urllib.request.urlopen(u,timeout=15).read();open(p,'wb').write(b)
 return x,y,Image.open(p).convert('RGB')
mosaic=Image.new('RGB',((tx1-tx0+1)*256,(ty1-ty0+1)*256))
with concurrent.futures.ThreadPoolExecutor(4)as pool:
 for x,y,im in pool.map(fetch_tile,[(x,y)for y in range(ty0,ty1+1)for x in range(tx0,tx1+1)]):mosaic.paste(im,((x-tx0)*256,(y-ty0)*256))
print('Mosaic ready',mosaic.size,flush=True)
mosaic.save(ROOT+'/data/coastal-map.webp',quality=86)
raw=np.load(ROOT+'/data/gttm-tokyo.npz')
interp=RegularGridInterpolator((raw['lat'],raw['lon']),raw['depth'],bounds_error=True)
yy,xx=np.meshgrid(lats,lons,indexing='ij');depth=interp(np.column_stack([yy.ravel(),xx.ravel()])).reshape(N,N)
# GtTM's GMT file is positive water depth and negative land height.
wet=np.isfinite(depth)&(depth>0)
labs,num=label(wet);edge_labels=set(labs[0])|set(labs[-1])|set(labs[:,0])|set(labs[:,-1]);edge_labels.discard(0)
wet=np.isin(labs,list(edge_labels));coast_wet=wet.copy()
# Never invent a water depth where the source elevation is above sea level.
source_valid=np.isfinite(depth)&(depth>=2)
wet &= source_valid
labs,num=label(wet);edge_labels=set(labs[0])|set(labs[-1])|set(labs[:,0])|set(labs[:,-1]);edge_labels.discard(0);wet=np.isin(labs,list(edge_labels))
depth=np.where(wet,depth,0)
ids=np.full((N,N),-1,int);ids[wet]=np.arange(wet.sum());M=int(wet.sum())
A=lil_matrix((M,M));rhs=np.zeros((M,2));edge=np.zeros_like(wet)
for iy,ix in np.argwhere(wet):
 k=ids[iy,ix]
 if ix in [0,N-1]or iy in [0,N-1]:
  edge[iy,ix]=True;A[k,k]=1;rhs[k]=[(ix-(N-1)/2)*DX,(iy-(N-1)/2)*DX];continue
 for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
  jy,jx=iy+dy,ix+dx
  if wet[jy,jx]:
   # Harmonic mean depth makes the shared face flux conservative.
   h=2*depth[iy,ix]*depth[jy,jx]/(depth[iy,ix]+depth[jy,jx])
   A[k,k]+=h;A[k,ids[jy,jx]]-=h
print('Solving',M,'wet cells',flush=True)
phi=splu(A.tocsc()).solve(rhs);residual=float(np.max(np.abs(A@phi-rhs)))
P=np.zeros((N,N,2));P[wet]=phi
U=np.zeros_like(P);V=np.zeros_like(P);div=np.zeros_like(P)
for iy,ix in np.argwhere(wet):
 ue=uw=vn=vs=np.zeros(2)
 if ix+1<N and wet[iy,ix+1]:ue=(P[iy,ix+1]-P[iy,ix])/DX
 if ix>0 and wet[iy,ix-1]:uw=(P[iy,ix]-P[iy,ix-1])/DX
 if iy+1<N and wet[iy+1,ix]:vn=(P[iy+1,ix]-P[iy,ix])/DX
 if iy>0 and wet[iy-1,ix]:vs=(P[iy,ix]-P[iy-1,ix])/DX
 U[iy,ix]=(ue+uw)/2;V[iy,ix]=(vn+vs)/2
 for dy,dx,v in [(0,1,ue),(0,-1,-uw),(1,0,vn),(-1,0,-vs)]:
  jy,jx=iy+dy,ix+dx
  if 0<=jy<N and 0<=jx<N and wet[jy,jx]:div[iy,ix]+=2*depth[iy,ix]*depth[jy,jx]/(depth[iy,ix]+depth[jy,jx])*v/DX
distance,nearest=distance_transform_edt(coast_wet,sampling=DX,return_indices=True)
ne=np.zeros_like(depth);nn=np.zeros_like(depth)
for iy,ix in np.argwhere(wet):
 dy=iy-nearest[0,iy,ix];dx=ix-nearest[1,iy,ix];r=math.hypot(dx,dy)
 if r:ne[iy,ix]=dx/r;nn[iy,ix]=dy/r
cells=[]
for iy in range(N):
 for ix in range(N):
  if not wet[iy,ix]:cells.append(None);continue
  cells.append([round(float(depth[iy,ix]),1),round(float(U[iy,ix,0]),5),round(float(V[iy,ix,0]),5),round(float(U[iy,ix,1]),5),round(float(V[iy,ix,1]),5),round(float(distance[iy,ix])),round(float(ne[iy,ix]),3),round(float(nn[iy,ix]),3)])
interior=wet&~edge
out={'version':2,'name':'新安浦・猿島・馬堀海岸 沿岸参考モデル','n':N,'dx':DX,'lat0':float(lats[0]),'lon0':float(lons[0]),'dlat':DLAT,'dlon':DLON,'cells':cells,'mask':np.where(wet,1,np.where(coast_wet,2,0)).ravel().tolist(),'anchor':{'x':190,'y':395,'lat':35+(631-395)/840,'lon':139.5+(190-30)/675},'sourceResolution':'NIED GtTM, 2 arc seconds（約50m間隔・原典の精度は場所により異なる）','depthSource':'https://kiyuu.bosai.go.jp/GtTM/','attribution':'Naotaka CHIKASADA (2020), NIED GtTM; CC BY 4.0; subset and resampled','doi':'https://doi.org/10.17598/NIED.0021','coastSource':'https://maps.gsi.go.jp/development/ichiran.html','map':{'z':14,'x':tx0,'y':ty0,'w':mosaic.width,'h':mosaic.height},'validation':{'linearResidual':residual,'maxInteriorFluxDivergence':float(np.max(np.abs(div[interior]))),'wetCells':M},'limitations':['未検証の定常ポテンシャル流。実際の局所流予報ではありません。','計算格子100mは精度100mを意味しません。元水深は2秒角・約50m間隔。原典の測量密度は一定でない。','細かい堤防・台船・渦・潮汐の慣性・風・成層は含みません。','水深不明・陸地・計算範囲外には推定値を出しません。']}
json.dump(out,open(ROOT+'/data/coastal-model.json','w'),ensure_ascii=False,separators=(',',':'))
json.dump(out['validation'],open(ROOT+'/data/coastal-validation.json','w'),indent=2)
print(out['validation'],flush=True)
