# Fits the tide harmonic constants used by index.html (TIDE.st) to JMA 潮位表 hourly heights.
# 1) Station list: https://www.data.jma.go.jp/kaiyou/db/tide/suisan/station2026.php
# 2) Tables: https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/<year>/<code>.txt saved as <year>/<code>.txt
# 3) python3 tide_fit.py <code>  (run in the folder holding the year folders) prints the fit error.
# Same 29 constituents, nodal corrections and epoch (2026-01-01 JST) as the app; the result x is
# [mean, a1, b1, a2, b2, ...] rounded to 0.1 cm. Kanto stations 2026-11: 1.7-3 cm RMS; Ariake/Seto up to 8 cm.
import numpy as np, re, json, datetime as dt, sys
SRC=open(__import__('os').path.join(__import__('os').path.dirname(__file__),'..','public','index.html')).read()
sp=[float(x) for x in re.search(r"sp:\[([^\]]*)\]",SRC).group(1).split(',')]
nk=re.search(r"nk:\[([^\]]*)\]",SRC).group(1).replace("'","").split(',')
EP=dt.datetime(2026,1,1,0,0,tzinfo=dt.timezone(dt.timedelta(hours=9))).timestamp()*1000
J2000=dt.datetime(2000,1,1,12,tzinfo=dt.timezone.utc).timestamp()*1000
D=np.pi/180
def nodal(t):
    N=(125.0445-0.0529539*((EP+t*3600e3-J2000)/864e5))*D;c=np.cos;s=np.sin
    M2=(1.0004-0.0373*c(N)+0.0002*c(2*N),-2.14*s(N));K1=(1.006+0.115*c(N)-0.0088*c(2*N)+0.0006*c(3*N),-8.86*s(N)+0.68*s(2*N)-0.07*s(3*N))
    O1=(1.0089+0.1871*c(N)-0.0147*c(2*N)+0.0014*c(3*N),10.8*s(N)-1.34*s(2*N)+0.19*s(3*N));K2=(1.0241+0.2863*c(N)+0.0083*c(2*N)-0.0015*c(3*N),-17.74*s(N)+0.68*s(2*N)-0.04*s(3*N))
    J1=(1.1029+0.1676*c(N)-0.017*c(2*N)+0.0016*c(3*N),-12.94*s(N)+1.34*s(2*N)-0.19*s(3*N));OO1=(1.1027+0.6504*c(N)+0.0317*c(2*N)-0.0014*c(3*N),-36.68*s(N)+4.02*s(2*N)-0.57*s(3*N))
    one=np.ones_like(t)
    return {'1':(one,0*t),'Mm':(1-0.13*c(N),0*t),'Mf':(1.043+0.414*c(N),-23.7*s(N)),'O1':O1,'K1':K1,'J1':J1,'OO1':OO1,'M2':M2,'K2':K2,
      'MO3':(M2[0]*O1[0],M2[1]+O1[1]),'M3':(M2[0]**1.5,1.5*M2[1]),'MK3':(M2[0]*K1[0],M2[1]+K1[1]),'M4':(M2[0]**2,2*M2[1]),'M6':(M2[0]**3,3*M2[1])}
def load(code):
    T=[];H=[]
    for y in (2025,2026,2027):
        for line in open(f'{y}/{code}.txt',encoding='ascii',errors='replace'):
            if len(line)<80:continue
            yy,mm,dd=int(line[72:74]),int(line[74:76]),int(line[76:78])
            base=dt.datetime(2000+yy,mm,dd,tzinfo=dt.timezone(dt.timedelta(hours=9))).timestamp()*1000
            for h in range(24):
                v=line[h*3:h*3+3]
                try:v=int(v)
                except:continue
                if v>=999:continue
                T.append((base+h*3600e3-EP)/3600e3);H.append(v)
    return np.array(T),np.array(H,float)
def design(t):
    nd=nodal(t);cols=[np.ones_like(t)]
    for i,w in enumerate(sp):
        f,u=nd[nk[i]];a=w*D*t+u*D;cols+= [f*np.cos(a),f*np.sin(a)]
    return np.stack(cols,1)
def fit(code):
    t,h=load(code);A=design(t);x,*_=np.linalg.lstsq(A,h,rcond=None);res=h-A@x
    return x,float(np.sqrt(np.mean(res**2))),float(np.max(np.abs(res)))
if __name__=='__main__':
    x,rms,mx=fit(sys.argv[1]);print(sys.argv[1],'rms',round(rms,2),'max',round(mx,1))
    old=re.search(sys.argv[1]+r":\{n:'[^']*',x:'([^']*)'",SRC)
    if old:
        o=np.array([float(v) for v in old.group(1).split(',')]);print('old len',len(o),'new len',len(x));print('max coef diff',np.max(np.abs(o-np.round(x,1))))
