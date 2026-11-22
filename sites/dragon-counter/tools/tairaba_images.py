"""タイラバカウンターのカタログ写真（ヘッド・ネクタイ・スカートの色ごと）。オーナー指示 2026-11-22（案A：カタログ全部）。

    python3 tools/tairaba_images.py work/tairaba-img      写真を切り抜いて縮め、地図を作る
    （アプリへは tairaba_build.py が apply() で入れる）

入力：work/tairaba-img/<メーカー>/manifest-<メーカー>.json = [{kind, series, color, image_url, file, source, note, crop?, asis?}]
     （file は <メーカー>/ からの場所。集めた元の写真はリポジトリに入れない）
写真は「切り抜く」と「縮める」だけ。色や明るさの補正、消す・描き足すなどはしない（ティップランのエギの写真と同じ。tipran_images.py の box/make を使う）。
出力：public/tairaba/img/<id>.webp と tools/tairaba/images.json {"kind|maker|series|color": {"id","src"}}
アプリでは、カタログの色の選択肢と、登録したヘッド・ネクタイ・スカート（カタログから登録したもの）に写真が出る。
自分で付けた写真があれば、そちらを先に出す。
"""
import glob, hashlib, json, os, re, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
OUT = os.path.join(SITE, 'public', 'tairaba', 'img')
MAP = os.path.join(HERE, 'tairaba', 'images.json')
sys.path.insert(0, HERE)
import tipran_images as TI   # box() と make()（切り抜き・縮小だけ）

TI.MAXW, TI.MAXH = 320, 240
# 店の写真（シマノは公式サイトが読めず、大手釣具店の色別写真）には「イメージ画像」などの小さな文字が横に入る：
# いちばん大きい塊（商品）と、それに重なる塊だけを囲んで、離れた文字や小さな別の写真は枠の外にする（shop_box）
BLOB = {'シマノ'}


def key(kind, m, s, c):
    return '%s|%s|%s|%s' % (kind, m, s, c)


def shop_box(path):
    """店の写真の切り抜き枠：いちばん大きい塊（商品）と、その枠に重なる塊（針・ネクタイなど）だけを囲む。
    離れたところにある小さな文字（「イメージ画像」）や、小さな別の写真（裏側など）は枠の外になる。画素は変えない"""
    import numpy as np
    from scipy import ndimage
    from PIL import ImageFilter
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(int)
    fg = a.min(axis=2) < 236
    fg = np.asarray(Image.fromarray((fg * 255).astype('uint8')).filter(ImageFilter.MinFilter(3))) > 0
    lab, n = ndimage.label(fg, structure=np.ones((3, 3)))
    if not n:
        return None
    sizes = np.bincount(lab.ravel()); sizes[0] = 0
    sl = ndimage.find_objects(lab)
    big = sizes.argmax(); y0, y1, x0, x1 = sl[big - 1][0].start, sl[big - 1][0].stop, sl[big - 1][1].start, sl[big - 1][1].stop
    for _ in range(3):   # 主の枠に重なるもの（少し広げて）を足していく
        mx, my = 0.06 * (x1 - x0), 0.06 * (y1 - y0)
        for i, q in enumerate(sl):
            if not q or sizes[i + 1] < 15:
                continue
            if q[1].start < x1 + mx and q[1].stop > x0 - mx and q[0].start < y1 + my and q[0].stop > y0 - my:
                y0, y1, x0, x1 = min(y0, q[0].start), max(y1, q[0].stop), min(x0, q[1].start), max(x1, q[1].stop)
    pad = 6
    return [max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)]


def main():
    src = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    cat = json.load(open(os.path.join(HERE, 'tairaba', 'catalog.json'), encoding='utf-8'))
    ok = {key(k, r['m'], r['s'], c) for k in ('heads', 'ties', 'skirts') for r in cat[k] for c in r['c']}
    mp = json.load(open(MAP, encoding='utf-8')) if os.path.exists(MAP) else {}
    exf = os.path.join(HERE, 'tairaba', 'images-exclude.json')
    EX = set(json.load(open(exf, encoding='utf-8'))['keys']) if os.path.exists(exf) else set()   # 目で見て使わないと決めた写真
    bad = []
    for f in sorted(glob.glob(os.path.join(src, '*', 'manifest-*.json'))):
        d = os.path.dirname(f)
        maker = re.sub(r'^manifest-|\.json$', '', os.path.basename(f))
        n = 0
        for r in json.load(open(f, encoding='utf-8')):
            k = key(r.get('kind', ''), maker, r.get('series', ''), r.get('color', ''))
            if k in EX:
                continue
            if k not in ok:
                bad.append(k); continue
            p = os.path.join(d, r['file'])
            if not os.path.exists(p):
                bad.append('missing ' + p); continue
            i = hashlib.sha1(k.encode('utf-8')).hexdigest()[:10]
            try:
                cr = r.get('crop') or (shop_box(p) if maker in BLOB else None)
                TI.make(p, os.path.join(OUT, i + '.webp'), False, cr, bool(r.get('asis')) or (maker in BLOB and not r.get('crop')))
            except Exception as e:
                bad.append('error %s %s' % (p, e)); continue
            mp[k] = {'id': i, 'src': r.get('image_url', '')}
            n += 1
        print(maker, n)
    json.dump(dict(sorted(mp.items())), open(MAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    tot = sum(os.path.getsize(os.path.join(OUT, x)) for x in os.listdir(OUT))
    print(len(mp), 'images,', tot // 1024, 'KB; not matched:', len(bad))
    for b in bad[:40]:
        print('  ', b)


def apply(s):
    """TB_CAT の各行に、色と同じ並びの写真番号 i を付け、写真を出すところをつなぐ"""
    if not os.path.exists(MAP):
        return s
    import re as _re

    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('tairaba_images: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    IMG = json.load(open(MAP, encoding='utf-8'))
    # オーナーに確かめ中のもの（写真の中にメーカーの文字・印が入っていて、切り抜きでは外せない）。決まるまでアプリには出さない
    HOLD_MAKERS = {'松岡スペシャル'}
    HOLD_KEYS = set(json.load(open(os.path.join(HERE, 'tairaba', 'images-hold.json'), encoding='utf-8'))['keys']) if os.path.exists(os.path.join(HERE, 'tairaba', 'images-hold.json')) else set()
    IMG = {k: v for k, v in IMG.items() if k.split('|')[1] not in HOLD_MAKERS and k not in HOLD_KEYS}
    m = _re.search(r"const TB_CAT=(\{.*?\});\n", s, flags=_re.S)
    cat = json.loads(m.group(1))
    for k in ('heads', 'ties', 'skirts'):
        for r in cat.get(k, []):
            ii = [(IMG.get(key(k, r['m'], r['s'], c)) or {}).get('id', '') for c in r['c']]
            ii = [i if i and os.path.exists(os.path.join(OUT, i + '.webp')) else '' for i in ii]
            if any(ii):
                r['i'] = ii
    s = s[:m.start(1)] + json.dumps(cat, ensure_ascii=False, separators=(',', ':')) + s[m.end(1):]
    # 写真：自分で付けた写真があればそれ、なければカタログの写真（カタログから登録したもの）
    R("const gph=(id,cls)=>id&&GPH[id]?`<img class=\"gph ${cls||''}\" src=\"${GPH[id]}\" alt=\"\" decoding=\"async\">`:'';",
      "const gph0=(id,cls)=>id&&GPH[id]?`<img class=\"gph ${cls||''}\" src=\"${GPH[id]}\" alt=\"\" decoding=\"async\">`:'';\n"
      "/* カタログの写真（tairaba_images.py）。登録したもののメーカー・製品・色でカタログを引く */\n"
      "const TB_KIND={rigs:'heads',baits:'ties',skirts:'skirts'};\n"
      "function catImOf(k,x){if(!x||!x.series)return '';const r=(TB_CAT[TB_KIND[k]]||[]).find(r=>r.m===x.maker&&r.s===x.series);if(!r||!r.i)return '';return r.i[r.c.indexOf(x.color)]||''}\n"
      "function catIm(id){if(!id)return '';const s=spOf(SOLO);for(const k of ['rigs','baits','skirts']){const x=(s[k]||[]).find(g=>g.id===id);if(x)return catImOf(k,x)}return ''}\n"
      "const cimg=(i,cls)=>i?`<img class=\"gph cat ${cls||''}\" src=\"/tairaba/img/${i}.webp\" alt=\"\" loading=\"lazy\" decoding=\"async\" onerror=\"this.remove()\">`:'';\n"
      "const gph=(id,cls)=>gph0(id,cls)||cimg(catIm(id),cls);")
    s = s.replace("GPH[curGear(tr).rig]", "(GPH[curGear(tr).rig]||catIm(curGear(tr).rig))")
    # カタログの色の選択肢に写真
    R("""${cur.c.map(c=>`<button class="chip ${tbc.c.has(c)?'on':''}" data-act="tbcC" data-d="${esc(c)}">${esc(c)}</button>`).join('')}""",
      """${cur.c.map((c,j)=>{const im=cur.i&&cur.i[j];return `<button class="chip ${im?'cimg':''} ${tbc.c.has(c)?'on':''}" data-act="tbcC" data-d="${esc(c)}">${cimg(im,'cc')}<span>${esc(c)}</span></button>`}).join('')}""")
    R(".gph{flex:none;object-fit:cover;background:#fff;border-radius:6px}",
      ".gph{flex:none;object-fit:cover;background:#fff;border-radius:6px}.gph.cat{object-fit:contain}\n"
      ".chips.wrap .chip.cimg{box-sizing:border-box;display:inline-flex;flex-direction:column;align-items:stretch;gap:4px;flex:0 0 calc(50% - 4px);width:calc(50% - 4px);max-width:calc(50% - 4px);min-width:0;border-radius:12px;padding:6px;white-space:normal;text-align:center;font-size:14px;line-height:1.3}\n"
      ".gph.cc{width:100%;height:76px;border-radius:8px}.chip.cimg.on .gph{outline:3px solid var(--chipon);outline-offset:-3px}\n"
      ".dk-t.dk-g:has(.gph){flex-direction:row;align-items:center;gap:8px;flex-basis:168px}.dk-t.dk-g .gph.dkimg{position:static;flex:none;width:52px;height:42px;transform:none;border-radius:8px}.dk-t.dk-g:has(.gph) .dk-c{flex:1 1 auto;min-width:0;width:auto;max-width:none;font-size:13px;line-height:1.3;padding-right:14px}")
    return s


if __name__ == '__main__':
    main()
