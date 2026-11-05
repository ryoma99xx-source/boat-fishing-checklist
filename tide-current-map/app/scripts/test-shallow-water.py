import numpy as np
from shallow_water import ShallowWater

ny,nx=25,35;y,x=np.mgrid[:ny,:nx];H=10+5*np.sin(x/10)**2;H[7:15,13:20]=0
m=ShallowWater(H,250,dt=20)
for _ in range(50):d=m.step()
assert np.max(np.abs(m.eta))<1e-12 and np.max(np.abs(m.u))<1e-12
print('PASS: variable-depth still water stays still')
m.u[m.umask]=np.random.default_rng(0).normal(0,.01,m.umask.sum());m.v[m.vmask]=np.random.default_rng(1).normal(0,.01,m.vmask.sum())
d=m.step();assert d['massResidualM']<1e-10 and d['landFaceFlux']==0
print('PASS: face mass conservation and impermeable land',d)
# A closed basin: no boundary cells and no forcing. Energy must decrease.
H=np.zeros((31,31));H[1:-1,1:-1]=20;m=ShallowWater(H,250,dt=10,viscosity=10,drag=.005,coriolis=0)
m.eta[7:15,9:18]=.05;e0=m.energy()
for _ in range(300):m.step()
assert m.energy()<e0;assert abs(np.sum(m.eta))<20
print('PASS: closed-basin energy decreases',e0,m.energy())
