#!/usr/bin/env python3
"""Head-only cutouts of tenya photos for the dragon counter catalog.

    python3 sites/dragon-counter/tools/tenya_images.py daiwa          # fetch DAIWA official color photos → work/src/<id>.jpg
    python3 sites/dragon-counter/tools/tenya_images.py cut            # work/src/*.jpg → public/tenya/<id>.webp (+ index.json)
    python3 sites/dragon-counter/tools/tenya_images.py add <id> <file> # one photo (e.g. from a retail page) for one catalog id

The cut keeps the photo as is (no posterizing): it removes the white background by flood fill from the
border (white stripes on the head survive), crops to the head, and fits it into a fixed 480x360 frame.
Images are derived from maker photos; see CATALOG-UPDATE.md for the owner's decision on that.
"""
import json, os, re, sys, unicodedata, urllib.request, collections
from PIL import Image, ImageFilter, ImageDraw
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); SITE = os.path.dirname(HERE)
PUB = os.path.join(SITE, "public"); OUT = os.path.join(PUB, "tenya"); WORK = os.path.join(SITE, "work", "src")
sys.path.insert(0, HERE); import catalog_add as ca
W, H = 480, 360

def bg_mask(im, white=236):
    a = np.asarray(im).astype(int); nw = (a.min(axis=2) > white)
    L = Image.fromarray((nw * 255).astype("uint8")).copy(); w, h = L.size
    for pt in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if L.getpixel(pt) == 255: ImageDraw.floodfill(L, pt, 128)
    return np.asarray(L) != 128

def head_box(mask):
    cov = mask.mean(axis=0); thr = 0.35 * cov.max(); cols = np.where(cov > thr)[0]
    runs = []; s = cols[0]; p = cols[0]
    for c in cols[1:]:
        if c != p + 1: runs.append((s, p)); s = c
        p = c
    runs.append((s, p)); x0, x1 = max(runs, key=lambda r: r[1] - r[0])
    while x1 + 1 < mask.shape[1] and cov[x1 + 1] > 0.12 * cov.max(): x1 += 1
    sub = mask[:, x0:x1 + 1]; ys = np.where(sub.any(axis=1))[0]; return x0, ys.min(), x1, ys.max()

def cut(path):
    im = Image.open(path).convert("RGB"); mask = bg_mask(im)
    x0, y0, x1, y1 = head_box(mask); pad = int((y1 - y0) * 0.06)
    bx0, by0, bx1, by1 = max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)
    im = im.crop((bx0, by0, bx1, by1)); m = Image.fromarray((mask[by0:by1, bx0:bx1] * 255).astype("uint8"))
    m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    r = min((W - 24) / im.width, (H - 24) / im.height); nw, nh = int(im.width * r), int(im.height * r)
    im = im.resize((nw, nh), Image.LANCZOS); m = m.resize((nw, nh), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
    layer = Image.new("RGBA", (nw, nh)); layer.paste(im, (0, 0)); layer.putalpha(m)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); out.alpha_composite(layer, ((W - nw) // 2, (H - nh) // 2)); return out

def catalog():
    items = json.load(open(os.path.join(PUB, "catalog-all.json"), encoding="utf-8"))["items"]
    src = open(os.path.join(PUB, "index.html"), encoding="utf-8").read()
    cat = json.loads(re.search(r"const TENYA_CAT=(\{.*?\});\n", src, re.S).group(1))
    urls = {(m, p): u for m, p, u, h in cat["products"]}
    for x in json.load(open(os.path.join(PUB, "catalog-extra.json"), encoding="utf-8"))["items"]:
        if x.get("u"): urls.setdefault((x["m"], x["p"]), x["u"])
    return items, urls

def get(u, binary=False):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}); d = urllib.request.urlopen(req, timeout=40).read()
    return d if binary else d.decode("utf-8", "ignore")

norm = lambda t: re.sub(r"[\s・･\-/／\.]|ツートン|[（(][^）)]*[）)]", "", unicodedata.normalize("NFKC", str(t))).lower()

def fetch_daiwa():
    os.makedirs(WORK, exist_ok=True); items, urls = catalog(); by = collections.defaultdict(list)
    for it in items:
        if it["m"] == "DAIWA": by[it["p"]].append(it)
    cache = {}; total = done = 0; report = []
    for p, its in sorted(by.items()):
        u = urls.get(("DAIWA", p), ""); total += len(its)
        if "daiwa.com/jp/product/" not in u: report.append(f"  公式ページなし：{p}（{len(its)}）"); continue
        h = cache.get(u) or get(u); cache[u] = h
        pairs = re.findall(r'<li>\s*<div class="img">\s*<img src="([^"]+)"[^>]*>\s*</div>\s*<p class="caption">([^<]+)</p>', h)
        best = {}
        for s, c in pairs:
            k = norm(re.sub(r"（\d+(?:\.\d+)?）$", "", c.strip()))
            if k not in best or "表" in c: best[k] = s.split("?")[0]
        miss = []
        for it in its:
            k = norm(it["c"]); s = best.get(k)
            if not s:
                cands = [v for kk, v in best.items() if k and (k in kk or kk in k)]; s = cands[0] if len(cands) == 1 else None
            if not s: miss.append(it["c"]); continue
            fn = os.path.join(WORK, ca.key(it["m"], it["p"], it["z"], it["c"]) + ".jpg")
            if not os.path.exists(fn): open(fn, "wb").write(get(s, True))
            done += 1
        if miss: report.append(f"  {p}：未対応 {len(miss)}/{len(its)}：" + "、".join(miss))
    print(f"DAIWA 写真あり {done}/{total}"); print("\n".join(report))

def export():
    os.makedirs(OUT, exist_ok=True); n = 0; ids = []
    for f in sorted(os.listdir(WORK)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")): continue
        iid = os.path.splitext(f)[0]
        try: im = cut(os.path.join(WORK, f))
        except Exception as e: print("切り出し失敗", f, e); continue
        im.resize((240, 180), Image.LANCZOS).save(os.path.join(OUT, iid + ".webp"), "WEBP", quality=82, method=6); ids.append(iid); n += 1
    json.dump({"v": 1, "ids": sorted(ids)}, open(os.path.join(OUT, "index.json"), "w"))
    size = sum(os.path.getsize(os.path.join(OUT, x)) for x in os.listdir(OUT)); print(f"書き出し {n} 枚、合計 {size/1024:.0f}KB")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "daiwa": fetch_daiwa()
    elif cmd == "cut": export()
    elif cmd == "add" and len(sys.argv) == 4:
        os.makedirs(WORK, exist_ok=True); import shutil; shutil.copy(sys.argv[3], os.path.join(WORK, sys.argv[2] + os.path.splitext(sys.argv[3])[1].lower())); export()
    else: sys.exit(__doc__)
