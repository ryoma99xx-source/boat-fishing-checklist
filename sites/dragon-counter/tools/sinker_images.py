"""Makes the small sinker（増し錘）photos for the egi/sinker catalog page and article (not shown in the app).

    python3 tools/sinker_images.py <folder with manifest.json and raw/>

manifest.json = [{"m","s","color","image_url","file":"raw/…","source","note", "crop"?:[x0,y0,x1,y1], "asis"?:true}]
color "" = one photo for the whole product (shown when a colour has no photo of its own).
The photos are only cut (the box around the sinker, same as tipran_images.box) and made smaller. Pixels are not
otherwise changed: no colour correction, no retouching, no generated content.
Output: public/tipran/sinker/<id>.webp and tools/tipran/sinker-images.json {"maker|series|color": {"id","src"}}
(existing entries are kept; the same key is replaced)."""
import hashlib, json, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tipran_images as TI

OUT = os.path.join(os.path.dirname(HERE), 'public', 'tipran', 'sinker')
MAP = os.path.join(HERE, 'tipran', 'sinker-images.json')
MAXW, MAXH = 360, 270


def make(path, out, crop=None, asis=False):
    src = Image.open(path)
    alpha = src.mode in ('RGBA', 'LA') or (src.mode == 'P' and 'transparency' in src.info)
    im = src.convert('RGBA' if alpha else 'RGB')
    if crop:
        im = im.crop(tuple(crop))
    b = None if asis else TI.box(im, False)
    if b:
        im = im.crop(b)
    im.thumbnail((MAXW, MAXH), Image.LANCZOS)
    im.save(out, 'WEBP', quality=82, method=6)
    return im.size


def main():
    src = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    mp = json.load(open(MAP, encoding='utf-8')) if os.path.exists(MAP) else {}
    n = 0
    for r in json.load(open(os.path.join(src, 'manifest.json'), encoding='utf-8')):
        p = os.path.join(src, r['file'])
        if not os.path.exists(p):
            print('missing file', p); continue
        k = '%s|%s|%s' % (r['m'], r['s'], r.get('color', ''))
        i = 'sk' + hashlib.sha1(k.encode('utf-8')).hexdigest()[:10]
        make(p, os.path.join(OUT, i + '.webp'), r.get('crop'), bool(r.get('asis')))
        mp[k] = {'id': i, 'src': r.get('image_url', '')}
        n += 1
    json.dump(dict(sorted(mp.items())), open(MAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(n, 'made,', len(mp), 'in map')


if __name__ == '__main__':
    main()
