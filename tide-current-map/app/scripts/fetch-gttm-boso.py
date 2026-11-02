"""Extract the Boso Peninsula region (Tateyama/Sunosaki - outer Boso - Choshi - southern Kashima-nada, 34.80-36.05N) from the CC-BY-4.0 NIED GtTM GMT/NetCDF grid via HTTP Range.
Only a latitude band is transferred, then the desired longitude range is kept.
GMT classic grids store z north-to-south; output latitude is ascending.
"""
import os,struct,json,urllib.request,math,hashlib
import numpy as np
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL='https://kiyuu.bosai.go.jp/GtTM/TwDB/nankaiTrough.grd'
CACHE=ROOT+'/data/source-cache';os.makedirs(CACHE,exist_ok=True)
def request_range(a,b):
 req=urllib.request.Request(URL,headers={'Range':f'bytes={a}-{b}'})
 r=urllib.request.urlopen(req,timeout=40)
 if r.status!=206 or not r.headers.get('Content-Range','').startswith(f'bytes {a}-{b}/'):raise RuntimeError('Server did not honor the requested byte range')
 return r
header=request_range(0,16383).read();pos=4
def integer():
 global pos
 v=struct.unpack_from('>I',header,pos)[0];pos+=4;return v
def string():
 global pos
 n=integer();v=header[pos:pos+n].decode(errors='replace');pos+=(n+3)//4*4;return v
def attributes():
 global pos
 tag=integer();n=integer();out={}
 for _ in range(n):
  name=string();typ=integer();num=integer();sz={1:1,2:1,3:2,4:4,5:4,6:8}[typ];raw=header[pos:pos+num*sz];pos+=(num*sz+3)//4*4
  out[name]=raw.decode(errors='replace').rstrip('\x00')if typ==2 else list(struct.unpack('>'+{1:'b',3:'h',4:'i',5:'f',6:'d'}[typ]*num,raw))
 return out
if header[:4]!=b'CDF\x01':raise RuntimeError('Unexpected grid format')
integer();integer();nd=integer();dims=[(string(),integer())for _ in range(nd)];attributes();integer();nv=integer();variables={}
for _ in range(nv):
 name=string();n=integer();ds=[integer()for _ in range(n)];attrs=attributes();typ=integer();size=integer();offset=integer();variables[name]={'offset':offset,'type':typ,'attrs':attrs}
def field(name,fmt):return struct.unpack_from(fmt,header,variables[name]['offset'])
x0,x1=field('x_range','>2d');y0,y1=field('y_range','>2d');dx,dy=field('spacing','>2d');nx,ny=field('dimension','>2i')
if nx*ny!=dims[1][1]or variables['z']['type']!=5:raise RuntimeError('Grid dimensions do not match')
south,north,west,east=34.80,36.05,139.55,141.10
row0=max(0,math.floor((y1-north)/dy));row1=min(ny-1,math.ceil((y1-south)/dy));col0=max(0,math.floor((west-x0)/dx));col1=min(nx-1,math.ceil((east-x0)/dx))
start=variables['z']['offset']+row0*nx*4;end=variables['z']['offset']+(row1+1)*nx*4-1
p=CACHE+'/gttm-boso-band.bin';expected=end-start+1
if not os.path.exists(p)or os.path.getsize(p)!=expected:
 print('Downloading required latitude band:',round(expected/1e6,1),'MB',flush=True)
 with request_range(start,end)as r,open(p+'.partial','wb')as f:
  while True:
   block=r.read(2**20)
   if not block:break
   f.write(block)
 if os.path.getsize(p+'.partial')!=expected:raise RuntimeError('Incomplete download')
 os.replace(p+'.partial',p)
z=np.memmap(p,dtype='>f4',mode='r',shape=(row1-row0+1,nx))[:,col0:col1+1][::-1].astype('float32')
lats=y1-np.arange(row1,row0-1,-1)*dy;lons=x0+np.arange(col0,col1+1)*dx
# stored as int16 decimetres (+-3276 m clipped is irrelevant: deeper ocean is only a boundary)
np.savez_compressed(ROOT+'/data/gttm-boso.npz',lat=lats,lon=lons,depth_dm=np.clip(np.round(np.nan_to_num(z,nan=0)*10),-32767,32767).astype('<i2'))
meta={'name':'GtTM Whole Japan / Nankai Trough subset','author':'Naotaka CHIKASADA (2020), NIED','doi':'https://doi.org/10.17598/NIED.0021','source':URL,'info':'https://kiyuu.bosai.go.jp/GtTM/','license':'CC BY 4.0','licenseUrl':'https://creativecommons.org/licenses/by/4.0/','gridArcSeconds':2,'datum':'JGD2000 (per GtTM creation notes)','verticalDatum':'Mixed source vertical references; not verified locally','signConvention':'positive depth below water, negative elevation on land (checked against known sea/land sites)','sourceYears':'CAO tsunami terrain published 2012 / central disaster council 2005 / GEBCO 2019','changes':'Boso region subset, latitude reordered, stored as int16 decimetres (depth clipped at 3276.7 m); resampled later for model computation','bounds':{'south':float(lats[0]),'north':float(lats[-1]),'west':float(lons[0]),'east':float(lons[-1])},'shape':list(z.shape),'finite':int(np.isfinite(z).sum()),'depthPositiveDownRange':[float(np.nanmin(z)),float(np.nanmax(z))],'sha256':hashlib.sha256(z.tobytes()).hexdigest()}
json.dump(meta,open(ROOT+'/data/gttm-boso-provenance.json','w'),ensure_ascii=False,indent=2)
print(json.dumps(meta,ensure_ascii=False),flush=True)
