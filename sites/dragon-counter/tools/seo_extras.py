"""AI・検索に読まれやすくするための付け足し（dragon-counter.cutlassfish.tokyo）。オーナー指示 2026-11-26。

    python3 tools/seo_extras.py        構造化データ（JSON-LD）を入れ直し、sitemap.xml・llms.txt・robots.txt を作り直す

ページを作るスクリプト（tairaba_build・tipran_build・tenya_page・egi_page・tairaba_page）は、
書き出す前に ld() を通し、書き出したあとに after_build() を呼ぶ（＝このファイルの main() と同じ）。
ドラゴンカウンター本体（public/index.html）を手で直したときは、いつもどおり tairaba_build → tipran_build を回せば一緒に更新される。

やること
- 構造化データ：<head> の <!--ld--> 〜 <!--/ld--> を、ページの <title>・説明・og の値から作り直す（無ければ </head> の前に足す）。
  アプリ（カウンター3つ）は WebApplication、カタログは CollectionPage（「YYYY-MM-DD 時点」を dateModified に）。見た目は変わらない。
- sitemap.xml：<lastmod> は「そのページの中身が変わった日」。tools/seo-lastmod.json に中身のハッシュと日付を覚えておき、
  ハッシュが変わったときだけ今日（日本時間）の日付にする（毎回今日にすると、検索側に信用されなくなるため）。
- robots.txt：全部どうぞ＋サイトマップの場所。llms.txt：AI 向けの案内。
- SHA256SUMS・mirror-manifest.json：index.html と robots.txt のハッシュを合わせる（毎日の点検 ops/sitecheck が照合に使う）。
- リンク集（/links/）は検索に出さない設定（noindex）なので、サイトマップ・llms.txt に入れない。
"""
import datetime, hashlib, html as H, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.dirname(HERE)
PUB = os.path.join(SITE_DIR, 'public')
STATE = os.path.join(HERE, 'seo-lastmod.json')
HOST = 'https://dragon-counter.cutlassfish.tokyo'
PAGES = [  # (公開の道, ファイル, 種類)
    ('/', 'index.html', 'app'),
    ('/tipran/', 'tipran/index.html', 'app'),
    ('/tairaba/', 'tairaba/index.html', 'app'),
    ('/tenya-catalog/', 'tenya-catalog/index.html', 'catalog'),
    ('/egi-catalog/', 'egi-catalog/index.html', 'catalog'),
    ('/tairaba-catalog/', 'tairaba-catalog/index.html', 'catalog'),
    ('/tairaba-catalog/ties/', 'tairaba-catalog/ties/index.html', 'catalog'),
]
KIND = {p: k for p, f, k in PAGES}
ORG = {'@type': 'Organization', 'name': '3rd-Penguin Fishing Lab.', 'url': 'https://cutlassfish.tokyo/'}
SITE = {'@type': 'WebSite', 'name': '東京湾の魚・釣り（3rd-Penguin Fishing Lab.）', 'url': 'https://cutlassfish.tokyo/'}


def _meta(s, name):
    m = re.search(r'<meta\s+(?:name|property)="%s"\s+content="([^"]*)"' % re.escape(name), s)
    return H.unescape(m.group(1)) if m else ''


def _title(s):
    t = re.search(r'<title>(.*?)</title>', s, re.S)
    return H.unescape(t.group(1).strip()) if t else ''


def _name(s, kind):
    """アプリは名前だけ（「ドラゴンカウンター｜TOKYO BAY FISHING」→「ドラゴンカウンター」）。カタログは題のまま"""
    return (_meta(s, 'og:title') or _title(s).split('｜')[0]) if kind == 'app' else _title(s)


def ld(s, path):
    """ページの html に構造化データを入れて返す。path は公開の道（例 '/tairaba/'）。何度通しても同じ結果になる"""
    kind = KIND.get(path)
    if not kind:
        return s
    d = {'@context': 'https://schema.org', '@type': 'WebApplication' if kind == 'app' else 'CollectionPage',
         'name': _name(s, kind), 'url': HOST + path, 'description': _meta(s, 'description'), 'inLanguage': 'ja'}
    img = _meta(s, 'og:image')
    if img:
        d['image'] = img
    if kind == 'app':
        d.update({'applicationCategory': 'SportsApplication', 'operatingSystem': 'Any', 'browserRequirements': 'JavaScript が使えるブラウザ（スマートフォン・パソコン）',
                  'isAccessibleForFree': True, 'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'JPY'}})
    else:
        m = re.search(r'(\d{4}-\d{2}-\d{2})\s*時点', re.sub(r'<script.*?</script>', '', s, flags=re.S))
        if m:
            d['dateModified'] = m.group(1)
    d['publisher'] = ORG
    d['isPartOf'] = SITE
    block = '<!--ld--><script type="application/ld+json">%s</script><!--/ld-->' % json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    if '<!--ld-->' in s:
        return re.sub(r'<!--ld-->.*?<!--/ld-->', lambda m: block, s, count=1, flags=re.S)
    return s.replace('</head>', block + '\n</head>', 1)


def _today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d')


def _lastmods():
    """ページごとの「中身が変わった日」。ハッシュが前と違うページだけ今日にする"""
    st = json.load(open(STATE, encoding='utf-8')) if os.path.exists(STATE) else {}
    out, changed = {}, False
    for p, f, k in PAGES:
        h = hashlib.sha256(open(os.path.join(PUB, f), 'rb').read()).hexdigest()
        if st.get(f, {}).get('sha') != h:
            st[f] = {'sha': h, 'date': _today()}
            changed = True
        out[f] = st[f]['date']
    if changed:
        json.dump(st, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
        open(STATE, 'a').write('\n')
    return out


def _write(rel, text):
    """中身が変わったときだけ書く"""
    fp = os.path.join(PUB, rel)
    if not os.path.exists(fp) or open(fp, encoding='utf-8').read() != text:
        open(fp, 'w', encoding='utf-8').write(text)
        return True
    return False


def main(quiet=False):
    done = []
    # 1) 各ページの構造化データ
    for p, f, k in PAGES:
        fp = os.path.join(PUB, f)
        s = open(fp, encoding='utf-8').read()
        s2 = ld(s, p)
        if s2 != s:
            open(fp, 'w', encoding='utf-8').write(s2)
            done.append('ld ' + f)
    # 2) サイトマップ（更新日は中身が変わった日）
    lm = _lastmods()
    xs = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xs += ['<url><loc>%s%s</loc><lastmod>%s</lastmod></url>' % (HOST, p, lm[f]) for p, f, k in PAGES]
    xs.append('</urlset>')
    if _write('sitemap.xml', '\n'.join(xs) + '\n'):
        done.append('sitemap.xml')
    # 3) robots.txt
    if _write('robots.txt', 'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % HOST):
        done.append('robots.txt')
    # 4) llms.txt（AI 向けの案内）
    L = ['# 東京湾の釣りツール（3rd-Penguin Fishing Lab.）', '',
         '> 東京湾の船釣りのための無料ツール。登録なしでブラウザで使える釣果記録アプリ（タチウオ・アオリイカ・マダイ）と、テンヤ・エギ・タイラバの製品と色を写真で一覧にしたカタログ。'
         '釣行記・釣り方・考察の記事は本サイト https://cutlassfish.tokyo/ にあります（案内：https://cutlassfish.tokyo/llms.txt）。', '']
    for head, kind in (('## 釣果記録アプリ', 'app'), ('## カタログ', 'catalog')):
        L.append(head)
        for p, f, k in PAGES:
            if k == kind:
                s = open(os.path.join(PUB, f), encoding='utf-8').read()
                L.append('- [%s](%s%s): %s' % (_name(s, k), HOST, p, _meta(s, 'description')))
        L.append('')
    L += ['## そのほか',
          '- [東京湾の潮と流れ](https://tide-current-map.cutlassfish.tokyo/): 地図で東京湾の場所ごとの流れの向き・速さと潮位を見る無料ツール',
          '- [東京湾の魚・釣り（記事）](https://cutlassfish.tokyo/): 釣行記・釣り方・考察',
          '- [サイトマップ](%s/sitemap.xml)' % HOST]
    if _write('llms.txt', '\n'.join(L) + '\n'):
        done.append('llms.txt')
    # 5) 毎日の点検が照合に使う一覧（index.html・robots.txt）
    import catalog_add
    sums = open(os.path.join(SITE_DIR, 'SHA256SUMS'), encoding='utf-8').read()
    for name in ('index.html', 'robots.txt'):
        h = hashlib.sha256(open(os.path.join(PUB, name), 'rb').read()).hexdigest()
        if (h + '  ' + name) not in sums:
            catalog_add.refresh_hashes(name)
            done.append('SHA256SUMS ' + name)
    if not quiet:
        print('seo_extras:', ', '.join(done) if done else '変更なし')


def after_build():
    """ページを作るスクリプトが、書き出したあとに呼ぶ"""
    main(quiet=True)


if __name__ == '__main__':
    main()
