"""Harmonic analysis of the ferry ADCP currents in along-track segments.

Usage: python ferry-harmonics.py ferry2023.npz out.json
Segments: 0.5 km along the Kurihama -> Kanaya line, samples within 600 m of it.
The ferry samples only in daytime, so solar constituents (S2, P1) are poorly
determined; lunar ones (M2, N2, O1, K1) are the meaningful comparison.
"""
import sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tidelib as tl

A = (35.2225, 139.7175)  # Kurihama side
B = (35.1700, 139.8200)  # Kanaya side
KX = 111.195 * math.cos(math.radians(35.2)); KY = 111.195
NAMES = ['Q1', 'O1', 'K1', 'N2', 'M2', 'S2', 'K2', 'M4', 'MS4']
SEG_KM = 0.5

def along(lat, lon):
    ax, ay = 0, 0; bx = (B[1] - A[1]) * KX; by = (B[0] - A[0]) * KY
    px = (lon - A[1]) * KX; py = (lat - A[0]) * KY
    L = math.hypot(bx, by); ux, uy = bx / L, by / L
    return px * ux + py * uy, -px * uy + py * ux, L

def ellipse(cu, cv):
    """cu, cv complex amplitudes (amp*exp(i*phase)) -> semi-major, semi-minor, inclination(deg from east), phase."""
    wp = (cu + 1j * cv) / 2; wm = np.conj(cu - 1j * cv) / 2  # standard rotary decomposition
    ap, am = abs(wp), abs(wm)
    thp, thm = np.angle(wp), np.angle(wm)
    smaj = ap + am; smin = ap - am
    inc = np.degrees((thp + thm) / 2) % 180
    pha = np.degrees((thm - thp) / 2) % 360
    return smaj, smin, inc, pha

def main(path, out):
    d = np.load(path)
    s, c, L = along(d['lat'], d['lon'])
    keep = (np.abs(c) < 0.6) & (s > 0.2) & (s < L - 0.2)
    segs = []
    for k in range(int(L / SEG_KM) + 1):
        m = keep & (s >= k * SEG_KM) & (s < (k + 1) * SEG_KM)
        if m.sum() < 2000: continue
        t = d['t'][m]
        res = {'km': (k + .5) * SEG_KM, 'n': int(m.sum()), 'lat': float(d['lat'][m].mean()), 'lon': float(d['lon'][m].mean()),
               'depth': float(np.median(d['depth'][m]))}
        for lay, (uk, vk) in {'surface11m': ('u1', 'v1'), 'column': ('um', 'vm')}.items():
            Y = np.column_stack([d[uk][m], d[vk][m]])
            ok = np.all(np.isfinite(Y), 1) & (np.abs(Y) < 3).all(1)
            mean, amp, ph, resid = tl.fit(t[ok], Y[ok], NAMES, utc=True)
            cu = amp[:, 0] * np.exp(1j * np.radians(ph[:, 0])); cv = amp[:, 1] * np.exp(1j * np.radians(ph[:, 1]))
            res[lay] = {'mean': [float(mean[0]), float(mean[1])], 'residualRms': float(np.sqrt((resid ** 2).sum(1).mean())),
                        'totalRms': float(np.sqrt(((Y[ok] - Y[ok].mean(0)) ** 2).sum(1).mean())),
                        'const': {n: {'u': [float(amp[i, 0]), float(ph[i, 0])], 'v': [float(amp[i, 1]), float(ph[i, 1])]} for i, n in enumerate(NAMES)}}
            smaj, smin, inc, pha = ellipse(cu[NAMES.index('M2')], cv[NAMES.index('M2')])
            res[lay]['M2ellipse'] = {'major': float(smaj), 'minor': float(smin), 'incDeg': float(inc), 'phaseDeg': float(pha)}
        segs.append(res)
        e = res['column']['M2ellipse']; e1 = res['surface11m']['M2ellipse']
        print(f"km {res['km']:4.1f} n={res['n']:6d} depth {res['depth']:5.1f}m  M2 col {e['major']:.2f}m/s inc {e['incDeg']:5.1f}  11m {e1['major']:.2f}  resid {res['column']['residualRms']:.2f}/{res['column']['totalRms']:.2f}")
    json.dump({'source': '港湾空港技術研究所 UMI-POCHI（https://pari.mpat.go.jp/bdhome/）を加工して作成', 'line': [A, B], 'names': NAMES, 'segments': segs},
              open(out, 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main(*sys.argv[1:])
