"""Harmonic analysis of nested-model currents, exported for in-browser synthesis.

Usage: python harmonic-export.py run.npz outdir [--grids inner,outer]

For each wet cell, fits mean + constituents to hourly u, v. P1 and K2 cannot be
separated from K1 and S2 in a ~30 day record, so they are inferred from the
boundary forcing ratios (amplitude ratio and phase difference at Aburatsubo).

Output per grid: <name>.json (metadata) and <name>.bin:
  int16 little endian, per wet cell (in wetIds order): mean_u, mean_v, then per
  constituent: u_a, u_b, v_a, v_b where component(t) = sum f*(a cos(V+u) + b sin(V+u)),
  V+u from the UTC Greenwich convention (see tidelib.py / harmonic.js). Unit 1 mm/s.
"""
import sys, os, json, math, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tidelib as tl
from nested_model import station_constants, FORCING_NAMES

FIT = ['Q1', 'O1', 'K1', 'N2', 'M2', 'S2', 'M4', 'MS4', 'MN4', 'M6']
TIED = {'P1': 'K1', 'K2': 'S2'}
OUT = ['Q1', 'O1', 'P1', 'K1', 'N2', 'M2', 'S2', 'K2', 'M4', 'MS4', 'MN4', 'M6']

def inference():
    c = station_constants()['Z1']
    r = {}
    for minor, major in TIED.items():
        a = c[FORCING_NAMES.index(minor)]; b = c[FORCING_NAMES.index(major)]
        r[minor] = (abs(a) / abs(b), np.angle(a) - np.angle(b))
    return r

def design(t, inf):
    F, VU = tl.args(OUT, t, utc=True); R = np.radians(VU)
    cols = []
    for n in FIT:
        j = OUT.index(n)
        c = F[:, j] * np.cos(R[:, j]); s = F[:, j] * np.sin(R[:, j])
        for minor, major in TIED.items():
            if major == n:
                k = OUT.index(minor); ratio, dph = inf[minor]
                c = c + ratio * F[:, k] * np.cos(R[:, k] - dph); s = s + ratio * F[:, k] * np.sin(R[:, k] - dph)
        cols += [c, s]
    return np.column_stack([np.ones(len(t))] + cols)

def analyse(t, U, inf):
    """U: (nt, 2, ncell). Returns mean (2,n), coefficients (len(OUT), 2 comps, 2 (a,b), n), residual rms (n)."""
    X = design(t, inf)
    nt, _, n = U.shape
    Y = U.reshape(nt, 2 * n).astype(np.float64)
    coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
    resid = Y - X @ coef
    rms = np.sqrt((resid.reshape(nt, 2, n) ** 2).sum(1).mean(0))
    coef = coef.reshape(-1, 2, n)
    mean = coef[0]
    out = np.zeros((len(OUT), 2, 2, n))
    for i, nm in enumerate(FIT):
        a = coef[1 + 2 * i]; b = coef[2 + 2 * i]
        out[OUT.index(nm), :, 0] = a; out[OUT.index(nm), :, 1] = b
    for minor, major in TIED.items():
        ratio, dph = inf[minor]
        a = out[OUT.index(major), :, 0]; b = out[OUT.index(major), :, 1]
        # amplitude*ratio, phase + dph
        out[OUT.index(minor), :, 0] = ratio * (a * math.cos(dph) - b * math.sin(dph))
        out[OUT.index(minor), :, 1] = ratio * (a * math.sin(dph) + b * math.cos(dph))
    return mean, out, rms

def export(r, prefix, outdir, name, label):
    p = prefix.lower()
    t = r['times']; U = r[prefix + 'U']; ids = r[p + 'ids']
    shape = tuple(int(x) for x in r[p + 'shape'])
    lat = r[p + 'lat']; lon = r[p + 'lon']; H = r[p + 'H']
    inf = inference()
    mean, coef, rms = analyse(t, U, inf)
    q = lambda x: np.clip(np.round(x * 1000), -32767, 32767).astype('<i2')
    n = len(ids)
    block = np.zeros((n, 2 + 4 * len(OUT)), '<i2')
    block[:, 0] = q(mean[0]); block[:, 1] = q(mean[1])
    for i in range(len(OUT)):
        block[:, 2 + 4 * i] = q(coef[i, 0, 0]); block[:, 3 + 4 * i] = q(coef[i, 0, 1])
        block[:, 4 + 4 * i] = q(coef[i, 1, 0]); block[:, 5 + 4 * i] = q(coef[i, 1, 1])
    block.tofile(f'{outdir}/{name}.bin')
    m2 = np.hypot(np.hypot(coef[OUT.index('M2'), 0, 0], coef[OUT.index('M2'), 0, 1]), np.hypot(coef[OUT.index('M2'), 1, 0], coef[OUT.index('M2'), 1, 1]))
    meta = {'version': 1, 'name': name, 'label': label, 'nx': shape[1], 'ny': shape[0],
            'lat0': float(lat[0]), 'lon0': float(lon[0]), 'dlat': float(lat[1] - lat[0]), 'dlon': float(lon[1] - lon[0]),
            'dxM': float(json.loads(str(r['meta']))[prefix == 'I' and 'inner_dx' or 'outer_dx']),
            'constituents': OUT, 'speedsDegPerHour': [tl.speed(c) for c in OUT],
            'doodson': [list(tl.CONST[c][0]) for c in OUT], 'phaseOffsetDeg': [tl.CONST[c][1] for c in OUT],
            'nodal': [tl.CONST[c][2] for c in OUT], 'unit': 'mm/s', 'layout': 'mean_u,mean_v,(u_a,u_b,v_a,v_b)*constituents',
            'convention': 'UTC Greenwich; component = mean + sum f*(a*cos(V+u) + b*sin(V+u))',
            'wetIds': ids.tolist(), 'depth': np.round(H.ravel()[ids], 1).tolist(),
            'fitResidualRmsMps': {'median': float(np.median(rms)), 'p95': float(np.percentile(rms, 95))},
            'inference': {k: {'ratio': float(v[0]), 'phaseDiffDeg': float(np.degrees(v[1]))} for k, v in inf.items()},
            'record': {'hours': float(t[-1] - t[0]), 'samples': int(len(t))}, 'run': json.loads(str(r['meta']))}
    json.dump(meta, open(f'{outdir}/{name}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    print(name, 'cells', n, 'bin bytes', block.nbytes, 'M2 max', round(float(m2.max()), 3), 'resid median', round(float(np.median(rms)), 4), 'p95', round(float(np.percentile(rms, 95)), 4))
    return meta, mean, coef

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run'); p.add_argument('outdir'); p.add_argument('--grids', default='inner,outer')
    a = p.parse_args(); r = np.load(a.run); os.makedirs(a.outdir, exist_ok=True)
    if 'outer' in a.grids: export(r, 'O', a.outdir, 'harmonic-outer', '東京湾・浦賀水道（外側モデル）')
    if 'inner' in a.grids and r['IU'].shape[-1] > 100: export(r, 'I', a.outdir, 'harmonic-inner', '横須賀沿岸（内側モデル）')
