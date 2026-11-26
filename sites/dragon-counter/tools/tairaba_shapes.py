"""タイラバのネクタイ・スカートの「形の写真」（製品ごとに1枚）。オーナー指示 2026-11-25：
色ごとの写真が色見本・アップだけで、形がわからない製品がある → 製品ごとに全体が写った写真を1枚足す。

    python3 tools/tairaba_shapes.py work/tairaba-shape

入力：work/tairaba-shape/<メーカー>/shapes-<メーカー>.json = [{series, ok, why, image_url, file, source, crop?}]
     work/tairaba-shape/skirts/shapes-skirts.json はスカート（maker を各行に持つ）
     ok=false で file のあるものだけ使う。写真は「切り抜く」と「縮める」だけ（tipran_images.make）。
出力：public/tairaba/img/<id>.webp と tools/tairaba/shapes.json（足すだけ。渡したフォルダに無い製品の写真は、前のまま残る） {"ties|maker|series": {"id","src"}}
表示：カタログのページ・記事（tairaba_page.py）とアプリの色を選ぶところ（tairaba_images.apply）。
"""
import glob, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
OUT = os.path.join(SITE, 'public', 'tairaba', 'img')
MAP = os.path.join(HERE, 'tairaba', 'shapes.json')
sys.path.insert(0, HERE)
import tipran_images as TI


def main():
    src = sys.argv[1]
    TI.MAXW, TI.MAXH = 480, 300
    cat = json.load(open(os.path.join(HERE, 'tairaba', 'catalog.json'), encoding='utf-8'))
    ok = {'%s|%s|%s' % (k, r['m'], r['s']) for k in ('ties', 'skirts') for r in cat[k]}
    mp, bad = load(), []   # 足すだけ：前からある形の写真は残す（月次更新の新しいセッションには work/ が無い）
    for f in sorted(glob.glob(os.path.join(src, '*', 'shapes-*.json'))):
        d = os.path.dirname(f)
        name = re.sub(r'^shapes-|\.json$', '', os.path.basename(f))
        kind = 'skirts' if name == 'skirts' else 'ties'
        for r in json.load(open(f, encoding='utf-8')):
            if r.get('ok') or not r.get('file'):
                continue
            k = '%s|%s|%s' % (kind, r.get('maker') or name, r['series'])
            if k not in ok:
                bad.append(k); continue
            p = os.path.join(d, r['file'])
            if not os.path.exists(p):
                bad.append('missing ' + p); continue
            i = hashlib.sha1(('shape|' + k).encode('utf-8')).hexdigest()[:10]
            TI.make(p, os.path.join(OUT, i + '.webp'), False, r.get('crop'), bool(r.get('asis')))
            mp[k] = {'id': i, 'src': r.get('image_url', '')}
    json.dump(dict(sorted(mp.items())), open(MAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    mp = {k: v for k, v in mp.items() if k in ok and os.path.exists(os.path.join(OUT, v['id'] + '.webp'))}
    print(len(mp), 'shape photos; not matched:', len(bad))
    for b in bad:
        print('  ', b)


def load():
    return json.load(open(MAP, encoding='utf-8')) if os.path.exists(MAP) else {}


if __name__ == '__main__':
    main()
