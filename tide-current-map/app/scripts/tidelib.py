"""Small harmonic tide library (astronomical arguments, nodal factors, least squares).

Phases are local-time phase lags referenced to JST (UTC+9), the convention used in
Japanese tide tables, unless `utc=True` is passed. Nodal factors follow the classic
Schureman approximations. Good enough for tidal current synthesis, not a geodetic tool.
"""
import math, datetime
import numpy as np

# name: (Doodson tau,s,h,p,N',p1), phase offset in degrees, nodal family
CONST = {
 'Sa':  ((0,0,1,0,0,0),0,'one'),  'Ssa': ((0,0,2,0,0,0),0,'one'),
 'Mm':  ((0,1,0,-1,0,0),0,'Mm'),  'MSf': ((0,2,-2,0,0,0),0,'M2'),
 'Q1':  ((1,-2,0,1,0,0),90,'O1'),'O1':  ((1,-1,0,0,0,0),90,'O1'),
 'M1':  ((1,0,0,1,0,0),-90,'J1'),  'P1':  ((1,1,-2,0,0,0),90,'one'),
 'K1':  ((1,1,0,0,0,0),-90,'K1'),  'J1':  ((1,2,0,-1,0,0),-90,'J1'),
 'OO1': ((1,3,0,0,0,0),-90,'OO1'), '2N2': ((2,-2,0,2,0,0),0,'M2'),
 'MU2': ((2,-2,2,0,0,0),0,'M2'),  'N2':  ((2,-1,0,1,0,0),0,'M2'),
 'NU2': ((2,-1,2,-1,0,0),0,'M2'), 'M2':  ((2,0,0,0,0,0),0,'M2'),
 'L2':  ((2,1,0,-1,0,0),180,'M2'),'T2':  ((2,2,-3,0,0,1),0,'one'),
 'S2':  ((2,2,-2,0,0,0),0,'one'), 'K2':  ((2,2,0,0,0,0),0,'K2'),
 'M3':  ((3,0,0,0,0,0),180,'M3'), 'MK3': ((3,1,0,0,0,0),-90,'MK3'),
 'MN4': ((4,-1,0,1,0,0),0,'M4'),  'M4':  ((4,0,0,0,0,0),0,'M4'),
 'MS4': ((4,2,-2,0,0,0),0,'M2'),  'S4':  ((4,4,-4,0,0,0),0,'one'),
 'M6':  ((6,0,0,0,0,0),0,'M6'),   '2MS6':((6,2,-2,0,0,0),0,'M4'),
}
RATES = np.array([14.4920521, 0.5490165, 0.0410686, 0.0046418, 0.0022064, 0.0000020])  # deg/hour

def jma_kappa(g, name, lon):
    """Convert a Greenwich (UTC) phase lag to the JMA local-epoch kappa."""
    return (g + CONST[name][0][0] * lon) % 360

def speed(name):
    return float(np.dot(CONST[name][0], RATES))

def _astro(t):
    """t: datetime (UTC, naive) or array of hours since 2000-01-01 12:00 UTC."""
    T = np.asarray(t, float) / (24 * 36525.)
    s = 218.3164477 + 481267.88123421 * T
    h = 280.46646 + 36000.76983 * T
    p = 83.3532465 + 4069.0137287 * T
    N = 125.04452 - 1934.136261 * T
    p1 = 282.93735 + 1.71946 * T
    ut = (np.asarray(t, float) + 12.0) % 24.0  # hours UT of day (epoch is 12:00)
    tau = 15 * ut + 180 + h - s
    return tau, s, h, p, N, p1

EPOCH = datetime.datetime(2000, 1, 1, 12)

def hours(dt_utc):
    return (dt_utc - EPOCH).total_seconds() / 3600.

def nodal(family, N):
    n = np.radians(N); c = np.cos; s = np.sin
    if family == 'one': return np.ones_like(n), np.zeros_like(n)
    if family == 'M2': return 1.0004 - .0373 * c(n) + .0002 * c(2 * n), -2.14 * s(n)
    if family == 'O1': return 1.0089 + .1871 * c(n) - .0147 * c(2 * n) + .0014 * c(3 * n), 10.8 * s(n) - 1.34 * s(2 * n) + .19 * s(3 * n)
    if family == 'K1': return 1.0060 + .1150 * c(n) - .0088 * c(2 * n) + .0006 * c(3 * n), -8.86 * s(n) + .68 * s(2 * n) - .07 * s(3 * n)
    if family == 'K2': return 1.0241 + .2863 * c(n) + .0083 * c(2 * n) - .0015 * c(3 * n), -17.74 * s(n) + .68 * s(2 * n) - .04 * s(3 * n)
    if family == 'J1': return 1.0129 + .1676 * c(n) - .0170 * c(2 * n) + .0016 * c(3 * n), -12.94 * s(n) + 1.34 * s(2 * n) - .19 * s(3 * n)
    if family == 'OO1': return 1.1027 + .6504 * c(n) + .0317 * c(2 * n) - .0014 * c(3 * n), -36.68 * s(n) + 4.02 * s(2 * n) - .57 * s(3 * n)
    if family == 'Mm': return 1.0 - .1300 * c(n) + .0013 * c(2 * n), np.zeros_like(n)
    fm, um = nodal('M2', N)
    if family == 'M4': return fm ** 2, 2 * um
    if family == 'M6': return fm ** 3, 3 * um
    if family == 'M3': return fm ** 1.5, 1.5 * um
    if family == 'MK3':
        fk, uk = nodal('K1', N); return fm * fk, um + uk
    raise KeyError(family)

def args(names, t_hours, utc=False):
    """Return f (n_t, n_c) and V+u in degrees (n_t, n_c) at hours since EPOCH (UTC).

    With utc=False the phase is shifted so fitted phase lags match the JST
    (135E) convention used by JMA.
    """
    t = np.atleast_1d(np.asarray(t_hours, float))
    tau, s, h, p, N, p1 = _astro(t)
    A = np.stack([tau, s, h, p, -N, p1], -1)
    F = np.empty((len(t), len(names))); VU = np.empty_like(F)
    for j, nm in enumerate(names):
        d, off, fam = CONST[nm]
        V = A @ np.array(d, float) + off
        if not utc:
            V = V + 9 * speed(nm)  # local (JST) clock convention
        f, u = nodal(fam, N)
        F[:, j] = f; VU[:, j] = V + u
    return F, VU

def fit(t_hours, y, names, utc=False):
    """Least squares. y may be (n_t,) or (n_t, n_series). Returns mean, amp, phase(deg)."""
    F, VU = args(names, t_hours, utc)
    r = np.radians(VU)
    X = np.concatenate([np.ones((len(t_hours), 1)), F * np.cos(r), F * np.sin(r)], 1)
    y2 = y if y.ndim == 2 else y[:, None]
    coef, *_ = np.linalg.lstsq(X, y2, rcond=None)
    n = len(names); a = coef[1:1 + n]; b = coef[1 + n:]
    amp = np.hypot(a, b); ph = np.degrees(np.arctan2(b, a)) % 360
    resid = y2 - X @ coef
    out = (coef[0], amp, ph, resid)
    return tuple(o[..., 0] if y.ndim == 1 else o for o in out) if y.ndim == 1 else out

def predict(t_hours, mean, amp, ph, names, utc=False):
    F, VU = args(names, t_hours, utc)
    amp = np.asarray(amp); ph = np.asarray(ph)
    return mean + (F * amp[..., :] * np.cos(np.radians(VU - ph))).sum(-1)

def read_jma(path):
    """JMA hourly astronomical tide text (cm, JST). Returns hours-since-EPOCH (UTC) and metres."""
    t = []; v = []
    for line in open(path):
        if len(line) < 80: continue
        try:
            d = datetime.datetime(2000 + int(line[72:74]), int(line[74:76]), int(line[76:78]))
            vals = [int(line[i:i + 3]) for i in range(0, 72, 3)]
        except ValueError:
            continue
        for i, x in enumerate(vals):
            if x == 999: continue
            t.append(hours(d + datetime.timedelta(hours=i - 9))); v.append(x / 100)
    return np.array(t), np.array(v)
