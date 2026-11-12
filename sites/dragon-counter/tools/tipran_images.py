"""Makes the small egi photos for ティップランカウンター's catalog.

    python3 tools/tipran_images.py <folder with manifest-<maker>.json and raw/>

Input: manifest-<maker>.json = [{series, color, image_url, file, source, note}] (file is relative to the folder).
The photos are only cut (the box around the egi) and made smaller. Pixels are not otherwise changed: no colour
correction, no retouching, no generated content. A transparent background stays transparent.
Output: public/tipran/egi/<id>.webp and tools/tipran/egi-images.json {"maker|series|color": {"id", "src"}}.
tipran_build.py reads that map and gives each catalog row an image list next to its colours."""
import glob, hashlib, json, os, re, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
OUT = os.path.join(SITE, 'public', 'tipran', 'egi')
MAP = os.path.join(HERE, 'tipran', 'egi-images.json')
MAKER = {'フィッシュリーグ': 'マルキユー'}   # same names as tipran_catalog.py
MAXW, MAXH = 320, 140                       # shown at about 160x70 CSS px
# Store photos with printed labels next to the egi ("BASE : GOLD", "イメージ画像", a glow photo): keep only the box
# around the biggest blob (the egi with its hooks), so the labels fall outside the cut.
BLOB = {'シマノ'}


def key(m, s, c):
    return '%s|%s|%s' % (MAKER.get(m, m), s, c)


def box(im, blob=False):
    """The box around everything that is not background: transparent pixels, or white/near-white ones.
    Thin specks (JPEG noise, a 1px frame line) are ignored by eroding the mask before measuring."""
    if im.mode == 'RGBA' and (np.asarray(im)[:, :, 3] < 128).mean() > 0.05:
        fg = np.asarray(im)[:, :, 3] >= 24
    else:
        a = np.asarray(im.convert('RGB')).astype(int)
        fg = a.min(axis=2) < 236
    fg = np.asarray(Image.fromarray((fg * 255).astype('uint8')).filter(ImageFilter.MinFilter(3))) > 0
    if blob and fg.any():
        # the egi = the biggest blob, plus blobs that sit within its height (the hooks, a clear fin). A label or
        # glow photo reaches below the egi, so it is left out
        from scipy import ndimage
        lab, n = ndimage.label(fg, structure=np.ones((3, 3)))
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        sl = ndimage.find_objects(lab)
        big = sizes.argmax(); y0, y1 = sl[big - 1][0].start, sl[big - 1][0].stop
        keep = [big] + [i + 1 for i, q in enumerate(sl) if q and i + 1 != big and sizes[i + 1] >= 20
                        and q[0].start >= y0 - 0.2 * (y1 - y0) and q[0].stop <= y1 + 2]
        fg = np.isin(lab, keep)
        # a label that reaches up beside the sinker would show at the bottom of the box: end the box just above it
        # (only when that costs at most the bottom fifth of the egi)
        ys, xs = np.where(fg); top, bot, lft, rgt = ys.min(), ys.max(), xs.min(), xs.max()
        for i, q in enumerate(sl):
            if q and i + 1 not in keep and sizes[i + 1] >= 20 and q[1].start <= rgt and q[1].stop > lft \
                    and bot - 0.2 * (bot - top) < q[0].start <= bot:
                bot = q[0].start - 10   # the box gets 6px of margin later
        fg[bot + 1:] = False
    ys, xs = np.where(fg)
    if not len(xs):
        return None
    pad = 6
    return (max(0, xs.min() - pad), max(0, ys.min() - pad), min(im.width, xs.max() + 1 + pad), min(im.height, ys.max() + 1 + pad))


def make(path, out, blob=False):
    src = Image.open(path)
    alpha = src.mode in ('RGBA', 'LA') or (src.mode == 'P' and 'transparency' in src.info)
    im = src.convert('RGBA' if alpha else 'RGB')
    b = box(im, blob)
    if b:
        im = im.crop(b)
    im.thumbnail((MAXW, MAXH), Image.LANCZOS)
    im.save(out, 'WEBP', quality=82, method=6)
    return im.size


def main():
    src = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    mp = json.load(open(MAP, encoding='utf-8')) if os.path.exists(MAP) else {}
    for f in sorted(glob.glob(os.path.join(src, 'manifest-*.json'))):
        maker = re.sub(r'^manifest-|\.json$', '', os.path.basename(f))
        n = 0
        for r in json.load(open(f, encoding='utf-8')):
            p = os.path.join(src, r['file'])
            if not os.path.exists(p):
                print('missing file', p)
                continue
            k = key(maker, r['series'], r['color'])
            i = hashlib.sha1(k.encode('utf-8')).hexdigest()[:10]
            make(p, os.path.join(OUT, i + '.webp'), maker in BLOB)
            mp[k] = {'id': i, 'src': r.get('image_url', '')}
            n += 1
        print(maker, n)
    json.dump(dict(sorted(mp.items())), open(MAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    tot = sum(os.path.getsize(os.path.join(OUT, x)) for x in os.listdir(OUT))
    print(len(mp), 'images,', tot // 1024, 'KB')


if __name__ == '__main__':
    main()
