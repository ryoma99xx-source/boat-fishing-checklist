"""Read arrow directions from the Japan Coast Guard tidal current chart images.

Usage: python jcg-arrows.py jcg_dir out.json
jcg_dir holds YYYY-MM-DD-H.html (station map with speeds) and img-<name>.png (the chart).
For each station the coloured arrow pixels within a small radius are collected, the
principal axis gives the line, and the arrow head (the wider end) gives the sense.
Output: list of {time, x, y, lat, lon, speedKn, bearingDeg} with the chart's own
pixel->degree mapping plus the datum shift used in the app (+0.0036 lat, -0.0033 lon).
"""
import sys, os, re, glob, json, math
import numpy as np
from PIL import Image

SEA = np.array([204, 255, 255]); LAND = np.array([241, 214, 171])
R = 22

PALETTE = [(153, 153, 153), (106, 90, 205), (0, 0, 255), (0, 64, 0), (255, 0, 0)]  # 0-0.2, 0.2-0.5, 0.5-1, 1-2, 2+ kn

def bucket(kn):
    return 0 if kn < 0.2 else 1 if kn < 0.5 else 2 if kn < 1 else 3 if kn < 2 else 4

def arrow_mask(rgb, kn=None):
    """Pixels within a small tolerance of the arrow colours; with kn, only that speed's colour,
    which separates neighbouring arrows of different speed classes."""
    m = np.zeros(rgb.shape[:2], bool)
    for i, c in enumerate(PALETTE):
        if kn is not None and i != bucket(kn): continue
        m |= (np.abs(rgb.astype(int) - np.array(c)).max(-1) <= 24)
    return m

def direction(mask, x0, y0):
    """The station circle sits at the arrow's midpoint. The principal axis of the arrow touching
    the station gives the line; the head is the end with the wider (triangular) outline."""
    from scipy.ndimage import label
    y1, x1 = max(0, y0 - R), max(0, x0 - R)
    sub = mask[y1:y0 + R + 1, x1:x0 + R + 1]
    labs, n = label(sub)
    if n == 0: return None, 0
    cy, cx = y0 - y1, x0 - x1
    near = labs[max(0, cy - 4):cy + 5, max(0, cx - 4):cx + 5]
    ids = [i for i in np.unique(near) if i]
    if not ids: return None, 0
    pick = max(ids, key=lambda i: (labs == i).sum())
    ys, xs = np.nonzero(labs == pick)
    if len(xs) < 12: return None, len(xs)
    pts = np.column_stack([xs - xs.mean(), ys - ys.mean()]).astype(float)
    w, v = np.linalg.eigh(pts.T @ pts / len(pts)); ax = v[:, np.argmax(w)]
    t = pts @ ax; perp = np.abs(pts @ np.array([-ax[1], ax[0]]))
    far = np.abs(t) > 0.25 * np.abs(t).max()
    pos = perp[(t > 0) & far]; neg = perp[(t < 0) & far]
    if len(pos) < 3 or len(neg) < 3: return None, len(xs)
    sign = 1 if np.percentile(pos, 90) > np.percentile(neg, 90) else -1
    dx, dy = sign * ax[0], sign * ax[1]
    return (math.degrees(math.atan2(dx, -dy)) + 360) % 360, len(xs)

def main(folder, out):
    rows = []
    for f in sorted(glob.glob(f'{folder}/*.html')):
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})-(\d{1,2})\.html$', f)
        if not m: continue
        html = open(f, encoding='utf-8', errors='replace').read()
        img = re.search(r'curr_img/([^"]+\.png)', html)
        if not img or not os.path.exists(f'{folder}/img-{img.group(1)}'): continue
        rgb = np.asarray(Image.open(f'{folder}/img-{img.group(1)}').convert('RGB'))
        masks = {}
        y, mo, d, h = map(int, m.groups())
        st = [(int(x), int(yy), float(kn)) for x, yy, kn in re.findall(r'coords\s*=\s*["\']?(\d+),(\d+),\d+\s+ALT=["\']([\d.]+)kn\.', html, re.I)]
        for x, yy, kn in st:
            b = bucket(kn)
            if b not in masks: masks[b] = arrow_mask(rgb, kn)
            bearing, n = direction(masks[b], x, yy)
            # a neighbour of the same colour class closer than an arrow length can merge with this arrow
            crowded = any(bucket(k2) == b and 0 < math.hypot(x2 - x, y2 - yy) < 26 for x2, y2, k2 in st)
            rows.append({'time': f'{y}-{mo:02d}-{d:02d}T{h:02d}:00+09:00', 'x': x, 'y': yy,
                         'lat': round(35 + (631 - yy) / 840 + 0.0036, 4), 'lon': round(139.5 + (x - 30) / 675 - 0.0033, 4),
                         'speedKn': float(kn), 'bearingDeg': None if bearing is None else round(bearing, 1), 'pixels': int(n), 'crowded': crowded})
    json.dump(rows, open(out, 'w'), ensure_ascii=False)
    ok = sum(r['bearingDeg'] is not None for r in rows)
    print('rows', len(rows), 'with bearing', ok)

if __name__ == '__main__':
    main(*sys.argv[1:])
