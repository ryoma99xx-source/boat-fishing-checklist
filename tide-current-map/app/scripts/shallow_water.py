"""Experimental fixed-wet, depth-averaged free-surface solver.

MAC face velocities, conservative linearized continuity, implicit gravity,
explicit donor-cell advection, viscosity, Coriolis and quadratic bottom drag.
SI units throughout. This is a numerical experiment, not a validated forecast.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

class ShallowWater:
 def __init__(self,depth,dx,dt=20.,viscosity=5.,drag=.0025,coriolis=8.4e-5):
  self.H=np.asarray(depth,dtype=float);self.wet=self.H>0;self.ny,self.nx=self.H.shape;self.dx=dx;self.dt=dt;self.nu=viscosity;self.cd=drag;self.f=coriolis
  self.ids=np.full(self.H.shape,-1,int);self.ids[self.wet]=np.arange(self.wet.sum());self.edge=np.zeros_like(self.wet);self.edge[0]=self.wet[0];self.edge[-1]=self.wet[-1];self.edge[:,0]=self.wet[:,0];self.edge[:,-1]=self.wet[:,-1];self.inside=self.wet&~self.edge
  self.hu=np.zeros((self.ny,self.nx+1));self.hv=np.zeros((self.ny+1,self.nx))
  a=self.H[:,:-1];b=self.H[:,1:];self.hu[:,1:-1]=np.divide(2*a*b,a+b,out=np.zeros_like(a),where=(a>0)&(b>0))
  a=self.H[:-1];b=self.H[1:];self.hv[1:-1]=np.divide(2*a*b,a+b,out=np.zeros_like(a),where=(a>0)&(b>0))
  self.umask=self.hu>0;self.vmask=self.hv>0;self.u=np.zeros_like(self.hu);self.v=np.zeros_like(self.hv);self.eta=np.zeros_like(self.H)
  rows=[];cols=[];vals=[];fac=dt*dt*9.81/dx**2
  for y,x in np.argwhere(self.wet):
   k=self.ids[y,x]
   if self.edge[y,x]:rows.append(k);cols.append(k);vals.append(1.);continue
   diagonal=1.
   for dy,ddx,h in [(0,1,self.hu[y,x+1]),(0,-1,self.hu[y,x]),(1,0,self.hv[y+1,x]),(-1,0,self.hv[y,x])]:
    if h>0:rows.append(k);cols.append(self.ids[y+dy,x+ddx]);vals.append(-fac*h);diagonal+=fac*h
   rows.append(k);cols.append(k);vals.append(diagonal)
  self.A=coo_matrix((vals,(rows,cols)),shape=(int(self.wet.sum()),int(self.wet.sum()))).tocsc();self.solve=splu(self.A).solve
 def centers(self):return (self.u[:,:-1]+self.u[:,1:])/2,(self.v[:-1]+self.v[1:])/2
 def divergence(self,u,v):return (self.hu[:,1:]*u[:,1:]-self.hu[:,:-1]*u[:,:-1]+self.hv[1:]*v[1:]-self.hv[:-1]*v[:-1])/self.dx
 def energy(self):
  u,v=self.centers();return float(np.sum((self.H*(u*u+v*v)+9.81*self.eta**2)[self.inside])*.5*self.dx**2)
 def step(self,boundary=0.):
  dt=self.dt;dx=self.dx;u=self.u;v=self.v;uc,vc=self.centers();vu=np.zeros_like(u);uv=np.zeros_like(v);vu[:,1:-1]=(vc[:,:-1]+vc[:,1:])/2;uv[1:-1]=(uc[:-1]+uc[1:])/2
  def terms(q,ux,vy):
   p=np.pad(q,1,mode='edge');west=p[1:-1,:-2];east=p[1:-1,2:];south=p[:-2,1:-1];north=p[2:,1:-1]
   adv=ux*np.where(ux>=0,q-west,east-q)/dx+vy*np.where(vy>=0,q-south,north-q)/dx
   return -adv+self.nu*(west+east+south+north-4*q)/dx**2
  ust=(u+dt*(terms(u,u,vu)+self.f*vu))*self.umask
  vst=(v+dt*(terms(v,uv,v)-self.f*uv))*self.vmask
  # Semi-implicit quadratic drag remains stable in shallow cells.
  ust/=1+dt*self.cd*np.divide(np.hypot(u,vu),self.hu,out=np.zeros_like(u),where=self.umask)
  vst/=1+dt*self.cd*np.divide(np.hypot(v,uv),self.hv,out=np.zeros_like(v),where=self.vmask)
  rhs=(self.eta-dt*self.divergence(ust,vst))[self.wet]
  b=np.broadcast_to(boundary,self.H.shape);rhs[self.edge[self.wet]]=b[self.edge]
  eta=np.zeros_like(self.H);eta[self.wet]=self.solve(rhs)
  un=ust.copy();vn=vst.copy();un[:,1:-1]-=dt*9.81*(eta[:,1:]-eta[:,:-1])/dx;vn[1:-1]-=dt*9.81*(eta[1:]-eta[:-1])/dx;un*=self.umask;vn*=self.vmask
  residual=eta-self.eta+dt*self.divergence(un,vn)
  diagnostics={'massResidualM':float(np.max(np.abs(residual[self.inside]))),'landFaceFlux':float(max(np.max(np.abs(un[~self.umask])),np.max(np.abs(vn[~self.vmask])))),'maxSpeedMps':float(max(np.max(np.abs(un)),np.max(np.abs(vn))))}
  if not np.all(np.isfinite(eta))or not np.all(np.isfinite(un))or not np.all(np.isfinite(vn)):raise RuntimeError('Non-finite state')
  if diagnostics['maxSpeedMps']*dt/dx>.5:raise RuntimeError('Advection CFL limit exceeded')
  self.u=un;self.v=vn;self.eta=eta
  return diagnostics
