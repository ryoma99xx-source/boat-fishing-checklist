"""Nested harmonic tidal current model for Tokyo Bay -> Yokosuka coast.

Outer: Tokyo Bay + Uraga Channel + eastern Sagami Bay, forced on its open edges by
tide synthesised from harmonic constants fitted to JMA hourly astronomical tides
(Aburatsubo Z1, Tateyama TT, Okada OK, Ito Z3; Mera MR sits outside the bay mouth and leads by ~14 min, so it is not used), interpolated by inverse distance on
complex amplitudes.
Inner: Yokosuka coast (Shin-Yasuura, Sarushima, Umabori, Kannonzaki, Hashirimizu)
at fine resolution, forced on its open edges by outer-model water level each step.

Both use the existing ShallowWater solver (depth averaged, nonlinear advection,
quadratic bottom drag, Coriolis). The run records hourly currents for harmonic
analysis so any date/time can be synthesised later. Wind, rivers, stratification
and wetting/drying are not modelled. Not validated against current meters here;
see validate-*.py.
"""
import os, sys, json, math, time, argparse, datetime
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import label, distance_transform_edt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shallow_water import ShallowWater
import tidelib as tl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAT_REF = 35.3
FORCING_NAMES = ['Q1','O1','M1','P1','K1','J1','OO1','2N2','MU2','N2','NU2','M2','L2','T2','S2','K2','M3','MK3','MN4','M4','MS4','M6','2MS6']
FIT_NAMES = ['Sa','Ssa','Mm','MSf'] + FORCING_NAMES
STATIONS = {'Z1': (35.160, 139.617), 'TT': (34.983, 139.850), 'OK': (34.783, 139.383), 'Z3': (34.900, 139.133)}
OUTER = dict(south=35.03, north=35.75, west=139.43, east=140.20)
INNER = dict(south=35.195, north=35.345, west=139.625, east=139.815)

_gttm = None
def gttm():
    global _gttm
    if _gttm is None:
        raw = np.load(ROOT + '/data/gttm-tokyo.npz')
        _gttm = RegularGridInterpolator((raw['lat'], raw['lon']), raw['depth'])
    return _gttm

def grid(b, dx, min_depth):
    dlat = dx / 111195; dlon = dx / (111195 * math.cos(math.radians(LAT_REF)))
    lat = b['south'] + np.arange(int((b['north'] - b['south']) / dlat) + 1) * dlat
    lon = b['west'] + np.arange(int((b['east'] - b['west']) / dlon) + 1) * dlon
    yy, xx = np.meshgrid(lat, lon, indexing='ij')
    depth = gttm()(np.column_stack([yy.ravel(), xx.ravel()])).reshape(yy.shape)
    sea = depth > 0
    wet = depth >= min_depth
    labs, _ = label(wet)
    ids = set(labs[0]) | set(labs[-1]) | set(labs[:, 0]) | set(labs[:, -1]); ids.discard(0)
    wet = np.isin(labs, list(ids))
    H = np.where(wet, depth, 0.)
    return dict(lat=lat, lon=lon, dx=dx, H=H, wet=wet, sea=sea, dlat=dlat, dlon=dlon)

def station_constants(names=FORCING_NAMES):
    out = {}
    for st in STATIONS:
        th, y = tl.read_jma(f'{ROOT}/data/jma/{st}-2026.txt')
        mean, amp, ph, res = tl.fit(th, y, FIT_NAMES, utc=True)
        idx = [FIT_NAMES.index(n) for n in names]
        out[st] = amp[idx] * np.exp(1j * np.radians(ph[idx]))
    return out

def boundary_constants(g, consts):
    """Complex constants for each open-edge wet cell, by inverse-distance weighting."""
    m = ShallowWater.__new__(ShallowWater)
    wet = g['wet']; edge = np.zeros_like(wet)
    edge[0] = wet[0]; edge[-1] = wet[-1]; edge[:, 0] = wet[:, 0]; edge[:, -1] = wet[:, -1]
    ys, xs = np.nonzero(edge)
    la = g['lat'][ys]; lo = g['lon'][xs]
    w = []
    for st, (sla, slo) in STATIONS.items():
        d = np.hypot((la - sla) * 111.2, (lo - slo) * 111.2 * math.cos(math.radians(LAT_REF)))
        w.append(1 / np.maximum(d, 1) ** 2)
    w = np.array(w); w /= w.sum(0)
    C = sum(w[i][:, None] * consts[st][None, :] for i, st in enumerate(STATIONS))
    return edge, C

def synth(C, t_hours, names=FORCING_NAMES):
    F, VU = tl.args(names, [t_hours], utc=True)
    return (np.abs(C) * F[0] * np.cos(np.radians(VU[0]) - np.angle(C))).sum(-1)

class Nest:
    """Bilinear sampling of outer eta at inner open-edge cells (nearest wet fallback)."""
    def __init__(self, outer, inner):
        wet = inner['wet']; edge = np.zeros_like(wet)
        edge[0] = wet[0]; edge[-1] = wet[-1]; edge[:, 0] = wet[:, 0]; edge[:, -1] = wet[:, -1]
        self.edge = edge
        ys, xs = np.nonzero(edge)
        fy = (inner['lat'][ys] - outer['lat'][0]) / outer['dlat']
        fx = (inner['lon'][xs] - outer['lon'][0]) / outer['dlon']
        _, near = distance_transform_edt(~outer['wet'], return_indices=True)
        self.taps = []
        y0 = np.floor(fy).astype(int); x0 = np.floor(fx).astype(int); ty = fy - y0; tx = fx - x0
        for dy, dx, w in [(0, 0, (1 - ty) * (1 - tx)), (0, 1, (1 - ty) * tx), (1, 0, ty * (1 - tx)), (1, 1, ty * tx)]:
            yy = y0 + dy; xx = x0 + dx
            ny = near[0][yy, xx]; nx = near[1][yy, xx]
            self.taps.append((ny, nx, w))
    def __call__(self, eta_outer):
        return sum(w * eta_outer[y, x] for y, x, w in self.taps)

def run(args):
    t0 = time.time()
    outer = grid(OUTER, args.outer_dx, 3.0)
    INNER_B = dict(zip(['south','north','west','east'], map(float, args.inner_bounds.split(',')))) if args.inner_bounds else INNER
    inner = grid(INNER_B, args.inner_dx, args.inner_min_depth) if not args.outer_only else grid(dict(south=35.20,north=35.30,west=139.70,east=139.80), 500, 1)
    print('outer', outer['H'].shape, int(outer['wet'].sum()), 'inner', inner['H'].shape, int(inner['wet'].sum()), flush=True)
    consts = station_constants()
    oedge, OC = boundary_constants(outer, consts)
    mo = ShallowWater(outer['H'], args.outer_dx, dt=args.dt, viscosity=args.outer_nu, drag=args.drag)
    sub = int(round(args.dt / args.inner_dt))
    mi = ShallowWater(inner['H'], args.inner_dx, dt=args.dt / sub, viscosity=args.inner_nu, drag=args.drag)
    nest = Nest(outer, inner)
    print('factorised', round(time.time() - t0, 1), 's', flush=True)
    start = datetime.datetime.fromisoformat(args.start) - datetime.timedelta(hours=9)  # JST -> UTC
    h0 = tl.hours(start) - args.spinup
    total = int((args.spinup + args.days * 24) * 3600 / args.dt)
    rec_every = int(round(3600 * args.record_hours / args.dt))
    oids = np.flatnonzero(outer['wet']); iids = np.flatnonzero(inner['wet'])
    nrec = int(args.days * 24 / args.record_hours) + 1
    if args.bench: total = args.bench; nrec = 0
    OU = np.zeros((nrec, 2, len(oids)), np.float32); IU = np.zeros((nrec, 2, len(iids)), np.float32)
    OE = np.zeros((nrec, len(oids)), np.float32); IE = np.zeros((nrec, len(iids)), np.float32)
    times = []
    bo = np.zeros_like(outer['H']); bi = np.zeros_like(inner['H'])
    ramp_h = 12.0
    eta_prev = mo.eta.copy(); k = 0; tcheck = time.time()
    spin_steps = int(args.spinup * 3600 / args.dt)
    for i in range(total + 1):
        th = h0 + i * args.dt / 3600
        if not args.bench and i >= spin_steps and (i - spin_steps) % rec_every == 0 and k < nrec:
            for m, ids, U, E in [(mo, oids, OU, OE), (mi, iids, IU, IE)]:
                uc, vc = m.centers(); U[k, 0] = uc.ravel()[ids]; U[k, 1] = vc.ravel()[ids]; E[k] = m.eta.ravel()[ids]
            times.append(th); k += 1
        if i == total: break
        tn = th + args.dt / 3600
        ramp = min(1.0, (tn - h0) / ramp_h)
        bo[oedge] = ramp * synth(OC, tn)
        eta_prev = mo.eta.copy()
        mo.step(bo)
        for s in range(0 if args.outer_only else sub):
            a = (s + 1) / sub
            bi[nest.edge] = nest((1 - a) * eta_prev + a * mo.eta)
            d = mi.step(bi)
        if i % 1800 == 0 or (args.bench and i % 50 == 0):
            el = time.time() - tcheck
            print(f' step {i}/{total} t={(th-h0):.1f}h max_outer={np.abs(mo.u).max():.2f}m/s elapsed {el:.0f}s', flush=True)
    print('run seconds', round(time.time() - t0, 1), flush=True)
    if args.bench: return
    out = args.out
    np.savez_compressed(out, times=np.array(times), OU=OU[:k], OE=OE[:k], IU=IU[:k], IE=IE[:k],
        oids=oids, iids=iids, oshape=outer['H'].shape, ishape=inner['H'].shape,
        olat=outer['lat'], olon=outer['lon'], ilat=inner['lat'], ilon=inner['lon'],
        oH=outer['H'], iH=inner['H'], osea=outer['sea'], isea=inner['sea'],
        meta=json.dumps(vars(args)))
    print('saved', out, flush=True)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outer-dx', type=float, default=250)
    p.add_argument('--inner-dx', type=float, default=50)
    p.add_argument('--inner-min-depth', type=float, default=2.0)
    p.add_argument('--dt', type=float, default=20)
    p.add_argument('--inner-dt', type=float, default=10)
    p.add_argument('--outer-nu', type=float, default=5)
    p.add_argument('--inner-nu', type=float, default=1)
    p.add_argument('--drag', type=float, default=.0025)
    p.add_argument('--start', default='2026-10-01T00:00')
    p.add_argument('--days', type=float, default=30)
    p.add_argument('--spinup', type=float, default=48)
    p.add_argument('--record-hours', type=float, default=1)
    p.add_argument('--inner-bounds', default='', help='south,north,west,east')
    p.add_argument('--outer-only', action='store_true')
    p.add_argument('--bench', type=int, default=0)
    p.add_argument('--out', default='/tmp/nested-run.npz')
    run(p.parse_args())
