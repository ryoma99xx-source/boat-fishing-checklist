"""Compare modelled water level harmonics with JMA tide stations NOT used as forcing.

Usage: python validate-tide.py run.npz [out.json]
"""
import sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tidelib as tl
from nested_model import FIT_NAMES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = {'QN': ('横須賀', 35.283, 139.650), 'HM': ('本牧', 35.433, 139.667), 'QS': ('横浜', 35.450, 139.650),
         'KW': ('川崎', 35.517, 139.750), 'TK': ('東京', 35.650, 139.767), 'QL': ('千葉', 35.567, 140.050),
         'KZ': ('木更津', 35.367, 139.917), 'TT': ('館山', 34.983, 139.850)}
NAMES = ['O1', 'K1', 'N2', 'M2', 'S2', 'M4']

def nearest(lat, lon, glat, glon, ids, shape, H):
    ny, nx = shape
    yy, xx = np.unravel_index(ids, shape)
    d = np.hypot((glat[yy] - lat) * 111.2, (glon[xx] - lon) * 91.0)
    k = int(np.argmin(d)); return k, float(d[k]), float(H.ravel()[ids[k]])

def main(path, out=None):
    r = np.load(path)
    t = r['times']; E = r['OE']; ids = r['oids']
    fit_names = ['Q1', 'O1', 'P1', 'K1', 'N2', 'M2', 'S2', 'K2', 'M4', 'MS4', 'MN4']
    days = (t[-1] - t[0]) / 24
    if days < 27: fit_names = ['O1', 'K1', 'M2', 'S2', 'M4', 'MS4']
    rows = []
    for code, (name, la, lo) in CHECK.items():
        k, dist, h = nearest(la, lo, r['olat'], r['olon'], ids, tuple(r['oshape']), r['oH'])
        if dist > 3: continue
        _, ma, mp, res = tl.fit(t, E[:, k].astype(float), fit_names, utc=True)
        th, y = tl.read_jma(f'{ROOT}/data/jma/{code}-2026.txt')
        _, oa, op, _ = tl.fit(th, y, FIT_NAMES, utc=True)
        row = {'code': code, 'name': name, 'cellDistanceKm': round(dist, 2)}
        for n in ['O1', 'K1', 'M2', 'S2', 'M4']:
            if n not in fit_names: continue
            i = fit_names.index(n); j = FIT_NAMES.index(n)
            dph = (mp[i] - op[j] + 180) % 360 - 180
            row[n] = {'modelCm': round(ma[i] * 100, 1), 'jmaCm': round(oa[j] * 100, 1), 'phaseDiffDeg': round(float(dph), 1),
                      'phaseDiffMin': round(float(dph / tl.speed(n) * 60), 1)}
        rows.append(row)
        print(f"{name:4s} " + ' '.join(f"{n}:{row[n]['modelCm']:5.1f}/{row[n]['jmaCm']:5.1f}cm {row[n]['phaseDiffMin']:+5.1f}min" for n in ['M2', 'S2', 'K1', 'O1'] if n in row))
    if out: json.dump(rows, open(out, 'w'), ensure_ascii=False, indent=1)
    return rows

if __name__ == '__main__':
    main(*sys.argv[1:])
