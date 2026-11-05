"""Extract earth-referenced currents from the PARI Tokyo Bay ferry ADCP (Kurihama-Kanaya).

Source: 港湾空港技術研究所 UMI-POCHI (https://pari.mpat.go.jp/bdhome/) – raw, not
quality controlled by the provider. Processed here (ship velocity removed etc.).

current = water velocity relative to ADCP (Ser*) + ship velocity over ground
(bottom track; GPS when bottom track is missing). Returns bin-1 (about 11 m deep)
and a column mean of good bins down to 85% of the bottom depth.
Usage: python ferry-extract.py data2023.zip out.npz
"""
import sys, io, zipfile, datetime, tempfile, os
import numpy as np, scipy.io as sio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tidelib as tl

VARS = ['SerYear','SerMon','SerDay','SerHour','SerMin','SerSec','AnFLatDeg','AnFLonDeg','AnLLatDeg','AnLLonDeg',
        'SerEmmpersec','SerNmmpersec','SerPG4','AnNVEmmpersec','AnNVNmmpersec','AnBTEmmpersec','AnBTNmmpersec',
        'AnBTDepthcmB1','AnBTDepthcmB2','AnBTDepthcmB3','AnBTDepthcmB4']
BIN1, BINSZ, DRAFT = 7.21, 4.0, 3.5
BAD = -32768

def process(d):
    n = d['SerYear'].shape[0]
    t = np.array([tl.hours(datetime.datetime(2000 + int(y), int(m), int(dd), int(h), int(mi), int(s)) - datetime.timedelta(hours=9))
                  for y, m, dd, h, mi, s in zip(*[d[k].ravel() for k in VARS[:6]])])
    lat = (d['AnFLatDeg'].ravel() + d['AnLLatDeg'].ravel()) / 2
    lon = (d['AnFLonDeg'].ravel() + d['AnLLonDeg'].ravel()) / 2
    nvE = d['AnNVEmmpersec'].ravel().astype(float); nvN = d['AnNVNmmpersec'].ravel().astype(float)
    btE = d['AnBTEmmpersec'].ravel().astype(float); btN = d['AnBTNmmpersec'].ravel().astype(float)
    bt_ok = (btE != BAD) & (btN != BAD)
    shipE = np.where(bt_ok, btE, nvE); shipN = np.where(bt_ok, btN, nvN)
    depths = np.stack([d[f'AnBTDepthcmB{i}'].ravel().astype(float) for i in range(1, 5)], 1)
    depths[depths <= 0] = np.nan
    depth = np.nanmean(depths, 1) / 100 + DRAFT
    E = d['SerEmmpersec'].astype(float); N = d['SerNmmpersec'].astype(float); pg = d['SerPG4']
    good = (E != BAD) & (N != BAD) & (pg >= 80)
    zb = DRAFT + BIN1 + BINSZ * np.arange(E.shape[1])
    keep_bins = good & (zb[None, :] < 0.85 * depth[:, None])
    cE = E + shipE[:, None]; cN = N + shipN[:, None]
    with np.errstate(invalid='ignore'):
        mE = np.where(keep_bins, cE, 0).sum(1) / keep_bins.sum(1)
        mN = np.where(keep_bins, cN, 0).sum(1) / keep_bins.sum(1)
    b1 = good[:, 0]
    speed = np.hypot(nvE, nvN)
    ok = (speed > 2000) & bt_ok & np.isfinite(depth) & (keep_bins.sum(1) >= 2) & b1 & (nvE != BAD)
    return dict(t=t[ok], lat=lat[ok], lon=lon[ok], depth=depth[ok], nbins=keep_bins.sum(1)[ok],
                u1=cE[ok, 0] / 1000, v1=cN[ok, 0] / 1000, um=mE[ok] / 1000, vm=mN[ok] / 1000,
                btnv=np.hypot(btE - nvE, btN - nvN)[ok] / 1000)

def main(zpath, out):
    z = zipfile.ZipFile(zpath); parts = []
    for name in sorted(z.namelist()):
        if not name.endswith('.mat'): continue
        with tempfile.NamedTemporaryFile(suffix='.mat') as tmp:
            tmp.write(z.read(name)); tmp.flush()
            d = sio.loadmat(tmp.name, variable_names=VARS)
        r = process(d); parts.append(r)
        print(name, len(r['t']), flush=True)
    res = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    o = np.argsort(res['t']); res = {k: v[o] for k, v in res.items()}
    np.savez_compressed(out, **res)
    print('saved', out, len(res['t']))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
