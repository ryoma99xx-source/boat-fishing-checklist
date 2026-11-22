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


def key(kind, m, s, c):
    return '%s|%s|%s|%s' % (kind, m, s, c)


def main():
    src = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    cat = json.load(open(os.path.join(HERE, 'tairaba', 'catalog.json'), encoding='utf-8'))
    ok = {key(k, r['m'], r['s'], c) for k in ('heads', 'ties', 'skirts') for r in cat[k] for c in r['c']}
    mp = json.load(open(MAP, encoding='utf-8')) if os.path.exists(MAP) else {}
    bad = []
    for f in sorted(glob.glob(os.path.join(src, '*', 'manifest-*.json'))):
        d = os.path.dirname(f)
        maker = re.sub(r'^manifest-|\.json$', '', os.path.basename(f))
        n = 0
        for r in json.load(open(f, encoding='utf-8')):
            k = key(r.get('kind', ''), maker, r.get('series', ''), r.get('color', ''))
            if k not in ok:
                bad.append(k); continue
            p = os.path.join(d, r['file'])
            if not os.path.exists(p):
                bad.append('missing ' + p); continue
            i = hashlib.sha1(k.encode('utf-8')).hexdigest()[:10]
            try:
                TI.make(p, os.path.join(OUT, i + '.webp'), False, r.get('crop'), bool(r.get('asis')))
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
      ".dk-t.dk-g:has(.gph){padding-right:62px}.dk-t.dk-g .gph.dkimg{width:50px;height:40px;right:6px;bottom:auto;top:50%;transform:translateY(-50%)}")
    return s


if __name__ == '__main__':
    main()
