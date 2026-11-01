"""Validate harmonic model currents against
 (1) PARI ferry ADCP 2023 (Kurihama-Kanaya, measured; tidal + non-tidal), and
 (2) Japan Coast Guard official tidal current predictions (speed only, 41 points).

Usage: python validate-currents.py harmonic_dir ferry2023.npz ferry-harmonics.json jcg_html_dir out.json
"""
import sys, os, json, math, glob, re, datetime
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tidelib as tl

KT = 1.94384

class Grid:
    def __init__(self, d, name):
        self.m = json.load(open(f'{d}/{name}.json'))
        n = len(self.m['constituents'])
        self.c = np.fromfile(f'{d}/{name}.bin', '<i2').astype(float).reshape(len(self.m['wetIds']), 2 + 4 * n) / 1000
        self.index = {w: i for i, w in enumerate(self.m['wetIds'])}
    def cell(self, lat, lon):
        m = self.m
        iy = int(round((lat - m['lat0']) / m['dlat'])); ix = int(round((lon - m['lon0']) / m['dlon']))
        if not (0 <= iy < m['ny'] and 0 <= ix < m['nx']): return None
        return self.index.get(iy * m['nx'] + ix)
    def predict(self, i, t_hours):
        names = self.m['constituents']
        F, VU = tl.args(names, np.atleast_1d(t_hours), utc=True); R = np.radians(VU)
        c = self.c[i]; u = c[0] + 0 * F[:, 0]; v = c[1] + 0 * F[:, 0]
        for j in range(len(names)):
            k = 2 + 4 * j
            u = u + F[:, j] * (c[k] * np.cos(R[:, j]) + c[k + 1] * np.sin(R[:, j]))
            v = v + F[:, j] * (c[k + 2] * np.cos(R[:, j]) + c[k + 3] * np.sin(R[:, j]))
        return u, v

def pick(grids, lat, lon):
    for g in grids:
        i = g.cell(lat, lon)
        if i is not None: return g, i
    return None, None

def ferry(grids, npz, harm):
    d = np.load(npz); H = json.load(open(harm)); rows = []
    for s in H['segments']:
        g, i = pick(grids, s['lat'], s['lon'])
        if g is None: continue
        # samples near this segment centre
        near = (np.abs(d['lat'] - s['lat']) * 111.2 < 0.35) & (np.abs(d['lon'] - s['lon']) * 91 < 0.35)
        t = d['t'][near]; uo = d['um'][near]; vo = d['vm'][near]
        ok = np.isfinite(uo) & np.isfinite(vo) & (np.abs(uo) < 3) & (np.abs(vo) < 3)
        t, uo, vo = t[ok], uo[ok], vo[ok]
        if len(t) < 500: continue
        um, vm = g.predict(i, t)
        # observed tidal part from the observation's own harmonic fit (lunar + main solar)
        names = ['Q1', 'O1', 'K1', 'N2', 'M2', 'S2', 'K2', 'M4', 'MS4']
        _, a, p, res = tl.fit(t, np.column_stack([uo, vo]), names, utc=True)
        obs_tide = np.column_stack([uo, vo]) - res
        err_total = np.sqrt(((uo - um) ** 2 + (vo - vm) ** 2).mean())
        err_tide = np.sqrt(((obs_tide[:, 0] - obs_tide[:, 0].mean() - (um - um.mean())) ** 2 + (obs_tide[:, 1] - obs_tide[:, 1].mean() - (vm - vm.mean())) ** 2).mean())
        var_obs = ((uo - uo.mean()) ** 2 + (vo - vo.mean()) ** 2).mean()
        var_err = ((uo - um - (uo - um).mean()) ** 2 + (vo - vm - (vo - vm).mean()) ** 2).mean()
        # model M2 ellipse at this cell
        n = g.m['constituents']; k = 2 + 4 * n.index('M2'); c = g.c[i]
        cu = c[k] + 1j * c[k + 1]; cv = c[k + 2] + 1j * c[k + 3]
        wp = (np.conj(cu) + 1j * np.conj(cv)) / 2; wm = (cu + 1j * cv) / 2
        mod_major = abs(wp) + abs(wm); mod_inc = math.degrees((np.angle(wp) + np.angle(wm)) / 2) % 180
        oe = s['column']['M2ellipse']
        # phase of maximum flow along the observed major axis (time of max, minutes difference)
        ang = math.radians(oe['incDeg'])
        def along_phase(au, pu, av, pv):
            z = au * np.exp(1j * np.radians(pu)) * math.cos(ang) + av * np.exp(1j * np.radians(pv)) * math.sin(ang)
            return abs(z), math.degrees(np.angle(z))
        j = names.index('M2')
        oa, op = along_phase(a[j, 0], p[j, 0], a[j, 1], p[j, 1])
        mz = (c[k] - 1j * c[k + 1]) * math.cos(ang) + (c[k + 2] - 1j * c[k + 3]) * math.sin(ang)
        ma, mp = abs(mz), -math.degrees(np.angle(mz))
        dphase = ((mp - op + 180) % 360 - 180) / tl.speed('M2') * 60
        rows.append({'km': s['km'], 'lat': s['lat'], 'lon': s['lon'], 'grid': g.m['name'], 'n': int(len(t)),
                     'obsM2AlongMps': round(oa, 3), 'modelM2AlongMps': round(ma, 3), 'M2PhaseDiffMin': round(dphase, 1),
                     'obsM2IncDeg': round(oe['incDeg'], 1), 'modelM2IncDeg': round(mod_inc, 1),
                     'rmsErrorAllMps': round(float(err_total), 3), 'rmsErrorVsObservedTideMps': round(float(err_tide), 3),
                     'explainedVariance': round(float(1 - var_err / var_obs), 3), 'obsStdMps': round(float(math.sqrt(var_obs)), 3)})
        r = rows[-1]
        print(f"ferry km{r['km']:4.1f} M2 along obs {r['obsM2AlongMps']:.2f} model {r['modelM2AlongMps']:.2f} m/s, phase {r['M2PhaseDiffMin']:+.0f} min, inc {r['obsM2IncDeg']:.0f}/{r['modelM2IncDeg']:.0f}; rms err vs tide {r['rmsErrorVsObservedTideMps']:.2f}, vs all {r['rmsErrorAllMps']:.2f}, expl.var {r['explainedVariance']:.2f}")
    return rows

def official(grids, folder):
    pts = []
    for f in sorted(glob.glob(f'{folder}/*.html')):
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})-(\d{1,2})\.html', f)
        if not m: continue
        y, mo, d, h = map(int, m.groups())
        html = open(f, encoding='utf-8', errors='replace').read()
        st = [(int(a), int(b), float(c)) for a, b, c in re.findall(r'coords\s*=\s*["\']?(\d+),(\d+),\d+\s+ALT=["\']([\d.]+)kn\.', html, re.I)]
        th = tl.hours(datetime.datetime(y, mo, d, h) - datetime.timedelta(hours=9))
        for x, yy, kn in st:
            lat = 35 + (631 - yy) / 840; lon = 139.5 + (x - 30) / 675
            g, i = pick(grids, lat, lon)
            if g is None: continue
            u, v = g.predict(i, th)
            pts.append({'lat': round(lat, 4), 'lon': round(lon, 4), 'time': f'{y}-{mo:02d}-{d:02d}T{h:02d}', 'officialKt': kn, 'modelKt': round(float(math.hypot(u[0], v[0]) * KT), 2), 'grid': g.m['name']})
    if not pts: return {}
    o = np.array([p['officialKt'] for p in pts]); md = np.array([p['modelKt'] for p in pts])
    by = {}
    for p in pts: by.setdefault((p['lat'], p['lon']), []).append(p)
    stations = []
    for (la, lo), ps in by.items():
        a = np.array([q['officialKt'] for q in ps]); b = np.array([q['modelKt'] for q in ps])
        stations.append({'lat': la, 'lon': lo, 'n': len(ps), 'officialMeanKt': round(float(a.mean()), 2), 'modelMeanKt': round(float(b.mean()), 2),
                         'corr': round(float(np.corrcoef(a, b)[0, 1]), 2) if a.std() > 0 and b.std() > 0 else None, 'grid': ps[0]['grid']})
    summary = {'n': len(pts), 'meanOfficialKt': round(float(o.mean()), 3), 'meanModelKt': round(float(md.mean()), 3),
               'rmsDiffKt': round(float(np.sqrt(((o - md) ** 2).mean())), 3), 'corr': round(float(np.corrcoef(o, md)[0, 1]), 3), 'stations': stations}
    print('official n', summary['n'], 'mean official', summary['meanOfficialKt'], 'model', summary['meanModelKt'], 'rms', summary['rmsDiffKt'], 'corr', summary['corr'])
    return summary

if __name__ == '__main__':
    hd, npz, harm, jcg, out = sys.argv[1:6]
    grids = [Grid(hd, n) for n in ['harmonic-inner', 'harmonic-outer'] if os.path.exists(f'{hd}/{n}.json')]
    res = {'ferry': ferry(grids, npz, harm), 'official': official(grids, jcg)}
    json.dump(res, open(out, 'w'), ensure_ascii=False, indent=1)
