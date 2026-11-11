import json,sys
from shapely.geometry import shape,MultiPolygon
from shapely.ops import unary_union
src,out,tol,minarea=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4])
d=json.load(open(src,encoding='utf-8'))
gs=[]
for f in d['features']:
    g=shape(f['geometry'])
    if not g.is_valid: g=g.buffer(0)
    gs.append(g)
from shapely.geometry import box
u=unary_union(gs).buffer(0.001).buffer(-0.001)
u=u.difference(box(138.55,34.595,140.871,36.75)).difference(box(134.25,33.70,135.80,35.00))
u=u.simplify(tol,preserve_topology=True)
polys=list(u.geoms) if isinstance(u,MultiPolygon) else [u]
polys=[p for p in polys if p.area>minarea];polys.sort(key=lambda p:-p.area)
parts=[];n=0
for p in polys:
    pts=[(round(x*100),round(y*100)) for x,y in p.exterior.coords[:-1]]   # 0.01 deg units
    ded=[pts[0]]
    for q in pts[1:]:
        if q!=ded[-1]: ded.append(q)
    if len(ded)<3: continue
    v=[ded[0][0],ded[0][1]]
    for a,b in zip(ded,ded[1:]): v+=[b[0]-a[0],b[1]-a[1]]
    parts.append(','.join(map(str,v)));n+=len(ded)
s=';'.join(parts);open(out,'w').write(s)
print(tol,minarea,'polys',len(parts),'pts',n,'chars',len(s))
