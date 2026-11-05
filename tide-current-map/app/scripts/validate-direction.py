"""Compare model current DIRECTION with Japan Coast Guard chart arrows (from jcg-arrows.py).

Usage: python validate-direction.py harmonic_dir arrows.json out.json
Direction is compared only where the official speed is >= 0.2 kn (slack directions are noise)
and the chart arrow does not overlap a same-coloured neighbour (crowded).
"""
import sys, os, json, math, datetime
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tidelib as tl
import importlib
vc = importlib.import_module('validate-currents')

AREAS = {'観音崎北（走水寄り）': (35.2846, 139.7337), '猿島沖': (35.3131, 139.6863), '横須賀沖': (35.3286, 139.6715),
         '第二海堡付近': (35.3286, 139.7545), '中ノ瀬付近': (35.3953, 139.7723), '浦賀水道中央': (35.2846, 139.7752)}

def wrap(d): return (d + 180) % 360 - 180

def main(hd, arrows, out):
    grids = [vc.Grid(hd, n) for n in ['harmonic-inner', 'harmonic-mid', 'harmonic-outer'] if os.path.exists(f'{hd}/{n}.json')]
    rows = json.load(open(arrows))
    recs = []
    for r in rows:
        if r['bearingDeg'] is None or r['speedKn'] < 0.2 or r.get('crowded'): continue
        g, i = vc.pick(grids, r['lat'], r['lon'])
        if g is None: continue
        t = datetime.datetime.fromisoformat(r['time']).astimezone(datetime.timezone.utc).replace(tzinfo=None)
        u, v = g.predict(i, tl.hours(t))
        sp = math.hypot(u[0], v[0]) * vc.KT
        if sp < 0.05: continue
        mb = (math.degrees(math.atan2(u[0], v[0])) + 360) % 360
        recs.append({'lat': r['lat'], 'lon': r['lon'], 'time': r['time'], 'officialKn': r['speedKn'], 'officialDeg': r['bearingDeg'],
                     'modelKt': round(sp, 2), 'modelDeg': round(mb, 1), 'diffDeg': round(wrap(mb - r['bearingDeg']), 1), 'grid': g.m['name']})
    d = np.array([x['diffDeg'] for x in recs])
    summary = {'n': len(recs), 'medianAbsDiffDeg': float(np.median(np.abs(d))), 'within30deg': float((np.abs(d) <= 30).mean()),
               'within45deg': float((np.abs(d) <= 45).mean()), 'meanBiasDeg': float(math.degrees(math.atan2(np.sin(np.radians(d)).mean(), np.cos(np.radians(d)).mean())))}
    by = {}
    for x in recs: by.setdefault((x['lat'], x['lon']), []).append(x['diffDeg'])
    stations = [{'lat': la, 'lon': lo, 'n': len(v), 'medianAbsDiffDeg': float(np.median(np.abs(v))), 'within30deg': float((np.abs(np.array(v)) <= 30).mean()),
                 'biasDeg': float(math.degrees(math.atan2(np.sin(np.radians(v)).mean(), np.cos(np.radians(v)).mean())))} for (la, lo), v in by.items()]
    areas = {}
    for name, (la, lo) in AREAS.items():
        s = min(stations, key=lambda s: math.hypot((s['lat'] - la) * 111, (s['lon'] - lo) * 91))
        areas[name] = s
    print(f"direction: n={summary['n']} median |diff| {summary['medianAbsDiffDeg']:.0f}°, within 30°: {summary['within30deg']*100:.0f}%, within 45°: {summary['within45deg']*100:.0f}%, bias {summary['meanBiasDeg']:+.0f}°")
    for name, s in areas.items():
        print(f"  {name}: n={s['n']} median |diff| {s['medianAbsDiffDeg']:.0f}°, within 30° {s['within30deg']*100:.0f}%, bias {s['biasDeg']:+.0f}°")
    json.dump({'summary': summary, 'areas': areas, 'stations': stations, 'records': recs}, open(out, 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main(*sys.argv[1:])
