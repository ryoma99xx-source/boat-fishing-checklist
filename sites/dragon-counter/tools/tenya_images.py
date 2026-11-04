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

def bg_mask(im, white=240):
    """Background = white connected to the border. The white image is eroded before the flood fill so that
    light anti-aliased edge pixels cannot bridge into white paint on the head, then grown back."""
    a = np.asarray(im).astype(int); nw = (a.min(axis=2) > white)
    L = Image.fromarray((nw * 255).astype("uint8")).copy().filter(ImageFilter.MinFilter(5))  # erode white by 2px
    w, h = L.size
    seeds = [(x, y) for x in (0, w // 4, w // 2, 3 * w // 4, w - 1) for y in (0, h // 2, h - 1)]
    for pt in seeds:
        if L.getpixel(pt) == 255: ImageDraw.floodfill(L, pt, 128)
    bg = Image.fromarray(((np.asarray(L) == 128) * 255).astype("uint8")).filter(ImageFilter.MaxFilter(5))  # grow back 2px
    return np.asarray(bg) == 0

def head_component(mask):
    """Keep only the blob that holds the tallest column (the head). Glow insets, labels and loose rig parts
    are separate blobs and drop out; a hook attached to the head stays and is trimmed by head_box."""
    cov = mask.sum(axis=0); x = int(cov.argmax()); ys = np.where(mask[:, x])[0]; y = int(ys[len(ys) // 2])
    L = Image.fromarray((mask * 255).astype("uint8")).copy(); ImageDraw.floodfill(L, (x, y), 128)
    return np.asarray(L) == 128

def head_box(mask, maxw=1.7):
    cov = mask.mean(axis=0); thr = 0.35 * cov.max(); cols = np.where(cov > thr)[0]
    runs = []; s = cols[0]; p = cols[0]
    for c in cols[1:]:
        if c != p + 1: runs.append((s, p)); s = c
        p = c
    runs.append((s, p)); x0, x1 = max(runs, key=lambda r: r[1] - r[0])
    core = mask[:, x0:x1 + 1]; cy = np.where(core.any(axis=1))[0]; hh = max(1, cy.max() - cy.min())
    lim = x0 + int(maxw * hh)                                                     # a head is never much wider than tall
    while x1 + 1 < min(mask.shape[1], lim) and cov[x1 + 1] > 0.12 * cov.max(): x1 += 1   # ring / eye side
    while x0 - 1 >= 0 and cov[x0 - 1] > 0.02 * cov.max(): x0 -= 1              # the nose tapers: keep it
    sub = mask[:, x0:x1 + 1]; ys = np.where(sub.any(axis=1))[0]; return x0, ys.min(), x1, ys.max()

MAXW = {"START": 1.25, "DUO": 1.3}   # START: long mole shank behind the head; DUO: glow inset pasted at the right
def cut(path, maker=""):
    global _maxw, _maker; _maxw = MAXW.get(maker, 1.7); _maker = maker
    src = Image.open(path)
    if src.mode in ("RGBA", "LA") or (src.mode == "P" and "transparency" in src.info):
        src = src.convert("RGBA"); al = np.asarray(src)[:, :, 3]
        if (al < 128).mean() > 0.05:   # real transparency: use it as the mask, flatten onto white for the pixels
            bgw = Image.new("RGB", src.size, (255, 255, 255)); bgw.paste(src, mask=src.split()[3]); im = bgw; mask = al >= 128
            return cut_masked(im, mask)
    im = src.convert("RGB"); mask = bg_mask(im)
    return cut_masked(im, mask)

def drop_dark_inset(im, mask):
    """Some makers paste a round glow-in-the-dark inset over the photo. It is a big, nearly square, almost black
    blob; a black head is oval and is the main blob, so it is left alone."""
    a = np.asarray(im).astype(int); dark = (a.max(axis=2) < 40) & mask
    if dark.mean() < 0.03: return mask
    cov = dark.sum(axis=0); x = int(cov.argmax()); ys = np.where(dark[:, x])[0]
    if not len(ys): return mask
    L = Image.fromarray((dark * 255).astype("uint8")).copy(); ImageDraw.floodfill(L, (x, int(ys[len(ys) // 2])), 128)
    comp = np.asarray(L) == 128; yy, xx = np.where(comp)
    if not len(yy): return mask
    hgt, wid = yy.max() - yy.min() + 1, xx.max() - xx.min() + 1; fill = comp.sum() / float(hgt * wid)
    if 0.85 <= wid / hgt <= 1.2 and fill > 0.3 and comp.sum() > 0.02 * mask.size:
        grown = np.asarray(Image.fromarray((comp * 255).astype("uint8")).filter(ImageFilter.MaxFilter(9))) > 0
        return mask & ~grown
    return mask

INSET = {("DUO", (680, 250)): (226, 90, 356, 220)}   # DUO pastes a round glow inset at a fixed spot of its 680x250 photos
def cut_masked(im, mask):
    box = INSET.get((globals().get("_maker", ""), im.size))
    if box:
        mask = mask.copy(); mask[box[1]:box[3], box[0]:box[2]] = False
    mask = drop_dark_inset(im, mask)
    mask = head_component(mask)
    x0, y0, x1, y1 = head_box(mask, globals().get('_maxw', 1.7)); pad = int((y1 - y0) * 0.06)
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

import urllib.parse
def _save(it, url):
    os.makedirs(WORK, exist_ok=True); fn = os.path.join(WORK, ca.key(it["m"], it["p"], it["z"], it["c"]) + os.path.splitext(urllib.parse.urlparse(url).path)[1].lower())
    if not os.path.exists(fn): open(fn, "wb").write(get(url, True))

_bright = {}
def brightest(urls):
    """Of several photos for one color (normal shot + glow-in-the-dark shot), the normal one is the brighter."""
    if len(urls) == 1: return urls[0]
    import io
    best = None
    for u in urls:
        if u not in _bright:
            try: im = Image.open(io.BytesIO(get(u, True))).convert("L").resize((64, 48)); _bright[u] = float(np.asarray(im).mean())
            except Exception: _bright[u] = -1
        if best is None or _bright[u] > _bright[best]: best = u
    return best

def fetch_generic(maker, pairs_of):
    """pairs_of(html, url) -> list of (image_url, color_name). Matches color names to catalog items of that maker."""
    items, urls = catalog(); by = collections.defaultdict(list)
    for it in items:
        if it["m"] == maker: by[it["p"]].append(it)
    cache = {}; total = done = 0; report = []
    for p, its in sorted(by.items()):
        u = urls.get((maker, p), ""); total += len(its)
        try: h = cache.get(u) or get(u); cache[u] = h
        except Exception as e: report.append(f"  ページ取得不可：{p}（{len(its)}）{u}"); continue
        pairs = pairs_of(h, u); best = collections.defaultdict(list)
        for s_, c in pairs:
            if s_ not in best[norm(c)]: best[norm(c)].append(s_)
        miss = []
        for it in its:
            k = norm(it["c"]); cands = best.get(k) or []
            if not cands:
                loose = [v for kk, v in best.items() if k and kk and (k in kk or kk in k)]; cands = loose[0] if len(loose) == 1 else []
            if not cands: miss.append(it["c"]); continue
            try: _save(it, brightest(cands)); done += 1
            except Exception as e: miss.append(it["c"] + "（取得失敗）")
        if miss: report.append(f"  {p}：未対応 {len(miss)}/{len(its)}：" + "、".join(dict.fromkeys(miss)))
    print(f"{maker} 写真あり {done}/{total}"); print("\n".join(report))

def pairs_hayabusa(h, u):
    out = []
    for tag in re.findall(r"<img[^>]+>", h):
        s_ = re.search(r'src="([^"]+)"', tag); a_ = re.search(r'alt="([^"]*)"', tag)
        if s_ and a_ and re.match(r"\s*\d+[\.．]", a_.group(1)):
            out.append((urllib.parse.urljoin(u, s_.group(1)), re.sub(r"^\s*\d+[\.．]\s*", "", a_.group(1))))
    return out

def pairs_duo(h, u):
    # color variant images carry the color code (PCA0758); the catalog names start with that code
    out = []
    for s_ in dict.fromkeys(re.findall(r'https?://[^"\s]+?product_color_variants/product_images/[^"\s]+?\.(?:jpg|png|webp)', h)):
        m = re.search(r"_([A-Z]{3}\d{4})\.", s_)
        if m: out.append((s_, m.group(1)))
    return out

def pairs_jackall(h, u):
    sec = h[h.find("product-color-list"):] if "product-color-list" in h else h
    return [(s_, a_) for s_, a_ in re.findall(r'<img src="([^"]+\.(?:png|jpg|webp))" alt="([^"]+)">', sec) if "/wp-content/uploads/" in s_]

def pairs_start(h, u):
    return [(s_, re.sub(r"^#", "", t)) for s_, t in re.findall(r'<a href="([^"]+)" data-lightbox="product_color" data-title="([^"]+)"', h)]

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
    items, _ = catalog(); maker_of = {ca.key(i["m"], i["p"], i["z"], i["c"]): i["m"] for i in items}
    only = set(sys.argv[2:])
    for f in sorted(os.listdir(WORK)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")): continue
        iid = os.path.splitext(f)[0]
        if only and maker_of.get(iid) not in only and iid not in only:
            if os.path.exists(os.path.join(OUT, iid + ".webp")): ids.append(iid)
            continue
        try: im = cut(os.path.join(WORK, f), maker_of.get(iid, ""))
        except Exception as e: print("切り出し失敗", f, e); continue
        im.resize((240, 180), Image.LANCZOS).save(os.path.join(OUT, iid + ".webp"), "WEBP", quality=82, method=6); ids.append(iid); n += 1
    json.dump({"v": 1, "ids": sorted(ids)}, open(os.path.join(OUT, "index.json"), "w"))
    size = sum(os.path.getsize(os.path.join(OUT, x)) for x in os.listdir(OUT)); print(f"書き出し {n} 枚、合計 {size/1024:.0f}KB")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "daiwa": fetch_daiwa()
    elif cmd == "hayabusa": fetch_generic("HAYABUSA", pairs_hayabusa)
    elif cmd == "jackall": fetch_generic("JACKALL", pairs_jackall)
    elif cmd == "start": fetch_generic("START", pairs_start)
    elif cmd == "duo":
        _norm = globals()["norm"]; globals()["norm"] = lambda t: (re.match(r"\s*([A-Z]{3}\d{4})", unicodedata.normalize("NFKC", str(t))) or [None, _norm(t)])[1]
        try: fetch_generic("DUO", pairs_duo)
        finally: globals()["norm"] = _norm
    elif cmd == "cut": export()
    elif cmd == "add" and len(sys.argv) == 4:
        os.makedirs(WORK, exist_ok=True); import shutil; shutil.copy(sys.argv[3], os.path.join(WORK, sys.argv[2] + os.path.splitext(sys.argv[3])[1].lower())); export()
    else: sys.exit(__doc__)
