"""SHIO（東京湾の潮と流れ・tide-current-map）の自作潮汐モデルを、カウンター用に間引く。オーナー指示 2026-11-23。

SHIO の調和定数（平均流＋12分潮。格子：横須賀沿岸50m → 東京湾中部100m → 東京湾250m → 内房200m の順で、
その点を含むいちばん細かい格子が答える）を、約1km間隔の点（横須賀〜中ノ瀬あたりは約500m）に間引いて public/shio-grid.json に書く。
1km の点の中心が陸なら、その点の範囲（±0.5間隔）の中でいちばん近い海のセルを使う（岸寄りの釣り場のため）。
カウンターは釣れた・アタリ・バラシ・📍で記録した GPS の位置ごとに、ここから流れ（向き・流速）を計算する。

    python3 tools/shio_grid.py            （SHIO のデータを直したら、これを動かして作り直す）
"""
import base64, json, math, os, struct

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'tide-current-map', 'app', 'data'))
OUT = os.path.join(HERE, '..', 'public', 'shio-grid.json')
ORDER = ['inner', 'mid', 'outer', 'uchibo']   # SHIO と同じ優先順（外房の500m格子 boso は使わない）
LAT0, LAT1, LON0, LON1 = 34.90, 35.75, 139.43, 140.20
DLAT, DLON = 0.009, 0.011                      # 約1km × 約1km
FINE = (35.19, 35.47, 139.62, 139.97, 0.0045, 0.0055)   # 横須賀〜観音崎〜中ノ瀬・木更津沖は約500m（SHIO の50m・100m格子の範囲）


def load(name):
    m = json.load(open(os.path.join(SRC, 'harmonic-%s.json' % name), encoding='utf-8'))
    raw = open(os.path.join(SRC, 'harmonic-%s.bin' % name), 'rb').read()
    n = len(m['constituents']); stride = 2 + 4 * n
    coef = struct.unpack('<%dh' % (len(raw) // 2), raw)
    assert len(coef) == len(m['wetIds']) * stride, name
    idx = {cid: i for i, cid in enumerate(m['wetIds'])}
    return {'m': m, 'coef': coef, 'stride': stride, 'idx': idx}


G = [(k, load(k)) for k in ORDER]
M0 = G[0][1]['m']
for k, g in G:
    for key in ('constituents', 'doodson', 'phaseOffsetDeg', 'nodal'):
        assert g['m'][key] == M0[key], (k, key)


def box(g):
    m = g['m']
    return (m['lat0'] - m['dlat'] / 2, m['lat0'] + m['dlat'] * (m['ny'] - .5), m['lon0'] - m['dlon'] / 2, m['lon0'] + m['dlon'] * (m['nx'] - .5))


def sample(lat, lon, DLAT, DLON):
    """SHIO と同じ：点を含む最初の格子が答える。中心が陸なら、その点の範囲（±0.5間隔）の中で最も近い海のセル。"""
    for k, g in G:
        s, n, w, e = box(g)
        if not (s <= lat <= n and w <= lon <= e):
            continue
        m = g['m']
        fx, fy = (lon - m['lon0']) / m['dlon'], (lat - m['lat0']) / m['dlat']
        ix, iy = round(fx), round(fy)
        rx, ry = int(math.ceil(DLON / 2 / m['dlon'])), int(math.ceil(DLAT / 2 / m['dlat']))
        best = None
        for dy in range(-ry, ry + 1):
            for dx in range(-rx, rx + 1):
                x, y = ix + dx, iy + dy
                if not (0 <= x < m['nx'] and 0 <= y < m['ny']):
                    continue
                c = g['idx'].get(y * m['nx'] + x)
                if c is None:
                    continue
                d = (dx * m['dlon'] * math.cos(math.radians(lat))) ** 2 + (dy * m['dlat']) ** 2
                if best is None or d < best[0]:
                    best = (d, c)
        if best is None:
            return None, k
        o = best[1] * g['stride']
        return g['coef'][o:o + g['stride']], k
    return None, None


def build(LAT0, LAT1, LON0, LON1, DLAT, DLON):
    nx, ny = int(round((LON1 - LON0) / DLON)) + 1, int(round((LAT1 - LAT0) / DLAT)) + 1
    mask, coefs, used = bytearray(nx * ny), [], {}
    for iy in range(ny):
        for ix in range(nx):
            c, k = sample(LAT0 + iy * DLAT, LON0 + ix * DLON, DLAT, DLON)
            if c is None:
                continue
            mask[iy * nx + ix] = 1; coefs.extend(c); used[k] = used.get(k, 0) + 1
    return {'lat0': LAT0, 'lon0': LON0, 'dlat': DLAT, 'dlon': DLON, 'nx': nx, 'ny': ny, 'grids': used,
            'mask': base64.b64encode(bytes(mask)).decode(), 'coef': base64.b64encode(struct.pack('<%dh' % len(coefs), *coefs)).decode()}, sum(mask)


base, nb = build(LAT0, LAT1, LON0, LON1, DLAT, DLON)
fine, nf = build(*FINE)
out = {'v': 1, 'src': 'SHIO 東京湾の潮と流れ（tide-current-map）自作潮汐モデル', 'stride': G[0][1]['stride'],
       'constituents': M0['constituents'], 'doodson': M0['doodson'], 'phaseOffsetDeg': M0['phaseOffsetDeg'], 'nodal': M0['nodal'],
       'unit': 'mm/s', 'layout': M0['layout'], 'convention': M0['convention'], **base, 'fine': fine}
open(OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
print('base points', nb, base['grids'], 'fine points', nf, fine['grids'], 'bytes', os.path.getsize(OUT))
