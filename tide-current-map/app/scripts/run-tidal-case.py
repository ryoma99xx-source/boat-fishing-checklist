"""Reproducible, unvalidated 2026-10-24 Tokyo Bay tidal experiment.

Two JMA tide tables drive the open sea boundaries; Tokyo tide is withheld
for comparison. No tuning to the user's fishing observation is performed.
"""
import os,json,math,time,argparse,datetime
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import label,distance_transform_edt
from shallow_water import ShallowWater

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def tides(station):
 rows=[]
 for line in open(f'{ROOT}/data/{station}-2026.txt'):
  if len(line)<80:continue
  try:
   date=datetime.datetime(2000+int(line[72:74]),int(line[74:76]),int(line[76:78]));h=[int(line[i:i+3])for i in range(0,72,3)]
  except ValueError:continue
  rows.extend((date+datetime.timedelta(hours=i),v/100)for i,v in enumerate(h)if v!=999)
 return rows
def prepare(dx):
 south,north,west,east=35.03,35.75,139.43,140.20
 dlat=dx/111195;dlon=dx/(111195*math.cos(math.radians(35.39)));lat=south+np.arange(int((north-south)/dlat)+1)*dlat;lon=west+np.arange(int((east-west)/dlon)+1)*dlon
 raw=np.load(ROOT+'/data/gttm-tokyo.npz');interp=RegularGridInterpolator((raw['lat'],raw['lon']),raw['depth'])
 yy,xx=np.meshgrid(lat,lon,indexing='ij');depth=interp(np.column_stack([yy.ravel(),xx.ravel()])).reshape(len(lat),len(lon))
 coast=depth>0;wet=depth>=3
 labs,n=label(wet);ids=set(labs[0])|set(labs[-1])|set(labs[:,0])|set(labs[:,-1]);ids.discard(0);wet=np.isin(labs,list(ids))
 H=np.where(wet,depth,0);shore,nearest=distance_transform_edt(coast,sampling=dx,return_indices=True);ne=np.zeros_like(H);nn=np.zeros_like(H)
 yy,xx=np.indices(H.shape);ddx=xx-nearest[1];ddy=yy-nearest[0];r=np.hypot(ddx,ddy);np.divide(ddx,r,out=ne,where=r>0);np.divide(ddy,r,out=nn,where=r>0)
 return lat,lon,H,shore,ne,nn,np.where(wet,1,np.where(coast,2,0))
def run(dx=250,dt=20,spinup=48,viscosity=5,drag=.0025,save=True,suffix=''):
 lat,lon,H,shore,ne,nn,mask=prepare(dx);t0=time.time();m=ShallowWater(H,dx,dt=dt,viscosity=viscosity,drag=drag)
 day=datetime.datetime(2026,10,24);start=day-datetime.timedelta(hours=spinup);total=(spinup+24)*3600
 series={st:tides(st)for st in ['Z1','MR','TK']};offsets={'Z1':.926,'MR':.867,'TK':1.141}
 # JMA 2026 published chart-datum elevations convert tide heights to an elevation reference.
 # GtTM sea-depth vertical references may differ; this residual datum uncertainty remains.
 prepared={st:(np.array([(d-start).total_seconds()for d,_ in rows]),np.array([v-offsets[st]for _,v in rows]))for st,rows in series.items()}
 def level(st,seconds):
  times,values=prepared[st];return np.interp(seconds,times,values)
 table={st:np.array([level(st,t)for t in np.arange(0,total+dt,dt)])for st in ['Z1','MR']}
 westweight=np.clip((lon-139.58)/(139.86-139.58),0,1);nsteps=int(total/dt);wetIds=np.flatnonzero(m.wet);frames=[];checks=[];maxres=0.;maxspeed=0.;sample=[];pin=(int(round((35.279-lat[0])/(lat[1]-lat[0]))),int(round((139.708-lon[0])/(lon[1]-lon[0]))));tokyo=(int(round((35.647-lat[0])/(lat[1]-lat[0]))),int(round((139.769-lon[0])/(lon[1]-lon[0]))))
 print('Experiment',dx,'m',H.shape,'wet',len(wetIds),'steps',nsteps,'spinup',spinup,flush=True)
 for i in range(nsteps+1):
  sec=i*dt
  if sec>=spinup*3600 and (sec-spinup*3600)%1800==0:
   uc,vc=m.centers();vec=np.column_stack([uc.ravel()[wetIds],vc.ravel()[wetIds]])
   if np.max(np.abs(vec))>10:raise RuntimeError('Velocity out of experiment range')
   frames.append(np.round(vec*1000).astype('<i2').tobytes())
   sample.append({'hour':(sec-spinup*3600)/3600,'uMps':float(uc[pin]),'vMps':float(vc[pin]),'etaTokyo':float(m.eta[tokyo]),'etaTokyoTide':float(level('TK',sec))})
  if i==nsteps:break
  boundary=table['Z1'][i+1]*(1-westweight)+table['MR'][i+1]*westweight
  d=m.step(boundary);maxres=max(maxres,d['massResidualM']);maxspeed=max(maxspeed,d['maxSpeedMps'])
  if i%1080==0:print(' step',i,'/',nsteps,'max',round(maxspeed,3),'m/s','elapsed',round(time.time()-t0,1),'s',flush=True)
 rmse=float(np.sqrt(np.mean([(s['etaTokyo']-s['etaTokyoTide'])**2 for s in sample])))
 report={'dxM':dx,'dtS':dt,'spinupHours':spinup,'viscosityM2ps':viscosity,'dragCoefficient':drag,'maxMassResidualM':maxres,'maxFaceSpeedMps':maxspeed,'tokyoAstronomicalTideRMSEM':rmse,'stationReference':'JMA published chart-datum elevations: Z1 -0.926m, MR -0.867m; TK -1.141m. GtTM vertical datum remains approximate','datumOffsetM':offsets,'seconds':time.time()-t0,'samples':sample}
 if save:
  g={'version':1,'date':'2026-10-24','method':'Depth-averaged free-surface tidal experiment','nx':len(lon),'ny':len(lat),'dx':dx,'lat0':float(lat[0]),'lon0':float(lon[0]),'dlat':float(lat[1]-lat[0]),'dlon':float(lon[1]-lon[0]),'frameCount':len(frames),'frameIntervalMinutes':30,'velocityScale':.001,'velocityUnit':'m/s','wetIds':wetIds.tolist(),'depth':np.round(H.ravel()[wetIds],1).tolist(),'shore':np.round(shore.ravel()[wetIds]).astype(int).tolist(),'ne':np.round(ne.ravel()[wetIds],3).tolist(),'nn':np.round(nn.ravel()[wetIds],3).tolist(),'mask':mask.ravel().tolist(),'report':{k:v for k,v in report.items()if k!='samples'},'source':json.load(open(ROOT+'/data/gttm-provenance.json')),'boundaries':{'Z1':'油壺・気象庁天文潮位','MR':'布良・気象庁天文潮位','link':'https://www.data.jma.go.jp/kaiyou/db/tide/suisan/index.php'},'limitations':['2026年10月24日の事例計算。実測流速による検証は未実施。','計算格子250m。台船周辺・狭い港内・二枚潮・風・河川流・干出冠水は対象外。','元地形は約50m間隔だが、原典年代・測量密度・基準面に限界がある。','開境界の潮位は2地点を空間補間。潮位表の基準面高は補正しているが、水深側との基準面差は残る。']}
  json.dump(g,open(ROOT+f'/data/tidal-case{suffix}.json','w'),ensure_ascii=False,separators=(',',':'));open(ROOT+f'/data/tidal-frames{suffix}.bin','wb').write(b''.join(frames))
 json.dump(report,open(ROOT+f'/data/tidal-report{suffix}.json','w'),ensure_ascii=False,indent=2)
 print('DONE',json.dumps({k:v for k,v in report.items()if k!='samples'},ensure_ascii=False),flush=True)
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--dx',type=float,default=250);p.add_argument('--dt',type=float,default=20);p.add_argument('--spinup',type=float,default=48);p.add_argument('--suffix',default='');p.add_argument('--no-save',action='store_true');a=p.parse_args();run(a.dx,a.dt,a.spinup,save=not a.no_save,suffix=a.suffix)
