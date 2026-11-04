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
try:
    from scipy import ndimage as _nd
except ImportError:   # pip install scipy — without it the PIL flood fill below is used (same result, much slower)
    _nd = None

def label(mask):
    """Connected components (4-neighbour) of a boolean mask → (labels array, count)."""
    if _nd is not None: return _nd.label(mask)
    lab = np.zeros(mask.shape, dtype=np.int32); L = Image.fromarray((mask * 255).astype("uint8")).copy(); n = 0
    while True:
        rest = (np.asarray(L) == 255)
        if not rest.any(): break
        y, x = np.argwhere(rest)[0]; n += 1; ImageDraw.floodfill(L, (int(x), int(y)), 1 + n % 200)
        lab[(np.asarray(L) == 1 + n % 200) & (lab == 0)] = n
    return lab, n

def blobs(mask, limit=None, min_px=50):
    """Blobs of a mask as boolean arrays, biggest first."""
    lab, n = label(mask)
    if n == 0: return []
    sizes = np.bincount(lab.ravel())[1:]; order = np.argsort(-sizes)
    out = [lab == (i + 1) for i in order if sizes[i] >= min_px]
    return out[:limit] if limit else out

def bg_mask(im, white=240, store=False):
    """Background = white connected to the border, plus enclosed white regions that are big enough. The white image
    is eroded before labelling so that light anti-aliased edge pixels cannot bridge into white paint on the head,
    then grown back. Maker photos: an enclosed region counts only if huge (inside a drawn frame). Store shots: also
    the inside of a hook holder or a leader loop (a white head is shaded, so its own white patches stay small)."""
    a = np.asarray(im).astype(int); mn = a.min(axis=2)
    if store and (mn >= 254).mean() > 0.5: white = max(white, 251)   # pure white backdrop: a white head is only a little darker
    nw = np.asarray(Image.fromarray(((mn > white) * 255).astype("uint8")).filter(ImageFilter.MinFilter(5))) > 0   # erode 2px
    lab, n = label(nw)
    if n == 0: return np.ones(mn.shape, bool)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])); border = border[border > 0]
    sizes = np.bincount(lab.ravel()); lim = (0.015 if store else 0.2) * mn.size
    big = np.where(sizes >= lim)[0]; big = big[big > 0]
    keep = np.zeros(n + 1, bool); keep[border] = True; keep[big] = True
    bg = keep[lab]
    bg = np.asarray(Image.fromarray((bg * 255).astype("uint8")).filter(ImageFilter.MaxFilter(5))) > 0   # grow back 2px
    return ~bg

def head_component(mask):
    """Keep only the biggest *solid* blob (the head, with any hook attached to it). Glow insets, captions, loose rig
    parts are separate, smaller blobs and drop out; the hook is trimmed later by head_box. Store photos also carry
    a drawn frame (a huge but hollow outline) and a pasted glow photo (a filled rectangle): both are skipped by
    their fill ratio."""
    for comp in blobs(mask, 10):
        yy, xx = np.where(comp); bbox = float((yy.max() - yy.min() + 1) * (xx.max() - xx.min() + 1)); fill = comp.sum() / bbox
        if globals().get("_store"):
            if fill < 0.2 and bbox > 0.1 * mask.size: continue          # hollow frame drawn around the product shot
            if fill > 0.9 and comp.sum() > 0.01 * mask.size: continue   # pasted rectangular (glow) photo
            if comp.sum() > 0.01 * mask.size and rectish(comp[yy.min():yy.max() + 1, xx.min():xx.max() + 1]): continue
        return comp
    return mask

def rectish(c):
    """A pasted photo touches all four sides of its bbox along most of their length; a head touches each at a point."""
    return min(c[0].mean(), c[-1].mean(), c[:, 0].mean(), c[:, -1].mean()) > 0.6

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
    nose = x0 - int(0.6 * hh) if globals().get("_store") else 0                  # ...but a leader line is not a nose
    while x0 - 1 >= max(0, nose) and cov[x0 - 1] > 0.02 * cov.max(): x0 -= 1     # the nose tapers: keep it
    sub = mask[:, x0:x1 + 1]; ys = np.where(sub.any(axis=1))[0]; return x0, ys.min(), x1, ys.max()

MAXW = {"START": 1.25, "DUO": 1.3, "SHIMANO": 1.45}   # START: long mole shank; DUO: glow inset at the right; SHIMANO: hook holder behind the head
FIXED = {   # store shots are template photos: one composition per store and product, only the head colour changes → fixed head box
    ("fishing-sagamiya", "サーベルマスター 船テンヤ"): (50, 235, 280, 368),
    ("fishing-sagamiya", "サーベルマスター 船テンヤ ゲキハヤ"): (82, 222, 270, 314),
    ("fishing-sagamiya", "サーベルマスター 船テンヤ β ゲキハヤ"): (105, 252, 295, 354),
    ("f-marunishi", "サーベルマスター 船テンヤ β"): (195, 290, 350, 425),   # 680x680 (logo, SALE and size overlays)
}
def cut(path, maker="", product="", store=None, flags=None):
    """store: name of the store the photo came from (or True) → a retail shot (frame, badges, glow photo, snap and
    leader in the picture): the head is found by its eye, or by a fixed box known for that store and product"""
    global _maxw, _maker, _fixed, _store, _flags
    _maxw = 1.45 if store else MAXW.get(maker, 1.7); _maker = maker; _store = bool(store); _fixed = FIXED.get((store, product)) if store else None
    _flags = flags or {}
    src = Image.open(path)
    if src.mode in ("RGBA", "LA") or (src.mode == "P" and "transparency" in src.info):
        src = src.convert("RGBA"); al = np.asarray(src)[:, :, 3]
        if (al < 128).mean() > 0.05:   # real transparency: use it as the mask, flatten onto white for the pixels
            bgw = Image.new("RGB", src.size, (255, 255, 255)); bgw.paste(src, mask=src.split()[3]); im = bgw; mask = al >= 128
            return cut_masked(im, mask)
    im = src.convert("RGB"); mask = bg_mask(im, store=store)
    return cut_masked(im, mask)

def drop_dark_inset(im, mask):
    """Some makers paste a round glow-in-the-dark inset over the photo. It is a big, nearly square, almost black
    blob; a black head is oval and is the main blob, so it is left alone. Store shots paste a rectangular one."""
    a = np.asarray(im).astype(int); dark = (a.max(axis=2) < 40) & mask
    if dark.mean() < 0.03: return mask
    for comp in blobs(dark, 3):
        yy, xx = np.where(comp); hgt, wid = yy.max() - yy.min() + 1, xx.max() - xx.min() + 1; fill = comp.sum() / float(hgt * wid)
        crop = comp[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
        rect = globals().get("_store") and rectish(crop)
        if comp.sum() > 0.015 * mask.size and ((0.85 <= wid / hgt <= 1.2 and fill > 0.3) or rect):
            grown = np.asarray(Image.fromarray((comp * 255).astype("uint8")).filter(ImageFilter.MaxFilter(9))) > 0
            mask = mask & ~grown
    return mask

def find_eye(im, mask):
    """The head is the one part of a store shot with an eye: a small, compact, near-black blob that sits inside the
    object (a caption letter is as dark and compact, but white paper surrounds it). Returns (x, y) or None."""
    a = np.asarray(im).astype(int); dark = (a.max(axis=2) < 70) & mask; best = None; lab = None
    for c in blobs(dark, 120, min_px=int(0.0002 * mask.size)):
        n = c.sum()
        if not 0.0002 * mask.size <= n <= 0.006 * mask.size: continue
        yy, xx = np.where(c); h, w = yy.max() - yy.min() + 1, xx.max() - xx.min() + 1
        if not 0.4 <= w / h <= 2.5 or n < 0.3 * h * w: continue   # loose: on a silver head the eye merges with shading
        k = 2 * (max(h, w) // 2) + 3; ring = (np.asarray(Image.fromarray((c * 255).astype("uint8")).filter(ImageFilter.MaxFilter(k))) > 0) & ~c
        if mask[ring].mean() < 0.6: continue
        # a letter in a line of small print passes the ring test (the gaps between letters close up): the blob it
        # sits in is a short, wide line, while the head's blob is several times taller than the eye
        if lab is None: lab = label(mask)[0]
        by, bx = np.where(lab == lab[yy[0], xx[0]]); bh, bw = by.max() - by.min() + 1, bx.max() - bx.min() + 1
        if bh < 3 * max(h, w) or bw > 6 * bh: continue
        if best is None or n > best[0]: best = (n, int(xx.mean()), int(yy.mean()), int(max(h, w)))
    return best[1:] if best else None

def eye_box(im, mask, frac):
    """Box around the head of a store shot. With an eye, the box follows from the eye's place and the head's height
    at the eye (the eye sits in the front half); head_box then trims the hook or holder stem behind it.
    Without an eye, peel the biggest blob by frac x its height so wires and bars vanish and box the biggest core."""
    if not mask.any(): return None
    eye = find_eye(im, mask)
    if eye:
        x, y, d = eye; runs = []
        for cx in range(max(0, x - 2 * d), min(mask.shape[1], x + 4 * d + 1)):   # head height: typical run through the eye's rows
            col = mask[:, cx]; i = 0
            while i < len(col):
                if not col[i]: i += 1; continue
                j = i
                while j + 1 < len(col) and col[j + 1]: j += 1
                if i <= y <= j or (j - i) > 2 * d: runs.append(j - i + 1)
                i = j + 1
        hh = max(20, int(np.median(runs))) if runs else 6 * d   # the snap above the head front only widens a few columns
        x0, x1 = max(0, x - int(0.9 * hh)), min(mask.shape[1], x + int(1.6 * hh))
        y0, y1 = max(0, y - int(0.65 * hh)), min(mask.shape[0], y + int(0.65 * hh))
    else:
        bl = blobs(mask, 1); blob = bl[0] if bl else mask
        yy = np.where(blob.any(axis=1))[0]; r = max(2, int(frac * (yy.max() - yy.min() + 1)))
        M = Image.fromarray((blob * 255).astype("uint8"))
        for _ in range(r): M = M.filter(ImageFilter.MinFilter(3))
        cores = blobs(np.asarray(M) > 0, 1)
        if not cores: return None
        cy, cx = np.where(cores[0])
        x0, x1 = max(0, cx.min() - int(2.5 * r)), min(mask.shape[1], cx.max() + int(2.5 * r) + 1)
        y0, y1 = max(0, cy.min() - int(1.5 * r)), min(mask.shape[0], cy.max() + int(1.5 * r) + 1)
    box = np.zeros_like(mask); box[y0:y1, x0:x1] = True; return box

INSET = {("DUO", (680, 250)): (226, 90, 356, 220)}   # DUO pastes a round glow inset at a fixed spot of its 680x250 photos
def cut_masked(im, mask):
    box = INSET.get((globals().get("_maker", ""), im.size))
    if box:
        mask = mask.copy(); mask[box[1]:box[3], box[0]:box[2]] = False
        # the inset is a filled disc: find columns whose longest vertical run is disc-sized, right of the head, and drop them
        runs = []
        for x in range(mask.shape[1]):
            col = mask[:, x]; best = cur = 0
            for v in col:
                cur = cur + 1 if v else 0; best = max(best, cur)
            runs.append(best)
        tall = [x for x, r in enumerate(runs) if r >= 105]
        if tall:
            cov = mask.sum(axis=0); head_x = int(cov[: mask.shape[1] // 2].argmax())
            right = [x for x in tall if x > head_x + 60]
            if right:
                x0 = max(0, min(right) - 70); mask[:, x0:] = False
    mask = drop_dark_inset(im, mask)
    if globals().get("_flags", {}).get("fill"):   # source whitened by hand around the head: seal small gaps, fill the holes
        k = 13; mask = np.asarray(Image.fromarray((mask * 255).astype("uint8")).filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))) > 0
        if _nd is not None: mask = _nd.binary_fill_holes(mask)
    if globals().get("_fixed"):
        x0, y0, x1, y1 = _fixed; box = np.zeros_like(mask); box[y0:y1, x0:x1] = True; mask = mask & box
    elif globals().get("_store"):
        box = eye_box(im, mask, 0.1)
        if box is not None: mask = mask & box
    mask = head_component(mask)
    x0, y0, x1, y1 = head_box(mask, globals().get('_maxw', 1.7)); pad = int((y1 - y0) * 0.06)
    bx0, by0, bx1, by1 = max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)
    im = im.crop((bx0, by0, bx1, by1)); m = Image.fromarray((mask[by0:by1, bx0:bx1] * 255).astype("uint8"))
    m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    if globals().get("_store"): im, m = defringe(im, m)
    r = min((W - 24) / im.width, (H - 24) / im.height); nw, nh = int(im.width * r), int(im.height * r)
    im = im.resize((nw, nh), Image.LANCZOS); m = m.resize((nw, nh), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
    layer = Image.new("RGBA", (nw, nh)); layer.paste(im, (0, 0)); layer.putalpha(m)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); out.alpha_composite(layer, ((W - nw) // 2, (H - nh) // 2)); return out

def defringe(im, m, band=3):
    """Store JPEGs on white: the pixels along the edge are a blend of head and white paper, and on the app's dark
    background they show as a ragged white rim. In a thin band along the mask edge, make a pixel as transparent as
    it is white and take the white back out of its colour (un-premultiply against white)."""
    mk = np.asarray(m) > 127; k = 2 * band + 1
    inner = np.asarray(Image.fromarray((mk * 255).astype("uint8")).filter(ImageFilter.MinFilter(k))) > 0
    ring = mk & ~inner
    a = np.asarray(im).astype(float); mn = a.min(axis=2)
    alpha = np.where(mk, 1.0, 0.0); alpha[ring] = np.clip((250.0 - mn[ring]) / 45.0, 0.0, 1.0)   # white → 0, ≤205 → 1
    out = a.copy(); sel = ring & (alpha > 0.15)
    aa = alpha[sel][:, None]; out[sel] = np.clip((a[sel] - 255.0 * (1.0 - aa)) / aa, 0, 255)
    return Image.fromarray(out.astype("uint8")), Image.fromarray((alpha * 255).astype("uint8"))

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
    product_of = {ca.key(i["m"], i["p"], i["z"], i["c"]): i["p"] for i in items}
    retail = os.path.join(SITE, "work", "retail.json")   # ids whose source is a store photo (kept out of git with the sources)
    rj = json.load(open(retail, encoding="utf-8")) if os.path.exists(retail) else {}
    stores = {k: (None if v.get("plain") else (v.get("src") or True)) for k, v in rj.items()}   # "plain": hand-cropped to the head already
    flags = {k: {f: v[f] for f in ("fill",) if v.get(f)} for k, v in rj.items()}
    only = set(sys.argv[2:])
    for f in sorted(os.listdir(WORK)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")): continue
        iid = os.path.splitext(f)[0]
        if only and maker_of.get(iid) not in only and iid not in only:
            if os.path.exists(os.path.join(OUT, iid + ".webp")): ids.append(iid)
            continue
        try: im = cut(os.path.join(WORK, f), maker_of.get(iid, ""), product_of.get(iid, ""), stores.get(iid), flags.get(iid))
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
